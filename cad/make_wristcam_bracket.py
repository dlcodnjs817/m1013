#!/usr/bin/env python3
"""손목캠 브래킷 생성기 — M1013 플랜지 로컬 좌표(mm).

2026-09-11 전면 재설계. 09-03 판(cad/wristcam_bracket.step)은 카메라 미선정 상태의
임의 패드(34각·M2 28각·렌즈Φ22)를 z=+44 에 두고 있었는데, 09-04 에 풀린 실제 카메라
자세와 전혀 맞지 않아 폐기한다.

설계 근거
  · 카메라   INNOMAKER U20CAM-720P — 32×32 보드 · Ø2.2 나사홀 ×4(피치 미상) · M12 렌즈
  · 광심     (35, -45, 0)  ← 09-11 재배치. 09-04 값(60,-75,+5)은 시야여유 0.898 에
             렌즈 스탠드오프 ±12 mm 를 얹으면 1.03 으로 이탈했다. 재배치판은 0.669.
  · 광축     (-0.487, +0.393, +0.780)  ← 09-04 값 유지. 파지점 직접조준보다 낫다.
  · 체결     그리퍼 -Y 측면 2-M5 (x=±61, z=32, 면 y=-25), M5×8, 탭깊이 5.5
  · 구조     좌우 이어 2개 + 무릎 + 패드로 모이는 A-프레임. **좌우를 잇는 판을 두면 안 된다** —
             y=-27·z=32 의 판 중앙이 화면 (-0.19,-0.28) 로 큐브 궤적과 0.17 까지 겹친다.
  · 나사홀   보드 나사 피치가 미공개라 대각 장공(피치 24~32 수용)으로 처리한다.
"""
import numpy as np
import cadquery as cq

# ---------------- 파라미터 ----------------
CAM = np.array([35.0, -45.0, 0.0])              # 광심
FWD = np.array([-0.487, 0.393, 0.780])          # 광축
TCP = 72.5
LENS_STANDOFF = 15.0    # 보드 앞면 → 광심. ★OMX 리그 카메라로 실측 후 확정할 것
BOARD_T, BOARD = 1.6, 32.0
PAD, PAD_T = 40.0, 5.0
EAR_X, EAR_Z, EAR_Y = 61.0, 32.0, -25.0
WALL = 4.0                                      # 이어 두께 → M5×8 물림 4.0 < 탭 5.5
M5 = 5.5
STRUT_W, STRUT_H = 14.0, 11.0
NOM_PITCH, SLOT_TRAVEL, SLOT_D = 28.0, 3.0, 2.4
NUT_W, NUT_DEPTH = 4.3, 2.0


def cam_frame():
    """wristcam_check.cam_basis 와 동일 규약 — 카메라 x(우)/y(상)/광축."""
    f = FWD / np.linalg.norm(FWD)
    v = np.array([0.0, 0.0, TCP]) - CAM
    up = -(v - (v @ f) * f); up /= np.linalg.norm(up)
    yc = np.cross(up, f); yc /= np.linalg.norm(yc)
    return -yc, up, f                            # xc, yc, f


XC, YC, F = cam_frame()
PAD_FRONT = CAM - F * (LENS_STANDOFF + BOARD_T)  # 보드 뒷면 = 패드 앞면
PAD_CTR = PAD_FRONT - F * (PAD_T / 2.0)


def plane(origin, xdir, normal):
    return cq.Plane(origin=cq.Vector(*origin), xDir=cq.Vector(*xdir), normal=cq.Vector(*normal))


def strut(start, end, w=STRUT_W, h=STRUT_H):
    d = np.array(end) - np.array(start)
    L = float(np.linalg.norm(d)); d /= L
    x = np.cross(d, [0, 0, 1.0])
    if np.linalg.norm(x) < 1e-6:
        x = np.cross(d, [1.0, 0, 0])
    x /= np.linalg.norm(x)
    return cq.Workplane(plane(start, x, d)).rect(w, h).extrude(L)


# ---------------- 이어 2개 ----------------
def ear(sx):
    return (cq.Workplane('XZ', origin=(sx * EAR_X, EAR_Y, EAR_Z))
            .box(22.0, 18.0, WALL, centered=(True, True, False))
            .faces('<Y').workplane(origin=(sx * EAR_X, EAR_Y, EAR_Z))
            )


body = None
for sx in (+1, -1):
    b = (cq.Workplane('XY')
         .transformed(offset=(sx * EAR_X, EAR_Y - WALL / 2, EAR_Z))
         .box(18.0, WALL, 12.0))      # 09-07 에 간섭 0 으로 검증된 구 베이스판 z 26~38 안에 머문다
    body = b if body is None else body.union(b)

