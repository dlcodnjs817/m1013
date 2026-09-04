#!/usr/bin/env python3
"""M1013 작업 사각형 배치 스윕.

v5(EE pose, TX90 base 프레임) 궤적에 평행이동 오프셋 d 를 적용해 M1013 base 프레임
후보 위치를 만들고, 각 후보에서 앵커(6Hz) IK 체인을 돌려 채점한다.

convert_v6.py 규약 재사용: 7프레임 이동평균 → 6Hz 앵커 → 시드 체인(직전 해)
→ 2π 접기 → 브랜치(>90°) 거부 → 섭동 재시도.

2단계:
  1) 후보 전체 × 선별 에피소드 8개 → 실패/브랜치 0인 후보만 통과
  2) 통과 후보 상위(손목 특이점 여유 순) 5개 × 전체 159 에피소드 → 최종 확정

사용: python3 sweep_m1013.py [--stage2-top 5] [--out sweep_result.json]
"""
import argparse
import json
import time

import numpy as np
import pandas as pd

from m1013_kin import M1013Kin, euler_xyz_extrinsic_to_R, JOINT_LIMITS, orient_corr

CORR = orient_corr()  # 그리퍼 일자 장착용 손목 45° 보정

V5 = "/home/kim/physical_ai_tools/docker/huggingface/lerobot/dlcodnjs/tx90_act_pick_and_place_v5_ee"
N_EP = 159
SCREEN_EPS = [0, 20, 50, 80, 110, 130, 145, 158]  # task0/task1 포함 선별용
ANCHOR_STRIDE = 5      # 30Hz → 6Hz
MA_WIN = 7             # convert_v6 과 동일한 이동평균 창
GENERIC_SEED = np.deg2rad([0, 20, 100, 0, 60, 0])  # 테이블 위 아래보기 초기 시드

# 오프셋 후보 (m): v5 좌표에 더해 M1013 base 프레임으로
DX = [-0.25, -0.15, -0.05, 0.0, +0.05, +0.15]
DY = [-0.15, 0.0, +0.15]
DZ = [-0.10, 0.0, +0.10]

# 플랜지(link_6) → 파지점 = 조 사이 큐브 중심. v5 pose 를 파지점 목표로 해석:
#   플랜지 = p - R@[0,0,TCP]
#
# ★ 2026-09-04 정정. 종전 0.12 는 "플랜지 → 핑거 끝" 이었으나 정의가 틀렸다.
#   v5 추적점 = OMX end_effector_link 이고, 원본 OMX 데이터에서 이 점은 파지 순간
#   큐브 중심과 일치한다:  ep0 파지 z=0.0752  vs  큐브중심 0.0574+0.0175=0.0749  (오차 0.3mm)
#   (0.0574 = 그리퍼 개폐 전이 시점 z 평균 = Umeyama 4코너 기준면)
#   따라서 TCP 는 "핑거 끝"이 아니라 "조 사이 큐브 중심"까지의 거리다.
#
# MHF2-16D2 + 핑거 어태치먼트 실물 CAD (2026-09-03 확정, 플랜지 로컬):
JAW_TIP   = 0.083    # 조 끝 (플랜지면 기준). 조는 z 45~83
CUBE_SIZE = 0.035    # 폼 큐브
JAW_CLEAR = 0.002    # 파지 시 조 끝이 상판 위로 띄우는 여유
TCP = JAW_TIP + JAW_CLEAR - CUBE_SIZE / 2   # = 0.0675


def load_anchors(ep):
    df = pd.read_parquet(f"{V5}/data/chunk-000/episode_{ep:06d}.parquet")
    a = np.stack(df["action"].to_numpy()).astype(float)  # (T,7)
    # 7프레임 이동평균 (위치+오일러; v5 는 wrap 수정 완료라 연속적)
    k = np.ones(MA_WIN) / MA_WIN
    pad = MA_WIN // 2
    sm = np.empty_like(a[:, :6])
    for c in range(6):
        col = np.pad(a[:, c], pad, mode="edge")
        sm[:, c] = np.convolve(col, k, mode="valid")
    return sm[::ANCHOR_STRIDE]  # (A,6)


