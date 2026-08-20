"""v6 다봉성(multimodality) 검사.

정책 관점 검사: v6 입력 state 는 joint 이므로, "state joint 가 비슷한데
action joint 가 크게 다른" 쌍이 진짜 다봉이다 (감김 상태는 입력에 포함됨).
"""
import json
import sys
import numpy as np
import pandas as pd


V5 = "/home/kim/physical_ai_tools/docker/huggingface/lerobot/dlcodnjs/tx90_act_pick_and_place_v5_ee"
V6 = "/home/kim/tx90/m1013/v6_staging"
OFF = np.array([+0.15, -0.15, +0.10])

info = json.load(open(f"{V5}/meta/info.json"))
N = info["total_episodes"]

poses, joints, eps = [], [], []
for ep in range(N):
    d5 = pd.read_parquet(f"{V5}/data/chunk-000/episode_{ep:06d}.parquet")
    d6 = pd.read_parquet(f"{V6}/data/chunk-000/episode_{ep:06d}.parquet")
    ac5 = np.stack(d5["action"]).astype(float)
    ac6 = np.stack(d6["action"]).astype(float)
    T = len(d5)
    idx = np.linspace(0, T - 1, 30).astype(int)
    st6 = np.stack(d6["observation.state"]).astype(float)
    poses.append(st6[idx, :6])
    joints.append(ac6[idx, :6])
    eps += [ep] * len(idx)

S = np.vstack(poses)          # state joints (정책 입력)
J = np.vstack(joints)         # action joints (정책 출력)
eps = np.array(eps)
M = len(S)
print(f"샘플 {M}개 ({N} 에피소드 × 30)")

STATE_TH = 10.0               # state joint 이웃 판정 (deg, max)
JOINT_TH = 45.0

bad = 0
worst = []
for i in range(M):
    ds = np.degrees(np.abs(S - S[i])).max(axis=1)
    near = (ds < STATE_TH) & (eps != eps[i])
    if not near.any():
        continue
    dj = np.degrees(np.abs(J[near] - J[i])).max(axis=1)
    w = dj.max()
    if w > JOINT_TH:
        bad += 1
        k = np.where(near)[0][int(np.argmax(dj))]
        worst.append((round(w, 1), int(eps[i]), int(eps[k])))

print(f"다봉 의심 샘플: {bad}/{M} ({100*bad/M:.1f}%)")
if worst:
    worst.sort(reverse=True)
    print("최악 10건 (joint차°, ep_i, ep_j):", worst[:10])
    from collections import Counter
    c = Counter([w[1] for w in worst] + [w[2] for w in worst])
    print("관련 에피소드 top:", c.most_common(10))
else:
    print("→ 단봉: 비슷한 pose 는 어디서나 비슷한 joint")
