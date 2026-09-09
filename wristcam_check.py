#!/usr/bin/env python3
"""손목캠 시야 검증 — Isaac 없이 순수 기하로.

  python3 wristcam_check.py [HFOV_deg ...]      기본 85.6

카메라는 설계상 「플랜지 로컬」에 고정돼 있으므로, USD 아티큘레이션도 link_6 prim 도
DELTA 보정도 필요 없다. m1013_kin.fk 로 플랜지 자세만 구하면 끝이다.
(wristcam_solve.py 는 USD 씬에 카메라를 놓느라 DELTA 가 필요했고, 그걸 자세마다
 다시 계산하지 않아 최대 190 mm 어긋난 채 렌더한 이력이 있다 — 2026-09-09 수정)
"""
import sys, glob
import numpy as np
from m1013_kin import M1013Kin

CAM_POS = np.array([0.060, -0.075, 0.005])     # 플랜지 로컬 (m) — 09-04 §8 확정
CAM_FWD = np.array([-0.487, 0.393, 0.780])
FPS, ASPECT = 30.0, 480.0 / 640.0


def cam_basis(gz):
    """wristcam_solve.py 와 동일한 규약(USD: -Z 전방 / +Y 상방)."""
    f = CAM_FWD / np.linalg.norm(CAM_FWD)
    v = np.array([0.0, 0.0, gz]) - CAM_POS
    up = -(v - (v @ f) * f); up /= np.linalg.norm(up)
    yc = np.cross(up, f); yc /= np.linalg.norm(yc)
    T = np.eye(4)
    T[:3, 0] = -yc; T[:3, 1] = up; T[:3, 2] = -f; T[:3, 3] = CAM_POS
    return T


def project(P_world, T_fl, T_cam_fl, hfov_deg):
    """월드 점 → 정규화 화면 좌표 (u: 우+, v: 아래+). 뒤쪽이면 None."""
    P_fl = T_fl[:3, :3].T @ (P_world - T_fl[:3, 3])
    R, t = T_cam_fl[:3, :3], T_cam_fl[:3, 3]
    P_c = R.T @ (P_fl - t)
    if P_c[2] >= -1e-9:
        return None                                   # 카메라 뒤
    th = np.tan(np.radians(hfov_deg / 2.0))
    u = (P_c[0] / -P_c[2]) / th
    v = -(P_c[1] / -P_c[2]) / (th * ASPECT)
    return np.array([u, v])


def main(hfovs):
    kin = M1013Kin()
    files = sorted(glob.glob('replay_ep*.npz'))
    print('에피소드 %d개 · 카메라 플랜지로컬 (%.0f, %.0f, %.0f) mm\n'
          % (len(files), *(CAM_POS * 1000)))
    for hf in hfovs:
        print('=== HFOV %.1f°  (VFOV %.1f°) ==='
              % (hf, 2 * np.degrees(np.arctan(np.tan(np.radians(hf / 2)) * ASPECT))))
        print('%-16s %-7s %-24s %-24s %s'
              % ('episode', '프레임', '파지 시 (u, v)', '최종 2초 |u|max |v|max', '판정'))
        worst = 0.0
        for fn in files:
            d = np.load(fn)
            J, TC = d['joints'], int(d['t_close'])
            cube = d['cube_pick'].astype(float)
            T_cam_fl = cam_basis(float(d['tcp']))
            n = int(2.0 * FPS)                        # 최종 2초
            rng = range(max(0, TC - n), min(len(J), TC + 16))
            uv = [project(cube, kin.fk(J[t]), T_cam_fl, hf) for t in rng]
            inside = [p for p in uv if p is not None]
            if not inside:
                print('%-16s  (전 구간 카메라 뒤)' % fn); continue
            A = np.array(inside)
            g = project(cube, kin.fk(J[min(TC + 15, len(J) - 1)]), T_cam_fl, hf)
            um, vm = np.abs(A[:, 0]).max(), np.abs(A[:, 1]).max()
            worst = max(worst, um, vm)
            ok = um < 1.0 and vm < 1.0
            print('%-16s %-7d (%+.2f, %+.2f)%11s %5.2f  %5.2f%12s   %s'
                  % (fn.replace('replay_', '').replace('.npz', ''), len(inside),
                     g[0], g[1], '', um, vm, '', 'OK' if ok else '★프레임 이탈'))
        print('  → 최악값 %.2f  (1.00 이 화면 가장자리)  %s\n'
              % (worst, '전 에피소드 통과' if worst < 1.0 else '이탈 발생'))


if __name__ == '__main__':
    main([float(x) for x in sys.argv[1:]] or [85.6])