def eval_candidate(kin, d, episodes, anchors_cache):
    """오프셋 d 에서 에피소드들의 앵커 IK 체인 채점."""
    stats = {"fail": 0, "branch": 0, "ep_fail": [], "min_q5": np.inf,
             "min_j3_margin": np.inf, "max_dq_deg": 0.0, "n_anchor": 0}
    for ep in episodes:
        anc = anchors_cache[ep]
        seed = GENERIC_SEED.copy()
        prev = None
        ep_bad = 0
        for i, row in enumerate(anc):
            R = euler_xyz_extrinsic_to_R(*row[3:6]) @ CORR
            p = row[:3] + d - R @ np.array([0.0, 0.0, TCP])
            q, st = kin.solve(p, R, seed)
            stats["n_anchor"] += 1
            if st == "fail":
                stats["fail"] += 1
                ep_bad += 1
                continue  # 시드 유지한 채 다음 앵커
            if st == "branch":
                stats["branch"] += 1
                ep_bad += 1
            stats["min_q5"] = min(stats["min_q5"], abs(q[4]))
            j3m = min(q[2] - JOINT_LIMITS[2][0], JOINT_LIMITS[2][1] - q[2])
            stats["min_j3_margin"] = min(stats["min_j3_margin"], j3m)
            if prev is not None:
                # 앵커 간 이동을 30Hz 로 보간했을 때 프레임당 최대 관절 이동
                stats["max_dq_deg"] = max(stats["max_dq_deg"],
                                          np.degrees(np.max(np.abs(q - prev))) / ANCHOR_STRIDE)
            prev = q
            seed = q
        if ep_bad:
            stats["ep_fail"].append(int(ep))
    stats["min_q5"] = float(np.degrees(stats["min_q5"]))
    stats["min_j3_margin"] = float(np.degrees(stats["min_j3_margin"]))
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage2-top", type=int, default=5)
    ap.add_argument("--out", default="/home/kim/m1013/sweep_result.json")
    args = ap.parse_args()

    kin = M1013Kin()
    t0 = time.time()

    print("앵커 로드 (선별 8 에피소드)...", flush=True)
    cache = {ep: load_anchors(ep) for ep in SCREEN_EPS}

    # ---- 1단계: 격자 선별 ----
    results = []
    cands = [(dx, dy, dz) for dx in DX for dy in DY for dz in DZ]
    print(f"1단계: 후보 {len(cands)}개 × 에피소드 {len(SCREEN_EPS)}개", flush=True)
    for n, d in enumerate(cands):
        st = eval_candidate(kin, np.array(d), SCREEN_EPS, cache)
        st["d"] = list(d)
        results.append(st)
        tag = "PASS" if st["fail"] == 0 and st["branch"] == 0 else "----"
        print(f"  [{n + 1:2d}/{len(cands)}] d=({d[0]:+.2f},{d[1]:+.2f},{d[2]:+.2f}) {tag} "
              f"fail={st['fail']} branch={st['branch']} min|q5|={st['min_q5']:.1f}° "
              f"j3여유={st['min_j3_margin']:.1f}° maxΔq={st['max_dq_deg']:.1f}°/fr", flush=True)

    passed = [r for r in results if r["fail"] == 0 and r["branch"] == 0]
    # 손목 특이점 여유 우선, 다음 J3 여유
    passed.sort(key=lambda r: (-r["min_q5"], -r["min_j3_margin"]))
    print(f"\n1단계 통과 {len(passed)}/{len(cands)}. 상위 {args.stage2_top}개로 2단계 진행", flush=True)

    # ---- 2단계: 전체 159 에피소드 ----
    print("앵커 로드 (전체 159 에피소드)...", flush=True)
    cache_all = {ep: load_anchors(ep) for ep in range(N_EP)}
    finals = []
    for r in passed[:args.stage2_top]:
        d = np.array(r["d"])
        st = eval_candidate(kin, d, range(N_EP), cache_all)
        st["d"] = r["d"]
        finals.append(st)
        tag = "PASS" if st["fail"] == 0 and st["branch"] == 0 else "----"
        print(f"  2단계 d=({d[0]:+.2f},{d[1]:+.2f},{d[2]:+.2f}) {tag} "
              f"fail={st['fail']} branch={st['branch']} ep_fail={st['ep_fail'][:10]} "
              f"min|q5|={st['min_q5']:.1f}° j3여유={st['min_j3_margin']:.1f}° "
              f"maxΔq={st['max_dq_deg']:.1f}°/fr", flush=True)

    ok = [f for f in finals if f["fail"] == 0 and f["branch"] == 0]
    ok.sort(key=lambda r: (-r["min_q5"], -r["min_j3_margin"]))
    out = {"stage1": results, "stage2": finals,
           "winner": ok[0] if ok else None,
           "elapsed_s": round(time.time() - t0, 1)}
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    if ok:
        w = ok[0]
        print(f"\n최종 선정: d=({w['d'][0]:+.2f},{w['d'][1]:+.2f},{w['d'][2]:+.2f}) "
              f"min|q5|={w['min_q5']:.1f}° j3여유={w['min_j3_margin']:.1f}° "
              f"maxΔq={w['max_dq_deg']:.1f}°/fr", flush=True)
    else:
        print("\n2단계 전체 통과 후보 없음 — 격자 재설계 필요", flush=True)
    print(f"결과 저장: {args.out} ({out['elapsed_s']}s)", flush=True)


if __name__ == "__main__":
    main()
