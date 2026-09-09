#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M1013 그리퍼 제어 — 정책 출력 → SY5120 솔레노이드 (DO) 까지의 3단계.

    정책 (30 Hz, 0~1 연속)
       │
       ├─① 히스테리시스 + 최소유지  : 채터링 제거 → 안정된 이진 상태
       ├─② grip-lead                : 공압 지연만큼 명령을 앞당김
       └─③ ROS2 래퍼                : io/set_tool_digital_output 호출
       ▼
    플랜지 DO → M8 케이블 → SY5120 → 그리퍼

①② 는 순수 로직이라 ROS2 없이 import·테스트된다. ③ 만 rclpy 를 쓴다.

    python3 gripper_ctl.py                # 자체 테스트 (합성 채터링 + 실제 에피소드)
    python3 gripper_ctl.py --node         # ROS2 노드로 실행

2026-09-09 작성.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field

import numpy as np

# ── 규약 (run_policy_tx90.py 에서 승계) ─────────────────────────────────
# 정책 그리퍼 채널은 **낮을수록 닫힘** 이다. 데이터상 닫힘~0.23 / 열림~0.69,
# 그 중간이 0.459. 방향을 뒤집지 말 것.
GRIP_TH = 0.459
BAND = 0.10                 # 히스테리시스 반폭 → 닫힘 0.359 / 열림 0.559
CLOSE_TH = GRIP_TH - BAND
OPEN_TH = GRIP_TH + BAND

# MHF2-16D2 는 최대 60 c.p.m. = 1초에 1사이클. 한 상태를 최소 이만큼 유지한다.
# 0.5 s 면 정확히 사양 한계이고, 과제는 에피소드당 개폐가 1회씩이라 여유가 넉넉하다.
MIN_HOLD_S = 0.5

# 공압 지연 보상. **오토스위치 D-M9N 2개로 실측한 뒤 채울 것** (measure_lead() 참조).
# 30 Hz 기준 1.5~3 프레임(50~100 ms)이 발주서 추정치다.
LEAD_CLOSE_S = 0.0
LEAD_OPEN_S = 0.0

# 두산 플랜지 I/O. ⚠️ DO 와 DI 의 극성이 다르다 (dsr_msgs2/srv/io):
#   SetToolDigitalOutput.value : 0 = ON,  1 = OFF     ← 반전
#   GetToolDigitalInput.value  : 0 = OFF, 1 = ON      ← 정상
DO_ON, DO_OFF = 0, 1
DO_INDEX_VALVE = 1          # 실물 결선 후 확정
DI_INDEX_CLOSED = 1         # 오토스위치(닫힘 감지)
DI_INDEX_OPEN = 2           # 오토스위치(열림 감지)

# 밸브 A → 그리퍼「S」(닫힘). 솔레노이드 통전 = 닫힘, 무통전 = 스프링 복귀 = 열림.
# 정전·비상정지 시 열려서 큐브를 놓는 안전 배치다. 배관을 반대로 걸면 이 전제가 깨진다.


