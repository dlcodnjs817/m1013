#!/usr/bin/env python3
"""손목캠 자세 — 단일 소스. 브래킷 생성기·기하 검증·프리뷰·Isaac 렌더가 전부 여기서 읽는다.

플랜지 로컬 좌표(m). 카메라 규약은 USD(-Z 전방 / +Y 상방).

2026-09-11 (저녁) 확정 — **그리퍼 중앙(x=0) 측면 배치 · 보드 세로(포트레이트) 장착.**
  · 광심   (0, -65, -10)    그리퍼 -Y 옆면 바깥, 플랜지 면 10 mm 뒤 (손목 하우징 r 44.5 밖)
  · 조준   툴축 위 Z=140 mm 지점 → 틸트 21.8°, 대각 성분 0 → 좌우 대칭 구도
  · 롤     화면 가로 = 툴축(Z) 방향, 화면 세로 = 스트로크축(X).  보드를 90° 돌려 단다.
           큐브가 아래(+Z)에서 올라오는 움직임이 4:3 의 **긴 축**에 실려 여유가 확보된다.
           같은 위치에 가로로 달면 0.88, 세로로 달면 0.63 (1.00 = 화면 가장자리).
  · 이전   (35, -45, 0) / 광축 (-0.487, 0.393, 0.780) / 파지점-하단 롤 — 여유 0.647 이었으나
           X 로 35 치우치고 광축이 대각선이라 화면이 기울어 보였다. 사용자 요청으로 중앙화.
"""
import numpy as np

CAM_POS = np.array([0.000, -0.065, -0.010])       # 광심
AIM = np.array([0.0, 0.0, 0.140])                 # 조준점 (툴축 위)
CAM_FWD = (AIM - CAM_POS) / np.linalg.norm(AIM - CAM_POS)
ROLL = 'Z'                                        # 'Z' 세로(포트레이트) · 'X' 가로 · 'grasp' 09-04 규약
HFOV = 85.6                                       # U20CAM-720P, 960×720 중앙크롭 → 640×480
TCP = 0.0725


def basis(pos=None, fwd=None, roll=None, tcp=TCP):
    """카메라 → 플랜지 로컬 4x4.  열: [x=화면 우, y=화면 상, z=-전방, t]."""
    pos = CAM_POS if pos is None else np.asarray(pos, float)
    f = CAM_FWD if fwd is None else np.asarray(fwd, float)
    f = f / np.linalg.norm(f)
    roll = ROLL if roll is None else roll
    if roll == 'grasp':                          # 파지점이 화면 하단 중앙 (09-04)
        v = np.array([0.0, 0.0, tcp]) - pos
        up = -(v - (v @ f) * f); up /= np.linalg.norm(up)
        r = -np.cross(up, f)
    else:
        ax = np.array([0, 0, 1.0]) if roll == 'Z' else np.array([1.0, 0, 0])
        r = ax - (ax @ f) * f; r /= np.linalg.norm(r)
        up = np.cross(r, f)
    T = np.eye(4)
    T[:3, 0] = r; T[:3, 1] = up; T[:3, 2] = -f; T[:3, 3] = pos
    return T


def project(P_fl, T_cam_fl=None, hfov=HFOV, aspect=0.75):
    """플랜지 로컬 점 → 정규화 화면 좌표 (u 우+, v 하+). 1.0 = 가장자리. 카메라 뒤면 None."""
    T = basis() if T_cam_fl is None else T_cam_fl
    Pc = T[:3, :3].T @ (np.asarray(P_fl, float) - T[:3, 3])
    if Pc[2] >= -1e-9:
        return None
    th = np.tan(np.radians(hfov / 2))
    return np.array([(Pc[0] / -Pc[2]) / th, -(Pc[1] / -Pc[2]) / (th * aspect)])


if __name__ == '__main__':
    T = basis()
    print('광심 (mm)', np.round(CAM_POS * 1000, 1), ' 광축', np.round(CAM_FWD, 3),
          ' 틸트 %.1f°' % np.degrees(np.arccos(CAM_FWD[2])), ' 롤', ROLL)
    print('화면 우 =', np.round(T[:3, 0], 3), ' 화면 상 =', np.round(T[:3, 1], 3))
