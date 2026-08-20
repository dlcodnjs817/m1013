#!/usr/bin/env python3
"""M1013 기구학 모듈: URDF 기반 FK / 기하 자코비안 / DLS IK.

TX90 v6 파이프라인의 MoveIt /compute_ik 서비스를 대체하는 ROS 없는 독립 구현.
규약:
  - EE 프레임 = link_6 (두산 플랜지, ROS-Industrial tool0 상당). 접근축 = 로컬 +Z (FK로 확인).
  - 표준 m1013.urdf 사용. m1013_isaac_sim.urdf 는 리밋이 좁고(J1 ±120° 등)
    0.45m 받침대 오프셋이 있어 사용 금지.
  - IK 체인 규약은 convert_v6.py 와 동일: 시드 → 2π 접기 → 브랜치(>90°) 거부 → 시드 섭동 재시도.

셀프테스트: python3 m1013_kin.py  (무작위 포즈 IK 복원 검증)
"""
import xml.etree.ElementTree as ET

import numpy as np

URDF = "/home/kim/doosan-robot2/dsr_description2/urdf/m1013.urdf"
# 표준 m1013.urdf 실스펙 리밋
JOINT_LIMITS = np.deg2rad(np.array([
    [-360, 360], [-360, 360], [-160, 160], [-360, 360], [-360, 360], [-360, 360]], float))

# convert_v6.py 와 동일한 시드 섭동 (브랜치 탈출용)
PERTURB = [np.zeros(6),
           np.deg2rad([0, 0, 0, +20, +10, +20]),
           np.deg2rad([0, 0, 0, -20, +10, -20]),
           np.deg2rad([0, +5, -5, 0, +15, 0]),
           np.deg2rad([0, 0, 0, 0, -15, 0]),
           np.deg2rad([0, 0, 0, -20, -10, -20])]


def rpy_to_R(r, p, y):
    cr, sr, cp, sp, cy, sy = np.cos(r), np.sin(r), np.cos(p), np.sin(p), np.cos(y), np.sin(y)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]])


def euler_xyz_extrinsic_to_R(rx, ry, rz):
    """v5 데이터셋 규약: extrinsic xyz 오일러 → R = Rz @ Ry @ Rx."""
    Rx = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
    Ry = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
    Rz = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def orient_corr():
    """그리퍼 일자 장착용 손목 보정 회전 (2026-08-20 결정).

    OMX 데이터의 파지 접근축은 플랜지 로컬 [0.705,-0.027,0.708] (45° 틸트).
    이 회전 A (ẑ→해당 방향 최소 회전) 를 플랜지 목표 자세에 곱해
    R' = R_data @ A 로 IK 를 풀면, 파지 시 플랜지 z 가 세계 수직이 되어
    그리퍼를 표준처럼 플랜지에 일자로 장착할 수 있다.
    """
    d = np.array([0.705, -0.027, 0.708])
    d /= np.linalg.norm(d)
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(z, d)
    s = np.linalg.norm(v)
    c = float(z @ d)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]) / s
    th = np.arccos(c)
    return np.eye(3) + np.sin(th) * K + (1 - c) * (K @ K)


def rot_err_vec(R_tgt, R_cur):
    """회전 오차의 axis-angle 벡터 (world 프레임)."""
    Re = R_tgt @ R_cur.T
    w = np.array([Re[2, 1] - Re[1, 2], Re[0, 2] - Re[2, 0], Re[1, 0] - Re[0, 1]])
    c = np.clip((np.trace(Re) - 1.0) / 2.0, -1.0, 1.0)
    s = np.linalg.norm(w) / 2.0
    ang = np.arctan2(s, c)
    if s < 1e-9:
        if c > 0:
            return np.zeros(3)
        # 180° 부근: 대각에서 축 추출
        ax = np.sqrt(np.maximum(np.diag(Re) + 1.0, 0.0) / 2.0)
        ax /= (np.linalg.norm(ax) + 1e-12)
        return ax * ang
    return w / (2.0 * s) * ang