@dataclass
class GripperGate:
    """① 히스테리시스 + 최소유지, ② grip-lead 를 함께 처리하는 순수 로직.

    상태를 들고 있으므로 에피소드마다 새로 만들거나 reset() 할 것.
    """

    close_th: float = CLOSE_TH
    open_th: float = OPEN_TH
    min_hold_s: float = MIN_HOLD_S
    lead_close_s: float = LEAD_CLOSE_S
    lead_open_s: float = LEAD_OPEN_S
    fps: float = 30.0

    closed: bool = False            # 현재 이진 상태 (True = 닫힘)
    _t_last_change: float = -1e9
    n_suppressed: int = 0           # 최소유지에 막힌 전이 횟수 (진단용)
    history: list = field(default_factory=list)

    def reset(self, closed: bool = False) -> None:
        self.closed = closed
        self._t_last_change = -1e9
        self.n_suppressed = 0
        self.history.clear()

    # ── ② grip-lead ────────────────────────────────────────────────
    def _lead_value(self, g, chunk) -> float:
        """지연 보상: 액션 청크 안에서 앞을 내다본다.

        ACT 는 한 번에 chunk_size 개의 미래 액션을 뱉으므로 실시간에도 앞을
        볼 수 있다. 청크가 없으면(스칼라만 주어지면) 보상 없이 현재값을 쓴다.
        """
        if chunk is None or len(chunk) == 0:
            return float(g)
        lead_s = self.lead_close_s if not self.closed else self.lead_open_s
        k = int(round(lead_s * self.fps))
        if k <= 0:
            return float(chunk[0])
        return float(chunk[min(k, len(chunk) - 1)])

    # ── ① 히스테리시스 + 최소유지 ──────────────────────────────────
    def update(self, g: float, t: float, chunk=None) -> bool:
        """정책 출력 g(0~1) 와 시각 t(초) → 이진 상태(True=닫힘)."""
        v = self._lead_value(g, chunk)

        want = self.closed                       # 밴드 안이면 이전 상태 유지
        if v < self.close_th:
            want = True
        elif v > self.open_th:
            want = False

        if want != self.closed:
            if t - self._t_last_change < self.min_hold_s:
                self.n_suppressed += 1           # 최소유지 위반 → 무시
            else:
                self.closed = want
                self._t_last_change = t
                self.history.append((t, want))
        return self.closed


def naive(g: np.ndarray) -> np.ndarray:
    """비교용: 히스테리시스 없이 단일 임계값만 쓴 경우."""
    return g < GRIP_TH


def n_transitions(b: np.ndarray) -> int:
    return int(np.count_nonzero(np.diff(b.astype(int))))


# ── ③ ROS2 래퍼 ────────────────────────────────────────────────────
def run_node(args) -> None:
    """정책 출력 토픽을 구독해 플랜지 DO 를 구동하고, DI 로 실제 상태를 되돌린다.

    rclpy 는 여기서만 import 한다 — ①② 를 ROS2 없이 쓰기 위해서다.
    """
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import Bool, Float32
    from dsr_msgs2.srv import GetToolDigitalInput, SetToolDigitalOutput

    class GripperNode(Node):
        def __init__(self):
            super().__init__("m1013_gripper_ctl")
            self.gate = GripperGate(
                lead_close_s=args.lead_close, lead_open_s=args.lead_open,
                min_hold_s=args.min_hold, fps=args.fps)
            self.do_index = args.do_index
            self.cli_do = self.create_client(SetToolDigitalOutput, "io/set_tool_digital_output")
            self.cli_di = self.create_client(GetToolDigitalInput, "io/get_tool_digital_input")
            self.create_subscription(Float32, "policy/gripper", self.on_cmd, 10)
            self.pub_state = self.create_publisher(Bool, "gripper/closed_cmd", 10)
            self.pub_real = self.create_publisher(Bool, "gripper/closed_real", 10)
            self.create_timer(1.0 / args.fps, self.poll_di)
            self._last_sent = None
            self.get_logger().info(
                f"기동. DO index={self.do_index} (0=ON) · 밴드 {self.gate.close_th:.3f}/"
                f"{self.gate.open_th:.3f} · 최소유지 {self.gate.min_hold_s}s · "
                f"lead 닫힘 {self.gate.lead_close_s}s / 열림 {self.gate.lead_open_s}s")
            if self.gate.lead_close_s == 0.0 and self.gate.lead_open_s == 0.0:
                self.get_logger().warn(
                    "grip-lead 가 0 이다. 오토스위치로 지연을 실측해 --lead-close/--lead-open 에 넣을 것.")

        def on_cmd(self, msg: Float32):
            t = self.get_clock().now().nanoseconds * 1e-9
            closed = self.gate.update(float(msg.data), t)
            self.pub_state.publish(Bool(data=closed))
            if closed != self._last_sent:          # 전이에서만 서비스 호출
                self._send_do(closed)
                self._last_sent = closed

        def _send_do(self, closed: bool):
            if not self.cli_do.service_is_ready():
                self.get_logger().error("io/set_tool_digital_output 미준비 — 명령 유실")
                return
            req = SetToolDigitalOutput.Request()
            req.index = self.do_index
            req.value = DO_ON if closed else DO_OFF     # ⚠️ 0 이 ON
            self.cli_do.call_async(req)
            self.get_logger().info(f"밸브 {'ON(닫힘)' if closed else 'OFF(열림)'}")

        def poll_di(self):
            if not self.cli_di.service_is_ready():
                return
            req = GetToolDigitalInput.Request(); req.index = DI_INDEX_CLOSED
            fut = self.cli_di.call_async(req)
            fut.add_done_callback(
                lambda f: self.pub_real.publish(Bool(data=bool(f.result().value == 1)))
                if f.result() is not None else None)

    rclpy.init()
    node = GripperNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


