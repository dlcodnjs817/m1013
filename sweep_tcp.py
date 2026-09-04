#!/usr/bin/env python3
"""TCP 보정 반영 작업대 배치 스윕 (로컬 실행판).

원본 sweep_m1013.py 는 v5 원본 데이터셋이 필요하나 이 PC에 없다.
대신 v6_staging(변환 완료 관절)을 FK 로 되돌려 v5 앵커를 복원한다.

핵심 변경 — 플랜지 목표 산출식:
    기존: flange = v5 + d - R@[0,0,TCP]          (TCP=0.12, 핑거끝이 큐브보다 183.8mm 위)
    수정: flange = v5 + d + R@[0,0,F - TCP_new]  (F=0.1388 = v5점→큐브 거리)
"""
import glob, json, time, sys
import numpy as np, pandas as pd
from m1013_kin import M1013Kin, JOINT_LIMITS

TCP_OLD, F = 0.12, 0.13882972016227912
OFFSET = np.array([0.05, -0.15, 0.10])
STRIDE = 5
SEED0 = np.deg2rad([0, 20, 100, 0, 60, 0])
SCREEN = [0, 20, 50, 80, 110, 130, 145, 158]
DX = [-0.25, -0.15, -0.05, 0.0, 0.05, 0.15]
DY = [-0.15, 0.0, 0.15]
DZ = [-0.10, 0.0, 0.10]
TCPS = [0.060, 0.075, 0.090]

kin = M1013Kin(urdf="m1013_local.urdf")

def load_anchors():
    fs = sorted(glob.glob("v6_staging/data/chunk-*/episode_*.parquet"))
    out = []
    for f in fs:
        q = np.stack(pd.read_parquet(f)["action"].to_numpy()).astype(float)[::STRIDE, :6]
        P = np.empty((len(q), 3)); R = np.empty((len(q), 3, 3))
        for i, qq in enumerate(q):
            T = kin.fk(qq); R[i] = T[:3, :3]
            P[i] = T[:3, 3] + R[i] @ np.array([0, 0, TCP_OLD]) - OFFSET
        out.append((P, R))
    return out

def ev(anc, d, tcp, eps):
    s = {"fail":0,"branch":0,"ep_fail":[],"min_q5":np.inf,"min_j3":np.inf,"maxdq":0.0,"n":0}
    off = np.array([0.0, 0.0, F - tcp])
    for ep in eps:
        P, R = anc[ep]; seed = SEED0.copy(); prev = None; bad = 0
        for p5, Rf in zip(P, R):
            q, st = kin.solve(p5 + d + Rf @ off, Rf, seed)
            s["n"] += 1
            if st == "fail": s["fail"] += 1; bad += 1; continue
            if st == "branch": s["branch"] += 1; bad += 1
            s["min_q5"] = min(s["min_q5"], abs(q[4]))
            s["min_j3"] = min(s["min_j3"], q[2]-JOINT_LIMITS[2][0], JOINT_LIMITS[2][1]-q[2])
            if prev is not None:
                s["maxdq"] = max(s["maxdq"], np.degrees(np.max(np.abs(q-prev)))/STRIDE)
            prev = q; seed = q
        if bad: s["ep_fail"].append(int(ep))
    s["min_q5"] = float(np.degrees(s["min_q5"])); s["min_j3"] = float(np.degrees(s["min_j3"]))
    return s

if __name__ == "__main__":
    t0 = time.time()
    print("앵커 복원 중...", flush=True)
    anc = load_anchors()
    print(f"에피소드 {len(anc)}개, 앵커 {sum(len(p) for p,_ in anc)}개 ({time.time()-t0:.0f}s)\n", flush=True)

    # 자기검증: tcp = F+TCP_OLD, d = OFFSET 이면 원본 재현이어야 함
    chk = ev(anc, OFFSET, F+TCP_OLD, SCREEN[:2])
    print(f"[자기검증] fail={chk['fail']} branch={chk['branch']}  → {'✅ 복원 정확' if chk['fail']==0 and chk['branch']==0 else '⚠️ 복원 오차'}\n", flush=True)

    res = {}
    cands = [(x,y,z) for x in DX for y in DY for z in DZ]
    for tcp in TCPS:
        print(f"===== TCP {tcp*1000:.0f} mm : 1단계 {len(cands)}후보 × 8ep =====", flush=True)
        r1 = []
        for i, d in enumerate(cands):
            st = ev(anc, np.array(d), tcp, SCREEN); st["d"] = list(d)
            r1.append(st)
            ok = st["fail"]==0 and st["branch"]==0
            print(f"  [{i+1:2d}/{len(cands)}] d=({d[0]:+.2f},{d[1]:+.2f},{d[2]:+.2f}) {'PASS' if ok else '----'} "
                  f"fail={st['fail']} br={st['branch']} q5={st['min_q5']:.1f}° j3={st['min_j3']:.1f}°", flush=True)
        p = sorted([r for r in r1 if r["fail"]==0 and r["branch"]==0], key=lambda r:(-r["min_q5"],-r["min_j3"]))
        print(f"  1단계 통과 {len(p)}/{len(cands)}", flush=True)
        r2 = []
        for r in p[:5]:
            st = ev(anc, np.array(r["d"]), tcp, range(len(anc))); st["d"] = r["d"]
            r2.append(st)
            ok = st["fail"]==0 and st["branch"]==0
            print(f"  2단계 d={r['d']} {'PASS' if ok else '----'} fail={st['fail']} br={st['branch']} "
                  f"q5={st['min_q5']:.1f}° j3={st['min_j3']:.1f}° maxdq={st['maxdq']:.1f}°/fr", flush=True)
        res[f"tcp_{int(tcp*1000)}"] = {"stage1": r1, "stage2": r2}
        json.dump(res, open("sweep_tcp_result.json","w"), indent=1, ensure_ascii=False)
    print(f"\n완료 {time.time()-t0:.0f}s → sweep_tcp_result.json", flush=True)
