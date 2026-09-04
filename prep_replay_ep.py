#!/usr/bin/env python3
"""Isaac Sim 물리 재생용 에피소드 데이터 준비 → .npz

포함: joint 궤적(30Hz), 그리퍼 개폐(이진), 큐브 pick/place 위치(그리퍼 전이 시점의
TCP 위치), 시작 자세의 플랜지 pose (그리퍼 초기 배치용).
사용: python3 prep_replay_ep.py [--ep 0]
"""
import argparse

import numpy as np
import pandas as pd

from m1013_kin import M1013Kin, euler_xyz_extrinsic_to_R
from convert_v6_m1013 import OFFSET, TCP, V5, smooth_poses, SMOOTH_W

GRIP_TH = 0.459

# ★ 2026-09-04 정정. 종전 `0.332 - 0.0574 + OFFSET[2]` (= 0.3746) 는 두 군데가 틀렸다:
#   · 0.332 는 v5 궤적 z 최소인데 이건 상판이 아니라 HOME 자세 높이다
#     (OMX 프레임 z 최저점의 xy 가 (0.07, 0.00) — 베이스 바로 옆)
#   · 0.0574 는 OMX 베이스 프레임의 개폐 전이 z 평균이라 v5 프레임 값에서 뺄 수 없다
#   이 오차(-87.8mm)가 종전 finger_ext F=0.13883 을 부풀린 원인이었다.
#
# 올바른 기준면: v5 개폐 전이 시점 z 평균 = 큐브 중심면 (159ep · 338 전이).
# OMX 프레임 0.0574 (Umeyama 4코너 기준면) 의 v5 대응값.
GRIP_PLANE_V5 = 0.3799
GRIP_PLANE_Z = GRIP_PLANE_V5 + OFFSET[2]   # M1013 프레임 큐브 중심면 = 0.4799

