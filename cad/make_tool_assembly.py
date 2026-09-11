#!/usr/bin/env python3
"""툴 어셈블리 재생성 + 전 부품 간섭 검증 — M1013 플랜지 로컬(mm).

2026-09-11 신설. 기존 `tool_assembly_flangelocal.stl` 은 09-07 14:55 판이라
핑거 수정(09-07 17:17, 판 43.0→41.8)과 밸브 브래킷 재생성(09-09 09:56, 스페이서 6 mm)
이후로 갱신된 적이 없고, 만든 스크립트도 남아 있지 않았다. 그래서 다시 만든다.

좌표 매핑 (전부 원본 STEP 자체 좌표 → 플랜지 로컬, 순수 회전 + 평행이동)
  어댑터   (x, -y, 12 - z)          자체 좌표는 그리퍼 면이 z=0 · 스피곳 z 12~16 으로 뒤집혀 있다
  그리퍼   (z, -x, 12 - y)          SMC 원본은 스트로크축이 Z · 장착면이 Y=0
  핑거     (x, -y, 53 - z)          자체 좌표는 판 밑면 z=0 · 블록 밑면 z=8 · 조 끝 z=-30
  밸브/손목캠 브래킷                  이미 플랜지 로컬

검산 (스크립트가 자동 확인)
  · 어댑터   스피곳 -4~0 · 판 0~12
  · 그리퍼   옆면 Y=±25 · 배면에서 20 → 측면 M5 가 Z=32 · 몸체 Z 12~40.3
  · 핑거     조 끝 Z=83.0 · 완전 닫힘 좌우 판 간격 2.40
"""
import sys
import numpy as np
import cadquery as cq

Q = cq.importers.importStep


O = (0, 0, 0)
AX, AZ = (1, 0, 0), (0, 0, 1)


def to_adapter(sh):
    """(x, -y, 12 - z) = X축 180도 회전 후 Z +12"""
    return sh.rotate(O, AX, 180).translate((0, 0, 12))


def to_gripper(sh):
    """(z, -x, 12 - y) = X축 -90도 → Z축 -90도 → Z +12"""
    return sh.rotate(O, AX, -90).rotate(O, AZ, -90).translate((0, 0, 12))


def to_finger(sh):
    """(x, -y, 53 - z) = X축 180도 회전 후 Z +53"""
    return sh.rotate(O, AX, 180).translate((0, 0, 53))


parts = {}
parts['어댑터'] = to_adapter(Q('cad/adapter_m1013_mhf2.step').val())

g = Q('cad/1/MHF2-16D2(64_0_).stp')
sols = sorted(g.solids().vals(), key=lambda s: -s.Volume())
parts['그리퍼 몸체'] = to_gripper(sols[0])
STROKE = 32.0                                   # 조 1개당 이동량 (개방 71.4 → 닫힘 39.4)
# CADENAS 조 솔리드는 몸체 안쪽 가이드 레일까지 한 덩어리로 포함한다. 두 조를 각각 닫힘
# 위치로 옮기면 **모델 안에서 레일끼리 겹친다** (실물은 서로 엇갈려 들어간다). 레일은 검증
# 대상이 아니므로 몸체 밖으로 나온 블록(Z >= 40.3)만 남겨 쓴다.
BLOCK_Z = 40.3
for i, s in enumerate(sols[1:3]):
    t = to_gripper(s)
    bb = t.BoundingBox()
    d = -STROKE if bb.xmax > 60 else +STROKE    # 닫힘 위치로
    t = t.translate((d, 0, 0))
    keep = cq.Workplane('XY').transformed(offset=(0, 0, BLOCK_Z + 100)).box(400, 400, 200).val()
    parts['그리퍼 조%d' % (i + 1)] = t.intersect(keep)

