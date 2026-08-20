#!/usr/bin/env python3
"""큐브 배치 고정점 반복: 접근 스윕이 큐브를 미는 것이 불가피하므로,
"밀린 뒤 닫힘 시점(f240)에 실증 홀드 지점 H 에 도달"하도록 시작 위치를 반복 보정.

결정론적 시뮬레이션이라 수렴 가능. 성공하면 해당 --cube-at 를 결과로 출력.
사용: python3 fit_cube_position.py [--ep 0] [--iters 4]
"""
import argparse
import json
import subprocess

import numpy as np

H = np.array([0.7001, -0.3221])   # 실증 홀드 지점 (접촉밴드 높이 z=0.4031 기준, fingertraj_cal35)
OUT = "/home/kim/tx90/m1013/sim_out"

ap = argparse.ArgumentParser()
ap.add_argument("--ep", type=int, default=0)
ap.add_argument("--iters", type=int, default=4)
args = ap.parse_args()

c = H.copy()
for it in range(1, args.iters + 1):
    label = f"fit{it}"
    cmd = (f"cd /home/kim/isaacsim && ./python.sh /home/kim/tx90/m1013/replay_isaac.py "
           f"--ep {args.ep} --no-render --label {label} --cube-at {c[0]:.4f},{c[1]:.4f}")
    subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)
    res = json.load(open(f"{OUT}/replay_ep{args.ep:03d}_result.json"))
    e240 = np.array(next(l["cube"] for l in res["log"] if l["t"] == 240)[:2])
    print(f"[iter {it}] 배치 ({c[0]:.4f},{c[1]:.4f}) → f240 위치 ({e240[0]:.4f},{e240[1]:.4f}) "
          f"| H 오차 {np.linalg.norm(e240-H)*1000:.1f}mm | lifted={res['lifted']} "
          f"success={res['success']} err_xy={res['err_xy_mm']}mm", flush=True)
    if res["success"]:
        print(f"성공! --cube-at {c[0]:.4f},{c[1]:.4f}")
        break
    if res["lifted"] and res["err_xy_mm"] < 80:
        print(f"파지 성공 (배치 {c[0]:.4f},{c[1]:.4f}) — 놓기 오차만 남음")
        break
    c = c + (H - e240) * 0.8   # 감쇠 보정
else:
    print("미수렴 — 기하 재검토 필요")
