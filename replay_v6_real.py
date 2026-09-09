#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v7 실기 수집 — v6 궤적을 M1013 에서 재생하며 실물 영상·관절을 기록한다.

에피소드 1개 절차:
    ① 로봇이 「파지 자세」로 간다 (조 열림)   ← 큐브를 놓을 자리를 로봇이 알려준다
    ② 조작자가 조 사이에 큐브를 놓고 손을 뺀다
    ③ 로봇이 시작 자세로 복귀
    ④ 기록 시작 → 궤적 재생(그리퍼 포함) → 기록 정지
    ⑤ 큐브 회수, 다음 에피소드

왜 재생인가 — 궤적은 v6 에 159개가 이미 검증돼 있다. 정작 없는 건 M1013 실물 영상이다.
정책이 OMX 영상으로 학습돼 M1013 화면을 못 알아보므로, **같은 동작 + 새 영상**이 필요하다.
큐브 위치는 에피소드마다 다르므로(9cm×9cm 산포) 영상 속 큐브 픽셀 위치도 달라진다.

    python3 replay_v6_real.py --dry                 # ROS2 없이 절차·궤적만 검증
    python3 replay_v6_real.py --episodes 0,20,50    # 실기 수집

⚠️ 안전
  · ②에서 사람 손이 조 사이에 들어간다. **로봇 정지 확인 + 그리퍼 열림(무압)** 상태에서만.
  · 처음에는 --speed 를 낮춰(예 10) 한 에피소드만 돌려보고 올릴 것.
  · 비상정지 위치를 먼저 확인할 것.