class M1013Kin:
    def __init__(self, urdf=URDF):
        t = ET.parse(urdf)
        self.A = []  # 각 조인트의 고정 원점 변환 (4x4)
        for j in t.getroot().iter('joint'):
            if j.get('type') != 'revolute':
                continue
            o = j.find('origin')
            xyz = np.array([float(v) for v in (o.get('xyz') or '0 0 0').split()]) if o is not None else np.zeros(3)
            rpy = np.array([float(v) for v in (o.get('rpy') or '0 0 0').split()]) if o is not None else np.zeros(3)
            A = np.eye(4)
            A[:3, :3] = rpy_to_R(*rpy)
            A[:3, 3] = xyz
            self.A.append(A)
        assert len(self.A) == 6, f"revolute 6개 기대, {len(self.A)}개 파싱됨"

    def fk_frames(self, q):
        """각 조인트 회전 적용 직후의 world 변환 6개 + EE(=마지막) 반환."""
        T = np.eye(4)
        frames = []
        for i in range(6):
            T = T @ self.A[i]
            c, s = np.cos(q[i]), np.sin(q[i])
            Rz = np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)
            T = T @ Rz
            frames.append(T.copy())
        return frames

    def fk(self, q):
        return self.fk_frames(q)[-1]

    def jacobian(self, q, frames=None):
        """기하 자코비안 6x6 (v, w) — world 프레임."""
        if frames is None:
            frames = self.fk_frames(q)
        p_ee = frames[-1][:3, 3]
        J = np.zeros((6, 6))
        for i in range(6):
            # 조인트 i의 회전축 = (원점변환 적용 후) 로컬 z. frames[i] 는 회전 포함이지만
            # 회전은 z축을 바꾸지 않으므로 frames[i]의 z열이 곧 축.
            z = frames[i][:3, 2]
            p = frames[i][:3, 3]
            J[:3, i] = np.cross(z, p_ee - p)
            J[3:, i] = z
        return J

    def ik_dls(self, p_tgt, R_tgt, seed, pos_tol=1e-4, rot_tol=1e-3, iters=300):
        """감쇠 최소제곱 IK (오차 비례 적응 감쇠). 수렴 시 (q, True), 실패 시 (마지막 q, False)."""
        q = np.array(seed, float).copy()
        for _ in range(iters):
            frames = self.fk_frames(q)
            T = frames[-1]
            dp = p_tgt - T[:3, 3]
            dw = rot_err_vec(R_tgt, T[:3, :3])
            en = np.linalg.norm(np.concatenate([dp, dw]))
            if np.linalg.norm(dp) < pos_tol and np.linalg.norm(dw) < rot_tol:
                return q, True
            # 특이점 근방에서 자동으로 감쇠가 커지도록 오차에 비례
            lam = 0.02 + 0.2 * min(1.0, en)
            e = np.concatenate([dp, dw])
            J = self.jacobian(q, frames)
            dq = J.T @ np.linalg.solve(J @ J.T + lam * lam * np.eye(6), e)
            n = np.linalg.norm(dq)
            if n > 0.5:  # 스텝 제한 (발산 방지)
                dq *= 0.5 / n
            q += dq
        return q, False

    @staticmethod
    def fold_to_seed(q, seed):
        """각 관절을 시드에 가장 가까운 2π 등가각으로 접고 리밋 안으로 유지."""
        qf = q - 2 * np.pi * np.round((q - seed) / (2 * np.pi))
        for i in range(6):
            lo, hi = JOINT_LIMITS[i]
            if qf[i] < lo:
                qf[i] += 2 * np.pi
            elif qf[i] > hi:
                qf[i] -= 2 * np.pi
            if not (lo <= qf[i] <= hi):
                qf[i] = np.clip(qf[i], lo, hi)
        return qf

    def solve(self, p_tgt, R_tgt, seed, branch_deg=90.0):
        """convert_v6 규약의 완전판: DLS + 접기 + 브랜치 거부 + 섭동 재시도.

        반환: (q, status)  status ∈ {"ok", "branch", "fail"}
          - "ok": 수렴했고 시드에서 90° 이내
          - "branch": 수렴했지만 모든 시도가 90° 초과 (가장 가까운 해 반환)
          - "fail": 수렴 실패
        """
        best_q, best_dev = None, np.inf
        rng = np.random.default_rng(12345)  # 고정 시드 (재현성)
        trials = [seed + p for p in PERTURB] + \
                 [seed + rng.normal(0, np.deg2rad(40), 6) for _ in range(6)]
        for s0 in trials:
            q, ok = self.ik_dls(p_tgt, R_tgt, s0)
            if not ok:
                continue
            qf = self.fold_to_seed(q, seed)
            # 접은 뒤 포즈 재확인 (리밋 클램프로 틀어질 수 있음)
            T = self.fk(qf)
            if np.linalg.norm(T[:3, 3] - p_tgt) > 5e-4 or np.linalg.norm(rot_err_vec(R_tgt, T[:3, :3])) > 5e-3:
                continue
            dev = np.max(np.abs(qf - seed))
            if dev <= np.deg2rad(branch_deg):
                return qf, "ok"
            if dev < best_dev:
                best_q, best_dev = qf, dev
        if best_q is not None:
            return best_q, "branch"
        return np.array(seed, float), "fail"


