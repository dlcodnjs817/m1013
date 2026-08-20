#!/usr/bin/env python3
"""v5(EE pose, TX90 프레임) → v6-M1013(joint) 오프라인 IK 일괄 변환 + 검증 리포트.

TX90 convert_v6.py 규약 이식 (MoveIt /compute_ik → m1013_kin 독립 IK 로 교체):
  - 7프레임 이동평균 평활 (배치 스윕과 동일 전처리)
  - 작업 사각형 오프셋 d = (+0.15, -0.15, +0.10) m  (2026-08-20 스윕 + 기하검사 확정)
  - 6Hz 앵커(끝프레임 포함) IK 체인: 직전 해 시드 → j4/j6 3° 넛지 → 2π 접기
    → 브랜치(>90°) 거부 → 섭동/무작위 시드 재시도 (m1013_kin.solve 내장)
  - 30Hz 관절 선형 보간 (앵커 사이), state[t] = action[t-1] (완전 추종 가정)
  - 그리퍼(7번째 열)는 원본 그대로 (state 는 v5 state 그리퍼, action 은 v5 action 그리퍼)
  - 검증: ① 프레임 간 max|Δq| (임계 30°/fr) ② FK 역검증 15샘플/ep (위치·자세)

사용: python3 convert_v6_m1013.py [--episodes 0,1,2] [--out v6_staging]
"""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd

from m1013_kin import M1013Kin, euler_xyz_extrinsic_to_R, rot_err_vec, orient_corr

# 손목 45° 보정 (그리퍼 플랜지 일자 장착, 2026-08-20 사용자 결정): R' = R_data @ CORR.
# 부수효과: min|q5| 10°→50° 급증 (기울인 손목이 특이점 근처였음).
CORR = orient_corr()

V5 = "/home/kim/physical_ai_tools/docker/huggingface/lerobot/dlcodnjs/tx90_act_pick_and_place_v5_ee"
N_EP = 159
OFFSET = np.array([+0.05, -0.15, +0.10])  # 손목 45° 보정 반영 스윕+기하검사 확정 (2026-08-20)
# TCP 길이 (플랜지 link_6 → 핑거 끝). v5 pose 를 TCP 목표로 해석: 플랜지 = p - R@[0,0,TCP].
# LEHR 본체 + 3D 프린팅 핑거 잠정값 — 실물 확정 시 재측정 후 재변환할 것.
TCP = 0.12
ANCHOR_K = 5
SMOOTH_W = 7
NUDGE_DEG = 3.0
GENERIC_SEED = np.deg2rad([0, 20, 100, 0, 60, 0])
JUMP_TH_DEG = 30.0
FK_TOL_M = 0.005
FK_TOL_DEG = 1.0


def smooth_poses(arr, w):
    """(T,7) 의 위치·오일러만 이동평균. v5 는 wrap 수정 완료라 unwrap 불필요하지만 보험으로 적용."""
    if w <= 1:
        return arr
    out = arr.copy()
    eul = np.unwrap(arr[:, 3:6], axis=0)
    ker = np.ones(w) / w
    pad = w // 2
    for k in range(3):
        col = np.pad(arr[:, k], pad, mode="edge")
        out[:, k] = np.convolve(col, ker, mode="valid")[:len(arr)]
        cole = np.pad(eul[:, k], pad, mode="edge")
        out[:, k + 3] = np.convolve(cole, ker, mode="valid")[:len(arr)]
    return out


