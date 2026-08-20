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
TABLE_TOP_Z = 0.332 - 0.0574 + OFFSET[2]  # OMX 실물 상판의 M1013 프레임 높이 = 0.3766


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, default=0)
    ap.add_argument("--cube-size", type=float, default=0.035)
    ap.add_argument("--tip-mode", choices=["straight", "deep", "center", "bent"], default="straight",
                    help="straight: 일자 그리퍼(손목 45° 보정 데이터셋용, 권장) / 나머지: 구버전")
    args = ap.parse_args()

    d6 = pd.read_parquet(f"/home/kim/m1013/v6_staging/data/chunk-000/episode_{args.ep:06d}.parquet")
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

    # 핑거 연장 F 와 큐브 배치 (실측 큐브 35mm; 6cm 는 초기 추정 재현용)
    CUBE = args.cube_size
    cube_c_z = TABLE_TOP_Z + CUBE / 2
    tc = t_close[0] if t_close else 0
    to = t_open[-1] if t_open else len(joints) - 1
    # 실제 파지 순간 = 닫힘 완료 근처 (전이 후 ~15프레임, z 최저 부근)
    tg = min(tc + 15, len(joints) - 1)
    Rg = euler_xyz_extrinsic_to_R(*ac5[tg, 3:6])
    Ro = euler_xyz_extrinsic_to_R(*ac5[to, 3:6])
    kin = M1013Kin()
    if args.tip_mode == "straight":
        # 손목 45° 보정 데이터셋: 파지 시 플랜지 z 가 세계 수직(±11°) → 빔 = 플랜지 z 방향 일자.
        # 빔 길이 = 파지 순간 마운트(플랜지+0.07)에서 테이블+15mm 까지.
        def grip_axis(t):
            T = kin.fk(joints[t])
            mount = T[:3, 3] + T[:3, :3] @ np.array([0.0, 0.0, 0.07])
            dw = T[:3, :3][:, 2]
            return mount, dw

        m_g, d_g = grip_axis(tg)
        F = float(((TABLE_TOP_Z + 0.015) - m_g[2]) / d_g[2])  # 마운트→팁 길이
        grasp_pick = m_g + d_g * float((cube_c_z - m_g[2]) / d_g[2])
        m_o, d_o = grip_axis(to)
        grasp_place = m_o + d_o * float((cube_c_z - m_o[2]) / d_o[2])
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
             finger_ext=F, flange0=T0, table_top_z=TABLE_TOP_Z, tcp=TCP,
             t_close=tc, t_open=to)
    print(f"ep{args.ep}: {len(joints)}프레임, 닫힘@{t_close}, 열림@{t_open}")
    print(f"상판 z={TABLE_TOP_Z:.4f}, 핑거 연장 F={F:.3f}m (추적점 0.12 + F = 플랜지에서 {TCP+F:.3f}m)")
    print(f"큐브 pick={np.round(cube_pick,3)}, place={np.round(cube_place,3)}")
    print("저장:", out)


if __name__ == "__main__":
    main()
