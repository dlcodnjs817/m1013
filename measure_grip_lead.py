#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공압 개폐 지연 실측 — gripper_ctl.py 의 LEAD_CLOSE_S / LEAD_OPEN_S 를 채우기 위한 도구.

플랜지 DO 로 밸브를 켜고, 오토스위치(D-M9N) DI 가 바뀔 때까지의 시간을 잰다.
DO 와 DI 를 같은 컴퓨터에서 다루므로 시계 동기 문제가 없다.

    ros2 run ... 없이 바로:
      python3 measure_grip_lead.py                 # 10 사이클
      python3 measure_grip_lead.py -n 20 --dry     # 배선 확인만 (밸브 구동 안 함)

⚠️ 실행 전 확인
  · 공압 연결·압력이 **실사용 조건**(0.2~0.3 MPa)이어야 한다. 압력이 다르면 지연도 다르다.
  · **스피드컨트롤러를 최종 조임 상태로** 맞춘 뒤에 잴 것. 조이면 닫힘이 느려진다.
  · 조 사이에 손·물체를 두지 말 것. 이 스크립트는 그리퍼를 반복 개폐한다.

측정값에는 서비스 왕복 시간(보통 1~5 ms)이 포함된다. 공압 지연이 수십~수백 ms 라
무시할 수준이지만, 결과에 왕복 시간도 같이 찍는다.

2026-09-09 작성.
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
import time

from gripper_ctl import (DI_INDEX_CLOSED, DI_INDEX_OPEN, DO_INDEX_VALVE,
                         DO_OFF, DO_ON)

POLL_S = 0.002          # DI 폴링 주기 (2 ms) — 분해능이 이 값으로 제한된다
TIMEOUT_S = 3.0
SETTLE_S = 1.0          # 사이클 사이 안정화


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--cycles", type=int, default=10)
    ap.add_argument("--do-index", type=int, default=DO_INDEX_VALVE)
    ap.add_argument("--di-closed", type=int, default=DI_INDEX_CLOSED)
    ap.add_argument("--di-open", type=int, default=DI_INDEX_OPEN)
    ap.add_argument("--dry", action="store_true", help="밸브를 켜지 않고 DI 만 읽어 배선 확인")
    a = ap.parse_args()

    import rclpy
    from rclpy.node import Node
    from dsr_msgs2.srv import GetToolDigitalInput, SetToolDigitalOutput

    class M(Node):
        def __init__(self):
            super().__init__("measure_grip_lead")
            self.do = self.create_client(SetToolDigitalOutput, "io/set_tool_digital_output")
            self.di = self.create_client(GetToolDigitalInput, "io/get_tool_digital_input")
            for c, n in ((self.do, "set_tool_digital_output"), (self.di, "get_tool_digital_input")):
                if not c.wait_for_service(timeout_sec=5.0):
                    raise SystemExit(f"서비스 io/{n} 없음 — 두산 드라이버가 떠 있는지 확인할 것")

        def read_di(self, index: int):
            """DI 1채널 읽기 → (값 bool, 왕복 시간 s)."""
            req = GetToolDigitalInput.Request(); req.index = index
            t0 = time.perf_counter()
            fut = self.do_call(self.di, req)
            rtt = time.perf_counter() - t0
            return (bool(fut.value == 1) if fut is not None else None), rtt

        def set_do(self, on: bool):
            req = SetToolDigitalOutput.Request()
            req.index = a.do_index
            req.value = DO_ON if on else DO_OFF      # ⚠️ 0 이 ON
            return self.do_call(self.do, req)

        def do_call(self, cli, req, timeout=2.0):
            fut = cli.call_async(req)
            rclpy.spin_until_future_complete(self, fut, timeout_sec=timeout)
            return fut.result()

        def wait_flip(self, index: int, target: bool):
            """DI[index] 가 target 이 될 때까지 폴링 → 걸린 시간(s). 실패 시 None."""
            t0 = time.perf_counter()
            while time.perf_counter() - t0 < TIMEOUT_S:
                v, _ = self.read_di(index)
                if v == target:
                    return time.perf_counter() - t0
                time.sleep(POLL_S)
            return None

    rclpy.init()
    node = M()
    try:
        if a.dry:
            print("배선 확인 모드 — 밸브를 구동하지 않는다.")
            for idx, name in ((a.di_closed, "닫힘 스위치"), (a.di_open, "열림 스위치")):
                v, rtt = node.read_di(idx)
                print(f"  DI{idx} ({name}) = {v}   서비스 왕복 {rtt*1000:.1f} ms")
            print("\n조를 손으로 움직이면서 값이 바뀌는지 보고, 채널 번호가 맞는지 확인할 것.")
            return 0

        print(f"개폐 지연 실측 — {a.cycles} 사이클")
        print("⚠️ 조 사이에 손·물체를 두지 말 것.\n")
        node.set_do(False)                       # 안전: 열림 상태에서 시작
        time.sleep(SETTLE_S)

        close_ms, open_ms, rtts = [], [], []
        for i in range(1, a.cycles + 1):
            node.set_do(True)                    # 닫아라
            dtc = node.wait_flip(a.di_closed, True)
            time.sleep(SETTLE_S)
            node.set_do(False)                   # 열어라
            dto = node.wait_flip(a.di_open, True)
            time.sleep(SETTLE_S)
            _, rtt = node.read_di(a.di_closed); rtts.append(rtt)
            if dtc is None or dto is None:
                print(f"  {i:2d}  ★ 타임아웃 — 오토스위치 채널·공압 연결 확인")
                continue
            close_ms.append(dtc * 1000); open_ms.append(dto * 1000)
            print(f"  {i:2d}  닫힘 {dtc*1000:6.1f} ms   열림 {dto*1000:6.1f} ms")

        if not close_ms:
            print("\n유효 측정 0회 — 배선을 --dry 로 먼저 확인할 것.")
            return 1

        print(f"\n서비스 왕복 평균 {st.mean(rtts)*1000:.1f} ms (측정값에 포함돼 있다)")
        print("%-6s %8s %8s %8s %8s" % ("", "평균", "표준편차", "최소", "최대"))
        for name, v in (("닫힘", close_ms), ("열림", open_ms)):
            sd = st.stdev(v) if len(v) > 1 else 0.0
            print("%-6s %7.1f %8.1f %8.1f %8.1f  ms" % (name, st.mean(v), sd, min(v), max(v)))

        # 권장값: 평균 + 1 표준편차 (늦게 닫히는 쪽으로 안전하게)
        lc = (st.mean(close_ms) + (st.stdev(close_ms) if len(close_ms) > 1 else 0)) / 1000
        lo = (st.mean(open_ms) + (st.stdev(open_ms) if len(open_ms) > 1 else 0)) / 1000
        print(f"\n권장값 (평균 + 1σ, 30 Hz 기준 {lc*30:.1f} / {lo*30:.1f} 프레임)")
        print(f"  gripper_ctl.py 에 반영:")
        print(f"    LEAD_CLOSE_S = {lc:.3f}")
        print(f"    LEAD_OPEN_S  = {lo:.3f}")
        if lc * 30 > 5 or lo * 30 > 5:
            print("\n  ⚠️ 5 프레임을 넘는다. 스피드컨트롤러를 너무 조였거나 압력이 낮다.")
        return 0
    finally:
        try:
            node.set_do(False)                   # 안전: 반드시 열고 끝낸다
        except Exception:
            pass
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