def convert_episode(kin, ep):
    df = pd.read_parquet(f"{V5}/data/chunk-000/episode_{ep:06d}.parquet")
    st = np.stack(df["observation.state"]).astype(float)
    ac = np.stack(df["action"]).astype(float)
    T = len(df)
    st_s = smooth_poses(st, SMOOTH_W)
    ac_s = smooth_poses(ac, SMOOTH_W)
    ac_pos = ac_s[:, :3] + OFFSET

    anchors = list(range(0, T, ANCHOR_K))
    if anchors[-1] != T - 1:
        anchors.append(T - 1)

    # action 만 IK 체인 (state 는 OMX 측정 지터 배제 위해 action[t-1] 로 재정의)
    sols = {}
    seed = GENERIC_SEED.copy()
    started = False
    fails = branches = 0
    min_q5 = np.inf
    for t in anchors:
        base = seed.copy()
        if started:  # 손목 림 드리프트 보험: j4/j6 를 0 쪽으로 3° 당긴 시드
            for k in (3, 5):
                base[k] -= np.sign(base[k]) * min(np.deg2rad(NUDGE_DEG), abs(base[k]))
        R = euler_xyz_extrinsic_to_R(*ac_s[t, 3:6]) @ CORR
        p_flange = ac_pos[t] - R @ np.array([0.0, 0.0, TCP])
        q, stt = kin.solve(p_flange, R, base, branch_deg=90 if started else 360)
        if stt == "fail":
            fails += 1
            continue
        if stt == "branch":
            branches += 1
            continue  # 브랜치 해는 채택하지 않음 (이웃 보간으로 메움)
        sols[t] = q
        seed = q
        started = True
        min_q5 = min(min_q5, abs(q[4]))

    n_anchor = len(anchors)
    if len(sols) < 0.95 * n_anchor or not sols:
        return None, dict(ep=int(ep), status="FAIL", fails=fails, branches=branches)
    ts_sorted = sorted(sols.keys())
    max_gap = max((b - a for a, b in zip(ts_sorted, ts_sorted[1:])), default=T)
    if max_gap > 2 * ANCHOR_K:
        return None, dict(ep=int(ep), status="FAIL_GAP", fails=fails, branches=branches,
                          max_gap=int(max_gap))

    # 앵커 → 30Hz 관절 선형 보간 (풀린 앵커 기준, 실패 앵커는 이웃 보간으로 자동 메움)
    ts = np.array(ts_sorted)
    J = np.stack([sols[t] for t in ts])
    ac_j = np.empty((T, 6))
    idx = np.arange(T)
    for k in range(6):
        ac_j[:, k] = np.interp(idx, ts, J[:, k])
    st_j = np.vstack([ac_j[:1], ac_j[:-1]])  # state[t] = action[t-1]

    # 검증 ①: 프레임 간 최대 관절 이동
    max_dq = float(np.degrees(np.max(np.abs(np.diff(ac_j, axis=0))))) if T > 1 else 0.0

    # 검증 ②: FK 역검증 (보간 프레임 포함 15샘플) — 목표 TCP pose 대비
    perr, aerr = [], []
    for t in np.linspace(0, T - 1, 15).astype(int):
        Tm = kin.fk(ac_j[t])
        tcp_p = Tm[:3, 3] + Tm[:3, :3] @ np.array([0.0, 0.0, TCP])
        perr.append(float(np.linalg.norm(tcp_p - ac_pos[t])))
        R_tgt = euler_xyz_extrinsic_to_R(*ac_s[t, 3:6]) @ CORR
        aerr.append(float(np.degrees(np.linalg.norm(rot_err_vec(R_tgt, Tm[:3, :3])))))

    new = df.copy()
    new["observation.state"] = [
        np.concatenate([st_j[t], [st[t, 6]]]).astype(np.float32) for t in range(T)]
    new["action"] = [
        np.concatenate([ac_j[t], [ac[t, 6]]]).astype(np.float32) for t in range(T)]

    rep = dict(ep=int(ep), status="OK", frames=int(T), anchors=int(n_anchor),
               solved=len(sols), fails=fails, branches=branches,
               max_dq_deg=round(max_dq, 2),
               fk_pos_err_max_mm=round(max(perr) * 1000, 2),
               fk_ang_err_max_deg=round(max(aerr), 3),
               min_q5_deg=round(float(np.degrees(min_q5)), 2))
    return new, rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", default=None)
    ap.add_argument("--out", default="/home/kim/tx90/m1013/v6_staging")
    args = ap.parse_args()
    eps = ([int(x) for x in args.episodes.split(",")] if args.episodes else list(range(N_EP)))

    os.makedirs(f"{args.out}/data/chunk-000", exist_ok=True)
    kin = M1013Kin()
    t0 = time.time()
    reports = []
    for ep in eps:
        df, rep = convert_episode(kin, ep)
        reports.append(rep)
        if df is not None:
            df.to_parquet(f"{args.out}/data/chunk-000/episode_{ep:06d}.parquet")
        flag = ("" if rep["status"] == "OK" and rep["max_dq_deg"] <= JUMP_TH_DEG
                and rep["fk_pos_err_max_mm"] <= FK_TOL_M * 1000
                and rep["fk_ang_err_max_deg"] <= FK_TOL_DEG else "  <<< CHECK")
        print(f"ep{ep:03d} {rep['status']} " +
              (f"maxΔq={rep['max_dq_deg']:5.1f}° fk={rep['fk_pos_err_max_mm']:4.1f}mm/"
               f"{rep['fk_ang_err_max_deg']:.2f}° min|q5|={rep['min_q5_deg']:4.1f}° "
               f"fail={rep['fails']} br={rep['branches']}" if rep["status"] == "OK"
               else str(rep)) + flag, flush=True)

    ok = [r for r in reports if r["status"] == "OK"]
    summary = dict(
        n_ok=len(ok), n_total=len(eps),
        offset_m=OFFSET.tolist(), tcp_m=TCP, anchor_k=ANCHOR_K, smooth_window=SMOOTH_W,
        nudge_deg=NUDGE_DEG, state_def="action[t-1] (perfect tracking)",
        max_dq_deg=max((r["max_dq_deg"] for r in ok), default=-1),
        fk_pos_err_max_mm=max((r["fk_pos_err_max_mm"] for r in ok), default=-1),
        fk_ang_err_max_deg=max((r["fk_ang_err_max_deg"] for r in ok), default=-1),
        min_q5_deg=min((r["min_q5_deg"] for r in ok), default=-1),
        total_fails=sum(r["fails"] for r in reports),
        total_branches=sum(r["branches"] for r in reports),
        elapsed_s=round(time.time() - t0, 1))
    json.dump(dict(summary=summary, episodes=reports),
              open(f"{args.out}/report.json", "w"), indent=1)
    print("\nSUMMARY:", json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