parts['핑거 좌'] = to_finger(Q('cad/finger_left.step').val())
parts['핑거 우'] = to_finger(Q('cad/finger_right.step').val())
parts['밸브 브래킷'] = Q('cad/valve_bracket_sy5120.step').val()
parts['손목캠 브래킷'] = Q('cad/wristcam_bracket_v2.step').val()

print('=== 부품 배치 (플랜지 로컬) ===')
for k, v in parts.items():
    b = v.BoundingBox()
    print('  %-14s X %7.1f~%7.1f  Y %7.1f~%7.1f  Z %7.1f~%7.1f  %9.1f mm^3'
          % (k, b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax, v.Volume()))

# ---------------- 검산 ----------------
ok = True
def chk(name, got, want, tol=0.05):
    global ok
    good = abs(got - want) < tol
    ok &= good
    print('  %-40s %8.2f  (기대 %.2f)  %s' % (name, got, want, '✅' if good else '❌'))

print('\n=== 좌표 매핑 검산 ===')
a = parts['어댑터'].BoundingBox()
chk('어댑터 스피곳 끝 Z', a.zmin, -4.0)
chk('어댑터 판 상면 Z (= 그리퍼 접합면)', a.zmax, 12.0)
gb = parts['그리퍼 몸체'].BoundingBox()
chk('그리퍼 옆면 |Y|', gb.ymax, 25.0)
chk('그리퍼 몸체 기준면 Z', gb.zmin, 12.0)
chk('그리퍼 배면에서 20 → 측면 M5 Z', gb.zmin + 20.0, 32.0)
fl, fr = parts['핑거 좌'].BoundingBox(), parts['핑거 우'].BoundingBox()
chk('핑거 조 끝 Z', fl.zmax, 83.0)
chk('완전 닫힘 좌우 판 간격', fr.xmin - fl.xmax, 2.40)

# ---------------- 간섭 ----------------
print('\n=== 쌍별 불리언 간섭 (0.000 이어야 정상) ===')
names = list(parts)
bad = []
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        A, B = parts[names[i]], parts[names[j]]
        ba, bb_ = A.BoundingBox(), B.BoundingBox()
        if (ba.xmin > bb_.xmax or bb_.xmin > ba.xmax or ba.ymin > bb_.ymax or
                bb_.ymin > ba.ymax or ba.zmin > bb_.zmax or bb_.zmin > ba.zmax):
            continue                              # BBox 가 안 겹치면 건너뜀
        try:
            v = A.intersect(B).Volume()
        except Exception as e:
            print('  %-14s ↔ %-14s 불리언 실패: %s' % (names[i], names[j], e)); continue
        flag = '✅' if v < 1e-3 else '❌ 간섭'
        print('  %-14s ↔ %-14s %12.4f mm^3  %s' % (names[i], names[j], v, flag))
        if v >= 1e-3:
            bad.append((names[i], names[j], v))

asm = None
for v in parts.values():
    asm = v if asm is None else asm.fuse(v)

# 손목캠 브래킷을 뺀 판도 따로 내보낸다 — 손목캠 시점 렌더에서 브래킷만 색을 달리하려고
nw = None
for k, v in parts.items():
    if k == '손목캠 브래킷':
        continue
    nw = v if nw is None else nw.fuse(v)
cq.exporters.export(cq.Workplane(obj=nw), 'cad/tool_assembly_nowrist.stl', tolerance=0.08)
cq.exporters.export(cq.Workplane(obj=asm), 'cad/tool_assembly_flangelocal.stl', tolerance=0.08)
b = asm.BoundingBox()
print('\n어셈블리 BBox  X %.1f~%.1f  Y %.1f~%.1f  Z %.1f~%.1f' % (b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax))
print('갱신: cad/tool_assembly_flangelocal.stl')
print('\n결과: 검산 %s · 간섭 %s' % ('통과' if ok else '실패', '없음' if not bad else '%d건' % len(bad)))
sys.exit(0 if (ok and not bad) else 1)
