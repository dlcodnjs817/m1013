#!/usr/bin/env python3
"""스크립트 전문가 — 큐브 위치가 주어지면 M1013 관절 궤적(30 Hz)을 만든다. gen_isaac_demos / eval(--oracle) 공용.
사람 시연의 불완전함을 일부러 흉내 낸다: 손목 기울기 N(0,6°)(v6 중앙값 9°), 웨이포인트 지터, 저주파 흔들림, 속도 ±20%, 그리퍼 5프레임 램프.
"""
import numpy as np
from m1013_kin import M1013Kin
import wristcam_pose as WP

FPS = 30; CUBE = 0.035; TCP = WP.TCP
G_OPEN, G_CLOSED, G_TH, G_RAMP = 0.69, -0.02, 0.459, 5
PICK_BOX = np.array([[0.706, -0.325], [0.908, -0.200]])      # v6 159 ep 실측 (TCP, m)
PLACE_BOX = np.array([[0.684, -0.278], [0.877, 0.042]])
GRASP_YAW0 = np.radians(158.8)                               # v6 파지 시 플랜지 x축 yaw 중앙값
Q0S = np.load('/home/kim/m1013/sim_out/v6_start_q.npy')
kin = M1013Kin()


# ============================ 전문가 ============================
def minjerk(n):
    s = np.linspace(0, 1, n); return 10 * s**3 - 15 * s**4 + 6 * s**5


def rotz(a):
    c, s = np.cos(a), np.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def rot_axis(axis, a):
    axis = axis / np.linalg.norm(axis); K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * (K @ K)


def slerp(R0, R1, s):
    from scipy.spatial.transform import Rotation as Rt, Slerp
    return Slerp([0, 1], Rt.from_matrix([R0, R1]))(s).as_matrix()


def expand(box, k):
    c = box.mean(0); return c + (box - c) * k


def grasp_R(cube_yaw, tilt_dir, tilt):
    """플랜지 z 가 아래(-Z), x 축 yaw 는 큐브 yaw 의 90° 배수 중 v6 관습(159°)에 가장 가까운 것. 사람 손처럼 살짝 기울임."""
    cands = [cube_yaw + k * np.pi / 2 for k in range(-4, 5)]
    psi = min(cands, key=lambda p: abs((p - GRASP_YAW0 + np.pi) % (2 * np.pi) - np.pi))
    R = rotz(psi) @ np.diag([1.0, -1.0, -1.0])        # x=yaw 방향, z=아래
    return rot_axis(np.array([np.cos(tilt_dir), np.sin(tilt_dir), 0]), tilt) @ R


def expert(rng, cube_pick, cube_yaw, cube_place, table_z):
    """→ (q[T,6], grip[T], t_close, t_open, cube_pose_fn) 또는 None(IK 실패)."""
    zc = table_z + CUBE / 2
    q_start = Q0S[rng.integers(len(Q0S))] + rng.normal(0, np.radians(1.0), 6)
    T0 = kin.fk(q_start); p0 = T0[:3, 3] + T0[:3, 2] * TCP; R0 = T0[:3, :3]
    tilt = abs(rng.normal(0, np.radians(6))); tdir = rng.uniform(0, 2 * np.pi)
    Rg = grasp_R(cube_yaw, tdir, tilt)
    Rp = grasp_R(cube_yaw + rng.normal(0, np.radians(10)), rng.uniform(0, 2 * np.pi), abs(rng.normal(0, np.radians(6))))
    lift = rng.uniform(0.06, 0.11)
    jit = lambda s: rng.normal(0, s, 3) * np.array([1, 1, 0.5])
    P_pick = np.array([cube_pick[0], cube_pick[1], zc]); P_place = np.array([cube_place[0], cube_place[1], zc])
    tscale = rng.uniform(0.85, 1.3)
    # (목표 TCP, 목표 R, 구간 시간 s, 구간 뒤 그리퍼 상태)
    W_ = [(P_pick + [0, 0, lift] + jit(0.01), Rg, 3.0, 'open'),
          (P_pick + jit(0.003), Rg, 1.3, 'open'), (None, None, 0.45, 'close'),
          (P_pick + [0, 0, lift] + jit(0.01), Rg, 1.2, 'closed'),
          (P_place + [0, 0, lift] + jit(0.012), Rp, 3.0, 'closed'),
          (P_place + jit(0.004), Rp, 1.3, 'closed'), (None, None, 0.45, 'open_'),
          (P_place + [0, 0, lift] + jit(0.01), Rp, 1.2, 'open'), (None, None, 0.5, 'open')]
    qs, grips, p_cur, R_cur, q_cur = [], [], p0.copy(), R0.copy(), q_start.copy()
    g_cur = G_OPEN; t_close = t_open = None
    # 저주파 흔들림 (사람 손)
    wob_f = rng.uniform(0.15, 0.4, 3); wob_a = rng.uniform(0.0, 0.004, 3); wob_p = rng.uniform(0, 2 * np.pi, 3)
    for (p_tgt, R_tgt, dur, gstate) in W_:
        n = max(2, int(round(dur * tscale * FPS)))
        if p_tgt is None:                                   # 정지 구간 (그리퍼 동작)
            # 상태를 먼저 바꾸고 정지 프레임 전부를 새 상태로 채운다. 램프는 아래서 앞 5프레임에 덮어쓴다.
            # (09-11 버그: 바꾸기 전 값으로 채워 램프 뒤 10여 프레임이 다시 '열림'이 됐다 — 평가기가 놓기로 오판)
            if gstate == 'close': t_close = len(qs); g_cur = G_CLOSED
            elif gstate == 'open_': t_open = len(qs); g_cur = G_OPEN
            for i in range(n):
                qs.append(q_cur.copy()); grips.append(g_cur)
            continue
        s = minjerk(n + 1)[1:]
        for i in range(n):
            tt = len(qs) / FPS
            p = p_cur + (p_tgt - p_cur) * s[i] + wob_a * np.sin(2 * np.pi * wob_f * tt + wob_p)
            R = slerp(R_cur, R_tgt, s[i])
            p_fl = p - R[:, 2] * TCP                        # TCP → 플랜지
            q, st = kin.solve(p_fl, R, q_cur)
            if st != 'ok' or np.abs(q - q_cur).max() > np.radians(6):
                return None
            q_cur = q; qs.append(q.copy()); grips.append(g_cur)
        p_cur, R_cur = p_tgt.copy(), R_tgt.copy()
    q = np.array(qs); grip = np.array(grips, float)
    # 그리퍼 값 램프 (v6 전이 ~5 프레임)
    for t_ev, (a, b) in ((t_close, (G_OPEN, G_CLOSED)), (t_open, (G_CLOSED, G_OPEN))):
        for k in range(G_RAMP):
            if t_ev + k < len(grip): grip[t_ev + k] = a + (b - a) * (k + 1) / G_RAMP
    return q, grip, t_close, t_open


def sample_episode(rng, table_z, ws_scale=1.5):
    for _ in range(20):
        pk = rng.uniform(*expand(PICK_BOX, ws_scale)); pl = rng.uniform(*expand(PLACE_BOX, ws_scale))
        if np.linalg.norm(pk - pl) < 0.08: continue
        yaw = rng.uniform(0, np.pi / 2)
        r = expert(rng, pk, yaw, pl, table_z)
        if r is not None:
            return dict(pick=pk, place=pl, yaw=yaw, q=r[0], grip=r[1], t_close=r[2], t_open=r[3])
    return None