def _run_cases(kin, cases, rng):
    ok = branch = fail = 0
    perr_max = rerr_max = 0.0
    for q_true in cases:
        T = kin.fk(q_true)
        seed = q_true + rng.normal(0, np.deg2rad(10), 6)
        q, st = kin.solve(T[:3, 3], T[:3, :3], seed)
        if st == "fail":
            fail += 1
            continue
        Tc = kin.fk(q)
        perr_max = max(perr_max, np.linalg.norm(Tc[:3, 3] - T[:3, 3]))
        rerr_max = max(rerr_max, np.linalg.norm(rot_err_vec(T[:3, :3], Tc[:3, :3])))
        if st == "ok":
            ok += 1
        else:
            branch += 1
    return ok, branch, fail, perr_max, rerr_max


def _selftest(n=1000, rng_seed=0):
    rng = np.random.default_rng(rng_seed)
    kin = M1013Kin()

    # (a) 과제형 포즈: 테이블 위 그리퍼 아래보기 (±17° 틸트) — 여기가 실사용 영역, 실패 0 필수
    task_cases = []
    while len(task_cases) < n:
        p = rng.uniform([0.35, -0.35, 0.03], [0.90, 0.35, 0.40])
        rx = np.pi + rng.normal(0, 0.3)
        ry = rng.normal(0, 0.3)
        rz = rng.uniform(-np.pi, np.pi)
        R = euler_xyz_extrinsic_to_R(rx, ry, rz)
        # 도달 가능한지 넉넉한 시드에서 한 번 풀어 자세 확보 (샘플 생성용)
        q0 = np.deg2rad([0, 20, 100, 0, 60, 0])
        q, st = kin.solve(p, R, q0, branch_deg=360)
        if st != "fail":
            task_cases.append(q)
    ok, br, fail, pe, re = _run_cases(kin, task_cases, rng)
    print(f"[task-like] n={len(task_cases)}: ok={ok} branch={br} fail={fail} "
          f"| max pos {pe * 1000:.4f} mm, max rot {np.degrees(re):.4f} deg")
    assert fail == 0, "과제형 포즈에서 IK 실패"
    assert pe < 5e-4 and re < 5e-3, "포즈 오차 허용 초과"

    # (b) 전역 무작위 (특이점 포함) — 리포트만, 실패 소수 허용
    lo = np.deg2rad([-170, -100, -150, -170, -130, -170])
    hi = np.deg2rad([+170, +100, +150, +170, +130, +170])
    rand_cases = [rng.uniform(lo, hi) for _ in range(n)]
    ok, br, fail, pe, re = _run_cases(kin, rand_cases, rng)
    print(f"[random]    n={n}: ok={ok} branch={br} fail={fail} (특이 자세 포함, 참고용) "
          f"| max pos {pe * 1000:.4f} mm, max rot {np.degrees(re):.4f} deg")
    print("PASS")


if __name__ == "__main__":
    _selftest()