# ---------------- 스트럿 2개 (이어 → 무릎 → 패드) ----------------
# 무릎이 없으면 스트럿 단면의 안쪽 모서리가 **어댑터 평판(X±70, Y±35, Z -4~12)** 을 파고든다.
# 2026-09-11 불리언 검증에서 675.1 mm^3 관통으로 잡혔다. 축은 Y=-35 밖이지만 반폭 7 이
# z=12 에서 y=-30.9 까지 들어온다. 무릎으로 Y 를 -50 까지 먼저 빼고 내려간다 (어댑터 여유 6.82 mm).
KNEE_Y, KNEE_Z, KNEE_X = -50.0, 18.0, 57.0
BLEND = 9.0                                     # 무릎에서 두 구간을 겹쳐 solid 가 끊기지 않게


def _u(v):
    return v / np.linalg.norm(v)


for sx in (+1, -1):
    a = np.array([sx * EAR_X, EAR_Y - WALL / 2, EAR_Z])
    knee = np.array([sx * KNEE_X, KNEE_Y, KNEE_Z])
    d1, d2 = _u(knee - a), _u(PAD_CTR - knee)
    body = body.union(strut(a, knee + d1 * BLEND))
    body = body.union(strut(knee - d2 * BLEND, PAD_CTR))

# ---------------- 카메라 패드 ----------------
pad = cq.Workplane(plane(PAD_CTR - F * (-PAD_T / 2), XC, F)).rect(PAD, PAD).extrude(-PAD_T)
body = body.union(pad)

# ---------------- 가공 ----------------
# M5 관통 (Y 축)
for sx in (+1, -1):
    body = body.cut(cq.Workplane('XZ', origin=(sx * EAR_X, EAR_Y + 2, EAR_Z))
                    .circle(M5 / 2).extrude(-(WALL + 4)))

# 케이블/커넥터 도피 — 패드 중앙 관통
body = body.cut(cq.Workplane(plane(PAD_CTR + F * (PAD_T / 2 + 1), XC, F))
                .rect(22.0, 16.0).extrude(-(PAD_T + 2)))

# 보드 고정 대각 장공 ×4 + 배면 너트 채널
r0 = NOM_PITCH / np.sqrt(2.0)
for su in (+1, -1):
    for sv in (+1, -1):
        diag = (su * XC + sv * YC) / np.sqrt(2.0)
        for kind, dia, depth, off in (('slot', SLOT_D, PAD_T + 2, PAD_T / 2 + 1),
                                      ('nut', NUT_W, NUT_DEPTH, -PAD_T / 2 + NUT_DEPTH)):
            for s in (-SLOT_TRAVEL, +SLOT_TRAVEL):
                c = PAD_CTR + diag * (r0 + s) + F * off
                body = body.cut(cq.Workplane(plane(c, XC, F)).circle(dia / 2).extrude(-depth))
            c0 = PAD_CTR + diag * r0 + F * off
            perp = np.cross(diag, F)
            body = body.cut(cq.Workplane(plane(c0, perp, F))
                            .rect(dia, 2 * SLOT_TRAVEL).extrude(-depth))

# 그리퍼 착좌면(y = -25) 안쪽으로 새어나간 살을 잘라낸다 — 스트럿 단면이 이어 근처에서 넘어간다
body = body.cut(cq.Workplane('XY').transformed(offset=(0, 60 + EAR_Y, 0)).box(400, 120, 400))

# 패드의 케이블 구멍이 스트럿 모서리를 얇게 떼어내 부스러기가 생긴다 — 본체만 남긴다
_sol = sorted(body.solids().vals(), key=lambda v: -v.Volume())
if len(_sol) > 1:
    _drop = sum(v.Volume() for v in _sol[1:])
    assert _drop < 0.01 * _sol[0].Volume(), '떨어져 나간 살이 너무 크다: %.1f mm^3' % _drop
    print('부스러기 %d개 (%.1f mm^3) 제거' % (len(_sol) - 1, _drop))
    body = cq.Workplane(obj=_sol[0])

s = body.val()
print('솔리드 %d개 · 부피 %.1f mm^3 · PETG(1.27) %.2f g' % (len(body.solids().vals()), s.Volume(), s.Volume() * 1.27e-3))
bb = s.BoundingBox()
print('BBox  X %.1f~%.1f  Y %.1f~%.1f  Z %.1f~%.1f' % (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
print('패드 중심 (%.1f, %.1f, %.1f) · 보드 뒷면 (%.1f, %.1f, %.1f)' % (*PAD_CTR, *PAD_FRONT))

cq.exporters.export(body, 'cad/wristcam_bracket_v2.step')
cq.exporters.export(body, 'cad/wristcam_bracket_v2.stl', tolerance=0.05)
print('내보냄: cad/wristcam_bracket_v2.step / .stl')