# MHF2-16D2 + 핑거 어태치먼트 실물 CAD (2026-09-03 확정, 플랜지 로컬 m).
# 종전에는 핑거 길이 F 를 파지 기하에 맞춰 피팅했으나, 상판을 바로잡으면 팁 목표가
# 마운트와 겹쳐 F→0 으로 붕괴한다. 피팅을 버리고 실물 치수를 그대로 쓴다.
BODY_XYZ = (0.142, 0.050, 0.033)   # 그리퍼 몸체 외형
BODY_Z0, BODY_Z1 = 0.012, 0.045    # 몸체 구간 (0~12 는 어댑터)
JAW_Z0, JAW_Z1 = 0.045, 0.083      # 조 구간, 조 끝 = TCP 기준면
JAW_W, JAW_T = 0.030, 0.01325      # 조 폭(y) / 두께(x)
JAW_GAP_CLOSED = 0.0335            # 닫힘 시 조 안쪽면 간격 (35mm 큐브 1.5mm 압착)
JAW_STROKE_HALF = 0.032            # 편측 스트로크 (전체 64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, default=0)
    ap.add_argument("--cube-size", type=float, default=0.035)
    ap.add_argument("--staging", default="/home/kim/m1013/v6_staging_tcp0675",
                    help="TCP 정정(0.0675) 변환 결과. 구 v6_staging 은 TCP=0.12 규약이라 호환 안 됨")
    ap.add_argument("--tip-mode", choices=["straight", "deep", "center", "bent"], default="straight",
                    help="straight: 일자 그리퍼(손목 45° 보정 데이터셋용, 권장) / 나머지: 구버전")
    args = ap.parse_args()

    d6 = pd.read_parquet(f"{args.staging}/data/chunk-000/episode_{args.ep:06d}.parquet")
    ac6 = np.stack(d6["action"]).astype(float)          # (T,7) joint6 + gripper
    joints = ac6[:, :6]
    grip = ac6[:, 6]
    closed = (grip < GRIP_TH).astype(int)

    # pick/place = 그리퍼 닫힘/열림 전이 시점의 TCP 위치 (v5 pose + 오프셋)
    d5 = pd.read_parquet(f"{V5}/data/chunk-000/episode_{args.ep:06d}.parquet")
    ac5 = smooth_poses(np.stack(d5["action"]).astype(float), SMOOTH_W)
    tcp_pos = ac5[:, :3] + OFFSET
    trans = np.where(np.diff(closed) != 0)[0]
    t_close = [t for t in trans if closed[t + 1] == 1]
    t_open = [t for t in trans if closed[t + 1] == 0]
    pick = tcp_pos[t_close[0]] if t_close else tcp_pos[0]
    place = tcp_pos[t_open[-1]] if t_open else tcp_pos[-1]

    # 큐브 배치. TCP 규약 정정(추적점 = 조 사이 파지점) 이후로는 파지점이
    # 플랜지 로컬 z = TCP 에 있음이 변환으로 보장되므로 피팅이 필요 없다.
    CUBE = args.cube_size
    TABLE_TOP_Z = GRIP_PLANE_Z - CUBE / 2      # = 0.4624 (35mm 큐브)
    cube_c_z = GRIP_PLANE_Z
    tc = t_close[0] if t_close else 0
    to = t_open[-1] if t_open else len(joints) - 1
    # 실제 파지 순간 = 닫힘 완료 근처 (전이 후 ~15프레임, z 최저 부근)
    tg = min(tc + 15, len(joints) - 1)
    Rg = euler_xyz_extrinsic_to_R(*ac5[tg, 3:6])
    Ro = euler_xyz_extrinsic_to_R(*ac5[to, 3:6])
    kin = M1013Kin()
    if args.tip_mode == "straight":
        # 실물 기하: 조는 플랜지 로컬 z JAW_Z0~JAW_Z1, 파지점은 z=TCP.
        # 큐브는 상판 위에 있으므로 공구축을 큐브 중심 높이로 투영해 xy 를 잡는다.
        def axis_at(t, z_world):
            T = kin.fk(joints[t])
            p0, dw = T[:3, 3], T[:3, :3][:, 2]
            return p0 + dw * float((z_world - p0[2]) / dw[2])

        F = JAW_Z1 - JAW_Z0                       # 조 길이 38mm (종전 피팅값 대체)
        grasp_pick = axis_at(tg, cube_c_z)
        grasp_place = axis_at(to, cube_c_z)
    elif args.tip_mode == "bent":
        # 꺾인 빔은 파지 시 세계 수직 → 그립 xy 가 높이에 무관. 그립 라인 = 마운트 + s*(R@D_LOCAL)
        D_LOCAL = np.array([0.705, -0.027, 0.708]); D_LOCAL /= np.linalg.norm(D_LOCAL)

        def grip_point(t):
            T = kin.fk(joints[t])
            mount = T[:3, 3] + T[:3, :3] @ np.array([0.0, 0.0, 0.07])
            dw = T[:3, :3] @ D_LOCAL
            s = (cube_c_z - mount[2]) / dw[2]
            return mount + s * dw

        F = 0.125
        grasp_pick = grip_point(tg)
        grasp_place = grip_point(to)
    elif args.tip_mode == "center":
        # 핑거끝 = 큐브 중심 (6cm 초기 구성 재현)
        F = float((cube_c_z - tcp_pos[tg][2]) / Rg[2, 2])
        grasp_pick = tcp_pos[tg] + Rg[:, 2] * F
        grasp_place = tcp_pos[to] + Ro[:, 2] * float((cube_c_z - tcp_pos[to][2]) / Ro[2, 2])
    else:
        # 핑거끝 테이블+22mm (틸트 시 팁 '모서리'가 11mm 더 내려가므로 모서리 기준 +11mm 확보;
        # +12mm 로 하면 모서리가 테이블을 파고들어 핑거가 튕김 — 갭 실측으로 확인)
        tip_target_z = TABLE_TOP_Z + 0.022
        F = float((tip_target_z - tcp_pos[tg][2]) / Rg[2, 2])
        grasp_pick = tcp_pos[tg] + Rg[:, 2] * float((cube_c_z - tcp_pos[tg][2]) / Rg[2, 2])
        grasp_place = tcp_pos[to] + Ro[:, 2] * float((cube_c_z - tcp_pos[to][2]) / Ro[2, 2])
    cube_pick = np.array([grasp_pick[0], grasp_pick[1], cube_c_z])
    cube_place = np.array([grasp_place[0], grasp_place[1], cube_c_z])
    T0 = kin.fk(joints[0])

    out = f"/home/kim/m1013/replay_ep{args.ep:03d}.npz"
    np.savez(out, joints=joints, grip=grip, grip_closed=closed,
             cube_pick=cube_pick, cube_place=cube_place, cube_size=CUBE,
             finger_ext=F, finger_z0=JAW_Z0, flange0=T0,
             table_top_z=TABLE_TOP_Z, tcp=TCP,
             body_xyz=np.array(BODY_XYZ), body_z=np.array([BODY_Z0, BODY_Z1]),
             jaw_wt=np.array([JAW_W, JAW_T]),
             jaw_gap_closed=JAW_GAP_CLOSED, jaw_stroke_half=JAW_STROKE_HALF,
             t_close=tc, t_open=to)
    print(f"ep{args.ep}: {len(joints)}프레임, 닫힘@{t_close}, 열림@{t_open}")
    print(f"상판 z={TABLE_TOP_Z:.4f}, 큐브 중심면 z={cube_c_z:.4f}")
    print(f"조 {JAW_Z0*1000:.0f}~{JAW_Z1*1000:.0f}mm, 파지점 {TCP*1000:.1f}mm, "
          f"닫힘 갭 {JAW_GAP_CLOSED*1000:.1f}mm (플랜지 로컬)")
    print(f"큐브 pick={np.round(cube_pick,3)}, place={np.round(cube_place,3)}")
    print("저장:", out)


if __name__ == "__main__":
    main()