2026-09-09 작성.
"""
from __future__ import annotations

import argparse
import glob
import sys
import time

import numpy as np

MAX_SPLINE_PTS = 100          # MoveSplineJoint 제한 (dsr_msgs2 srv 주석: target [100][6])
N_JOINT = 6
GRIP_CH = 6                   # 궤적 7번째 채널 = 그리퍼
DEG = 180.0 / np.pi           # ⚠️ 데이터는 라디안, 두산 서비스는 도(degree)


def load_episode(staging: str, ep: int) -> np.ndarray:
    fs = glob.glob(f"{staging}/data/chunk-*/episode_{ep:06d}.parquet")
    if not fs:
        raise SystemExit(f"에피소드 {ep} 없음: {staging}")
    import pandas as pd
    df = pd.read_parquet(fs[0])
    col = [c for c in df.columns if "action" in c][0]
    a = np.stack(df[col].values).astype(float)
    if a.shape[1] < N_JOINT + 1:
        raise SystemExit(f"채널 {a.shape[1]} 개 — 관절 6 + 그리퍼 1 이 필요하다")
    return a


def downsample(traj: np.ndarray, n: int = MAX_SPLINE_PTS) -> tuple[np.ndarray, np.ndarray]:
    """궤적을 스플라인 웨이포인트 n 개로 줄인다. 끝점은 반드시 포함."""
    T = len(traj)
    if T <= n:
        return traj, np.arange(T)
    idx = np.unique(np.concatenate([np.linspace(0, T - 1, n).round().astype(int), [T - 1]]))
    return traj[idx], idx


def grip_events(g: np.ndarray, fps: float) -> list[tuple[float, bool]]:
    """그리퍼 채널 → [(시각 s, 닫힘 bool)] 전이 목록. 낮은 값 = 닫힘."""
    from gripper_ctl import GripperGate
    gate = GripperGate(fps=fps)
    for i, v in enumerate(g):
        gate.update(float(v), i / fps)
    return list(gate.history)


def summarize(traj: np.ndarray, fps: float, ep: int) -> dict:
    q = traj[:, :N_JOINT]
    wp, idx = downsample(traj)
    ev = grip_events(traj[:, GRIP_CH], fps)
    dur = len(traj) / fps
    # 스플라인 근사 오차: 웨이포인트를 선형보간해 원본과 비교 (컨트롤러 스플라인은 이보다 매끄럽다)
    approx = np.stack([np.interp(np.arange(len(traj)), idx, q[idx, j]) for j in range(N_JOINT)], 1)
    err = np.degrees(np.abs(approx - q)).max()
    return dict(ep=ep, frames=len(traj), dur_s=dur, waypoints=len(wp),
                grip_events=ev, approx_err_deg=err,
                q_min=np.degrees(q.min(0)), q_max=np.degrees(q.max(0)))


def run_dry(args) -> int:
    print("건식 실행 — ROS2·로봇 없이 절차와 궤적만 검증한다.\n")
    eps = [int(x) for x in args.episodes.split(",")]
    print("%-5s %7s %7s %7s %9s  %s" % ("ep", "프레임", "길이s", "웨이포", "근사오차°", "그리퍼 전이"))
    worst = 0.0
    for ep in eps:
        tr = load_episode(args.staging, ep)
        s = summarize(tr, args.fps, ep)
        worst = max(worst, s["approx_err_deg"])
        ev = " ".join(f"{t:.1f}s{'닫' if c else '열'}" for t, c in s["grip_events"])
        print("%-5d %7d %7.1f %7d %9.2f  %s"
              % (ep, s["frames"], s["dur_s"], s["waypoints"], s["approx_err_deg"], ev or "없음"))
    print(f"\n웨이포인트 {MAX_SPLINE_PTS} 개로 줄였을 때 최대 근사오차 {worst:.2f}°")
    print("  (선형보간 기준. 실제 컨트롤러 스플라인은 이보다 매끄럽다)")
    if worst > 2.0:
        print("  ⚠️ 2° 를 넘는다 — 궤적을 나눠 여러 번 호출하는 편이 낫다")
    tr = load_episode(args.staging, eps[0])
    print(f"\n관절 범위 (ep{eps[0]}, deg):")
    for j in range(N_JOINT):
        print("  J%d  %8.2f ~ %8.2f" % (j + 1, np.degrees(tr[:, j].min()), np.degrees(tr[:, j].max())))
    print("\n실기 실행 전 확인:")
    print("  · 두산 드라이버 기동 · 카메라 노드 2개 기동 · gripper_ctl 노드 기동")
    print("  · physical_ai_server 가 m1013 설정으로 떠 있을 것")
    print("  · --speed 를 낮춰(10) 한 에피소드만 먼저 돌려볼 것")
    return 0


def run_real(args) -> int:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import Float32
    from sensor_msgs.msg import JointState
    from dsr_msgs2.srv import MoveJoint, MoveSplineJoint, MoveStop
    from std_msgs.msg import Float64MultiArray

    class Runner(Node):
        def __init__(self):
            super().__init__("replay_v6_real")
            self.mj = self.create_client(MoveJoint, "motion/move_joint")
            self.ms = self.create_client(MoveSplineJoint, "motion/move_spline_joint")
            self.stop = self.create_client(MoveStop, "motion/move_stop")
            self.pub_grip = self.create_publisher(Float32, "policy/gripper", 10)
            # ★ leader 역할: 우리가 「의도한」 관절 목표를 30 Hz 로 발행한다.
            #   physical_ai_server 가 이걸 action 으로, /joint_states(실측)를 state 로 기록한다.
            #   v6 의 action 정의(목표 관절값)와 의미가 정확히 같아진다.
            self.pub_cmd = self.create_publisher(JointState, "replay/joint_command", 10)
            for c, n in ((self.mj, "move_joint"), (self.ms, "move_spline_joint")):
                if not c.wait_for_service(timeout_sec=5.0):
                    raise SystemExit(f"motion/{n} 없음 — 두산 드라이버 확인")

        def call(self, cli, req, timeout=120.0):
            fut = cli.call_async(req)
            rclpy.spin_until_future_complete(self, fut, timeout_sec=timeout)
            return fut.result()

        def move_joint(self, q_rad, vel, acc):
            r = MoveJoint.Request()
            r.pos = [float(v) for v in np.degrees(q_rad[:N_JOINT])]   # ⚠️ 도 변환
            r.vel, r.acc, r.sync_type = float(vel), float(acc), 0     # SYNC = 끝날 때까지 대기
            return self.call(self.mj, r)

        def publish_cmd(self, q_rad, grip_closed: bool):
            m = JointState()
            m.header.stamp = self.get_clock().now().to_msg()
            m.name = [f"joint_{i}" for i in range(1, N_JOINT + 1)] + ["gripper"]
            m.position = [float(v) for v in q_rad[:N_JOINT]] + [0.0 if grip_closed else 1.0]
            self.pub_cmd.publish(m)

        def set_grip(self, closed: bool):
            # gripper_ctl 노드가 구독한다. 히스테리시스 밴드 밖 값을 준다.
            self.pub_grip.publish(Float32(data=0.10 if closed else 0.90))

        def spline(self, wp_rad, dur_s, vel, acc):
            r = MoveSplineJoint.Request()
            r.pos = []
            for q in wp_rad:
                m = Float64MultiArray(); m.data = [float(v) for v in np.degrees(q[:N_JOINT])]
                r.pos.append(m)
            r.pos_cnt = len(wp_rad)
            r.vel = [float(vel)] * N_JOINT
            r.acc = [float(acc)] * N_JOINT
            r.time = float(dur_s)
            r.mode, r.sync_type = 0, 1                                # ASYNC — 그리퍼를 병행 구동
            return self.call(self.ms, r, timeout=10.0)

    rclpy.init()
    node = Runner()
    eps = [int(x) for x in args.episodes.split(",")]
    try:
        for k, ep in enumerate(eps, 1):
            tr = load_episode(args.staging, ep)
            wp, _ = downsample(tr)
            dur = len(tr) / args.fps
            ev = grip_events(tr[:, GRIP_CH], args.fps)
            t_grasp = next((t for t, c in ev if c), None)

            print(f"\n===== [{k}/{len(eps)}] 에피소드 {ep} · {dur:.1f}s · 그리퍼 전이 {len(ev)}회")
            node.set_grip(False)                                      # 조 열림
            time.sleep(0.5)

            if t_grasp is None:
                print("  파지 전이가 없다 — 건너뛴다"); continue
            i_grasp = int(t_grasp * args.fps)
            print(f"  ① 파지 자세로 이동 (프레임 {i_grasp}, {t_grasp:.1f}s 지점)")
            node.move_joint(tr[i_grasp], args.speed, args.speed)

            input("  ② 조 사이에 큐브를 놓고 손을 뺀 뒤 Enter — (Ctrl+C 로 중단) ")

            print("  ③ 시작 자세로 복귀")
            node.move_joint(tr[0], args.speed, args.speed)

            for s in range(args.countdown, 0, -1):
                print(f"     재생 {s}...", end="\r"); time.sleep(1.0)
            print("  ④ 기록 시작 → 재생        ")
            # 기록은 physical_ai_server 가 담당한다(START_RECORD/MOVE_TO_NEXT).
            # 여기서는 재생과 그리퍼만 책임진다.
            node.spline(wp, dur, args.speed, args.speed)
            t0 = time.time()
            nxt = list(ev)                                            # 남은 그리퍼 전이
            closed_now = False
            dt = 1.0 / args.fps
            for i in range(len(tr)):                                  # 30 Hz 로 명령값 발행
                while nxt and (time.time() - t0) >= nxt[0][0]:
                    _, closed_now = nxt.pop(0)
                    node.set_grip(closed_now)
                    print(f"     {time.time()-t0:5.1f}s  그리퍼 {'닫힘' if closed_now else '열림'}")
                node.publish_cmd(tr[i], closed_now)
                slack = t0 + (i + 1) * dt - time.time()
                if slack > 0:
                    time.sleep(slack)
            while time.time() - t0 < dur + 0.5:
                node.publish_cmd(tr[-1], closed_now); time.sleep(dt)
            node.set_grip(False)
            print("  ⑤ 완료 — 큐브를 회수할 것")
        return 0
    except KeyboardInterrupt:
        print("\n중단 — 로봇 정지")
        node.call(node.stop, MoveStop.Request(), timeout=5.0)
        return 130
    finally:
        try:
            node.set_grip(False)                                      # 안전: 반드시 열고 끝낸다
        except Exception:
            pass
        node.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", default="/home/kim/m1013/v6_staging")
    ap.add_argument("--episodes", default="0,20,50,80,110,130,145,158")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--speed", type=float, default=20.0, help="deg/s, deg/s² — 처음엔 10 으로")
    ap.add_argument("--countdown", type=int, default=3)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    sys.exit(run_dry(a) if a.dry else run_real(a))
