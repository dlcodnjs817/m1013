#!/usr/bin/env python3
"""손목캠 브래킷 시야 침범 + 로봇 손목 간격 검사.

  python3 wristcam_occlusion.py

브래킷 STEP 정점을 wristcam_pose 카메라에 투영해 화면 안에 들어오는 비율과, 큐브 궤적과의 화면상
최소거리를 잰다. 로봇 손목(link_6) 하우징과의 최소거리도 함께.
"""
import re, glob
import numpy as np
import xml.etree.ElementTree as ET
from scipy.spatial import cKDTree
import cadquery as cq
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location
import wristcam_pose as WP
from m1013_kin import M1013Kin

T = WP.basis()
br = cq.importers.importStep('cad/wristcam_bracket_v2.step').val(); br.mesh(0.4)
BV = []
for f in br.Faces():
    loc = TopLoc_Location(); tri = BRep_Tool.Triangulation_s(f.wrapped, loc)
    if tri is None: continue
    tf = loc.Transformation()
    for i in range(1, tri.NbNodes() + 1):
        q = tri.Node(i).Transformed(tf); BV.append([q.X(), q.Y(), q.Z()])
BV = np.array(BV) / 1000.0

r6 = ET.parse('doosan-robot2/dsr_description2/meshes/m1013_blue/MF1013_6_0.dae').getroot()
c = re.match(r'\{(.*)\}', r6.tag).group(1); p6 = []
for src in r6.iter('{%s}source' % c):
    fa = src.find('{%s}float_array' % c); acc = src.find('.//{%s}accessor' % c)
    if fa is None or acc is None or acc.get('stride') != '3': continue
    if [q.get('name') for q in acc.findall('{%s}param' % c)][:3] != ['X', 'Y', 'Z']: continue
    p6.append(np.fromstring(fa.text, sep=' ').reshape(-1, 3))
L6 = (np.vstack(p6) + np.array([-0.7121, -1.3634, -26.1851])) / 1000.0
d, _ = cKDTree(L6).query(BV); k = int(np.argmin(d))
print('브래킷 ↔ 로봇 손목 link_6 최소간격 %.2f mm @ (%.0f, %.0f, %.0f)' % (d.min() * 1000, *(BV[k] * 1000)))

uv = [WP.project(p, T) for p in BV]
ins = np.array([q is not None and abs(q[0]) < 1 and abs(q[1]) < 1 for q in uv])
print('브래킷 정점 중 화면 안 %d / %d (%.2f%%)' % (ins.sum(), len(BV), 100 * ins.mean()))
U = np.array([q for q in uv if q is not None and abs(q[0]) < 1 and abs(q[1]) < 1])
if len(U):
    print('  화면상 범위  u %+.2f ~ %+.2f   v %+.2f ~ %+.2f' % (U[:, 0].min(), U[:, 0].max(), U[:, 1].min(), U[:, 1].max()))

kin = M1013Kin(); cu = []
for fn in sorted(glob.glob('replay_ep*.npz')):
    dd = np.load(fn); J, TC = dd['joints'], int(dd['t_close']); cube = dd['cube_pick'].astype(float)
    for kk in range(max(0, TC - 60), min(len(J), TC + 16)):
        Tf = kin.fk(J[kk]); q = WP.project(Tf[:3, :3].T @ (cube - Tf[:3, 3]), T)
        if q is not None: cu.append(q)
CU = np.array(cu)
print('  큐브 궤적    u %+.2f ~ %+.2f   v %+.2f ~ %+.2f   (최악 %.3f)'
      % (CU[:, 0].min(), CU[:, 0].max(), CU[:, 1].min(), CU[:, 1].max(), np.abs(CU).max()))
if len(U):
    dm = cKDTree(U).query(CU)[0].min()
    print('  브래킷 ↔ 큐브 화면상 최소거리 %.3f  %s' % (dm, '✅ 비침범' if dm > 0.05 else '❌ 큐브를 가림'))
else:
    print('  브래킷이 화면에 전혀 안 들어옴 ✅')