# ── 자체 테스트 ────────────────────────────────────────────────────
def selftest() -> None:
    fps = 30.0
    print("① 히스테리시스 — 합성 채터링 (임계값 근처에서 ±0.03 떨림)")
    t = np.arange(0, 6, 1 / fps)
    g = np.where(t < 3, GRIP_TH + 0.02, GRIP_TH - 0.02) + 0.03 * np.sin(2 * np.pi * 7 * t)
    gate = GripperGate(fps=fps)
    hyst = np.array([gate.update(v, tt) for v, tt in zip(g, t)])
    nv = naive(g)
    print(f"   단일 임계값   전이 {n_transitions(nv):3d} 회  →  초당 {n_transitions(nv)/6:.1f} 회")
    print(f"   히스테리시스  전이 {n_transitions(hyst):3d} 회  →  초당 {n_transitions(hyst)/6:.1f} 회"
          f"   (최소유지가 막은 전이 {gate.n_suppressed} 회)")
    lim = 1.0
    print(f"   MHF2 한계 초당 {lim:.0f} 회  →  단일임계값 {'초과 ★' if n_transitions(nv)/6 > lim else 'OK'}"
          f" / 히스테리시스 {'초과 ★' if n_transitions(hyst)/6 > lim else 'OK'}")

    print("\n② grip-lead — 청크 앞보기")
    gate2 = GripperGate(fps=fps, lead_close_s=0.1)      # 3 프레임 앞
    chunk = np.array([0.69] * 3 + [0.23] * 20)          # 3 프레임 뒤 닫힘 명령
    print(f"   현재값 {chunk[0]:.2f}(열림) 인데 3프레임 뒤 {chunk[3]:.2f}(닫힘)")
    print(f"   lead 0 s  → {'닫힘' if GripperGate(fps=fps).update(chunk[0], 0.0, chunk) else '열림'}")
    print(f"   lead 0.1s → {'닫힘' if gate2.update(chunk[0], 0.0, chunk) else '열림'}   ← 미리 닫는다")

    print("\n③ 실제 에피소드 (v6_staging, 정책 그리퍼 채널)")
    import glob
    import pandas as pd
    fs = sorted(glob.glob("/home/kim/m1013/v6_staging/data/chunk-*/episode_*.parquet"))[:3]
    for f in fs:
        df = pd.read_parquet(f)
        col = [c for c in df.columns if "action" in c][0]
        a = np.stack(df[col].values)
        if a.shape[1] < 7:
            print("   그리퍼 채널 없음 — 건너뜀"); break
        gg = a[:, 6]
        tt = np.arange(len(gg)) / fps
        gt = GripperGate(fps=fps)
        hb = np.array([gt.update(v, s) for v, s in zip(gg, tt)])
        print(f"   {f.split('/')[-1]}  단일임계값 {n_transitions(naive(gg)):2d} 회 → "
              f"히스테리시스 {n_transitions(hb):2d} 회  (막은 전이 {gt.n_suppressed})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", action="store_true", help="ROS2 노드로 실행")
    ap.add_argument("--do-index", type=int, default=DO_INDEX_VALVE)
    ap.add_argument("--lead-close", type=float, default=LEAD_CLOSE_S)
    ap.add_argument("--lead-open", type=float, default=LEAD_OPEN_S)
    ap.add_argument("--min-hold", type=float, default=MIN_HOLD_S)
    ap.add_argument("--fps", type=float, default=30.0)
    a = ap.parse_args()
    run_node(a) if a.node else selftest()
