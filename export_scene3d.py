#!/usr/bin/env python3
"""전체 설계 3D 씬 내보내기 — 로봇 + 어댑터 + 그리퍼 + 핑거 + 브래킷 2 + 카메라 + 큐브·상판.

  python3 export_scene3d.py [ep] [frame]      기본 ep130 파지 프레임

출력: sim_out/scene3d/scene.json  (부품별 정점/삼각형, 월드 좌표 m)
좌표 매핑은 cad/make_tool_assembly.py 와 동일. 로봇은 URDF 링크별 DAE + 노드 행렬 + fk_frames.
"""
import json, re, sys, struct, base64
import numpy as np
import xml.etree.ElementTree as ET
import cadquery as cq
from m1013_kin import M1013Kin
import wristcam_pose as WP

ep = sys.argv[1] if len(sys.argv) > 1 else '130'
D = np.load(f'replay_ep{ep}.npz'); J, TC = D['joints'], int(D['t_close'])
cp = np.array(D['cube_pick'], float); GZ = float(D['tcp']); CUBE = float(D['cube_size']); TZ = float(D['table_top_z'])
kin = M1013Kin()
if len(sys.argv) > 2:
    t = int(sys.argv[2])
else:
    Ts = [kin.fk(J[k]) for k in range(len(J))]
    tcp = np.array([T[:3, 3] + T[:3, 2] * GZ for T in Ts])
    t = int(np.argmin(np.linalg.norm(tcp - cp, axis=1)[:min(TC + 20, len(J))]))
q = J[t]; frames = kin.fk_frames(q); T_fl = frames[-1]
print('ep%s frame %d · 플랜지 월드 %s' % (ep, t, np.round(T_fl[:3, 3], 3)))

parts = []


def add(name, group, V, F, color, note=''):
    V = np.asarray(V, np.float32); F = np.asarray(F, np.uint32)
    parts.append(dict(name=name, group=group, color=color, note=note, nv=int(len(V)), nf=int(len(F)),
                      v=base64.b64encode(V.tobytes()).decode(), f=base64.b64encode(F.tobytes()).decode()))
    print('  %-14s %-8s 정점 %6d 삼각형 %6d' % (name, group, len(V), len(F)))


def tess(shape, tol=0.25):
    vs, ts = shape.tessellate(tol)
    return np.array([[v.x, v.y, v.z] for v in vs]) / 1000.0, np.array(ts)


def to_world(V):
    return V @ T_fl[:3, :3].T + T_fl[:3, 3]


# ---------------- 툴 (플랜지 로컬 → 월드) — make_tool_assembly 와 같은 매핑 ----------------
O, AX, AZ = (0, 0, 0), (1, 0, 0), (0, 0, 1); Q = cq.importers.importStep
ad = Q('cad/adapter_m1013_mhf2.step').val().rotate(O, AX, 180).translate((0, 0, 12))
V, F = tess(ad); add('어댑터 플레이트', 'tool', to_world(V), F, '#B9BEC7', 'AL6061-T6 140×70×12 · 절삭 외주')
sols = sorted(Q('cad/1/MHF2-16D2(64_0_).stp').solids().vals(), key=lambda s: -s.Volume())
gb = sols[0].rotate(O, AX, -90).rotate(O, AZ, -90).translate((0, 0, 12))
V, F = tess(gb, 0.4); add('그리퍼 MHF2-16D2', 'tool', to_world(V), F, '#7E838C', 'SMC 공압 평행 그리퍼 · TX90 이관')
keep = cq.Workplane('XY').transformed(offset=(0, 0, 40.3 + 100)).box(400, 400, 200).val()
for i, s in enumerate(sols[1:3]):
    tt = s.rotate(O, AX, -90).rotate(O, AZ, -90).translate((0, 0, 12)); bb = tt.BoundingBox()
    tt = tt.translate((-32.0 if bb.xmax > 60 else 32.0, 0, 0)).intersect(keep)
    V, F = tess(tt, 0.3); add('그리퍼 조 %d' % (i + 1), 'tool', to_world(V), F, '#6A6F78')
for nm, fn in (('핑거 좌', 'finger_left'), ('핑거 우', 'finger_right')):
    fg = Q(f'cad/{fn}.step').val().rotate(O, AX, 180).translate((0, 0, 53))
    V, F = tess(fg); add(nm, 'tool', to_world(V), F, '#A3A8B1', 'AL6061-T6 · 판 41.8 · 절삭 외주')
V, F = tess(Q('cad/valve_bracket_sy5120.step').val()); add('밸브 브래킷', 'bracket', to_world(V), F, '#2E8B8B', 'PETG 26 g · SY5120 밸브용 · +Y')
V, F = tess(Q('cad/wristcam_bracket_v2.step').val()); add('손목캠 브래킷', 'bracket', to_world(V), F, '#E07A2E', 'PETG 46 g · A-프레임 · −Y')

# ---------------- 카메라 보드 + 렌즈 (wristcam_pose) ----------------
Tc = WP.basis(); xc, yc, f = Tc[:3, 0], Tc[:3, 1], -Tc[:3, 2]; C = WP.CAM_POS * 1000
LENS, TB = 19.0, 1.6
bc = C - f * (LENS + TB / 2)
board = cq.Workplane(cq.Plane(origin=tuple(bc), xDir=tuple(xc), normal=tuple(f))).rect(32, 32).extrude(TB / 2, both=True)
V, F = tess(board.val()); add('카메라 보드', 'camera', to_world(V), F, '#2F7D4F', 'U20CAM-720P 32×32 · 세로 장착')
lens = cq.Workplane(cq.Plane(origin=tuple(C - f * LENS), xDir=tuple(xc), normal=tuple(f))).circle(7).extrude(LENS + 3)
V, F = tess(lens.val()); add('M12 렌즈', 'camera', to_world(V), F, '#1E2126', '광심 (0, −65, −10) · 틸트 23°')

# ---------------- 로봇 (URDF DAE) ----------------
MESH = {0: ['MF1013_0_0'], 1: ['MF1013_1_0'], 2: ['MF1013_2_0', 'MF1013_2_1', 'MF1013_2_2'], 3: ['MF1013_3_0'],
        4: ['MF1013_4_0', 'MF1013_4_1'], 5: ['MF1013_5_0'], 6: ['MF1013_6_0']}
LINKT = [np.eye(4)] + frames


def dae(path):
    """DAE → (정점 m, 삼각형). 파일 하나에 <geometry> 가 여럿일 수 있으므로 지오메트리 단위로
    위치 배열과 삼각형을 짝지어 합친다 (액센트 파일 2_1·2_2·4_1 이 그렇다)."""
    r = ET.parse(path).getroot(); c = re.match(r'\{(.*)\}', r.tag).group(1)
    ns = lambda t: '{%s}%s' % (c, t)
    # 노드 행렬: geometry id → matrix (instance_geometry url 로 연결)
    node_M = {}
    for nd in r.iter(ns('node')):
        m = nd.find(ns('matrix'))
        M = np.array([float(x) for x in m.text.split()]).reshape(4, 4) if m is not None else np.eye(4)
        for ig in nd.iter(ns('instance_geometry')):
            node_M[ig.get('url').lstrip('#')] = M
    Vs, Fs, off = [], [], 0
    for geo in r.iter(ns('geometry')):
        gid = geo.get('id'); M = node_M.get(gid, np.eye(4))
        srcs = {}
        for src in geo.iter(ns('source')):
            fa = src.find(ns('float_array')); acc = src.find('.//' + ns('accessor'))
            if fa is not None and acc is not None:
                srcs[src.get('id')] = np.fromstring(fa.text, sep=' ').reshape(-1, int(acc.get('stride')))
        vert = geo.find('.//' + ns('vertices'))
        pos_id = [i.get('source').lstrip('#') for i in vert.findall(ns('input')) if i.get('semantic') == 'POSITION'][0]
        pos = srcs[pos_id]
        for tri in list(geo.iter(ns('triangles'))) + list(geo.iter(ns('polylist'))):
            inputs = tri.findall(ns('input')); stride = max(int(i.get('offset')) for i in inputs) + 1
            vo = [int(i.get('offset')) for i in inputs if i.get('semantic') == 'VERTEX'][0]
            idx = np.fromstring(tri.find(ns('p')).text, sep=' ', dtype=np.int64).reshape(-1, stride)[:, vo]
            if tri.tag == ns('polylist'):
                vc = np.fromstring(tri.find(ns('vcount')).text, sep=' ', dtype=np.int64); F = []; k = 0
                for n_ in vc:
                    for j in range(1, n_ - 1): F.append([idx[k], idx[k + j], idx[k + j + 1]])
                    k += n_
                F = np.array(F)
            else:
                F = idx.reshape(-1, 3)
            Fs.append(F + off)
        Vs.append((M[:3, :3] @ pos.T).T + M[:3, 3]); off += len(pos)
    return np.vstack(Vs) * 0.001, np.vstack(Fs)


for li, files in MESH.items():
    for fn in files:
        V, F = dae(f'doosan-robot2/dsr_description2/meshes/m1013_blue/{fn}.dae')
        T = LINKT[li]; Vw = V @ T[:3, :3].T + T[:3, 3]
        accent = fn.endswith('_1') or fn.endswith('_2')
        add(('M1013 %s' % ('base' if li == 0 else 'link_%d' % li)) + (' 액센트' if accent else ''), 'robot', Vw, F,
            '#2F5FB3' if accent else '#EEF0F3')

# ---------------- 상판 · 큐브 ----------------
def box(c, s):
    x, y, z = c; a, b, d = np.array(s) / 2
    V = np.array([[x-a,y-b,z-d],[x+a,y-b,z-d],[x+a,y+b,z-d],[x-a,y+b,z-d],[x-a,y-b,z+d],[x+a,y-b,z+d],[x+a,y+b,z+d],[x-a,y+b,z+d]])
    F = np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
    return V, F
V, F = box((0.705, -0.15, TZ - 0.02), (0.9, 0.9, 0.04)); add('작업대', 'scene', V, F, '#CFC8BA', '상판 z=%.4f' % TZ)
V, F = box(cp, (CUBE,) * 3); add('큐브 35mm', 'scene', V, F, '#3557D6', '파지 위치')

meta = dict(ep=ep, frame=t, flange=T_fl[:3, 3].tolist(), flange_R=T_fl[:3, :3].tolist(),
            cam_world=(T_fl[:3, :3] @ WP.CAM_POS + T_fl[:3, 3]).tolist(),
            cam_fwd_world=(T_fl[:3, :3] @ WP.CAM_FWD).tolist(), tcp_world=(T_fl[:3, 3] + T_fl[:3, 2] * GZ).tolist(),
            cube=cp.tolist(), hfov=WP.HFOV)
import os; os.makedirs('sim_out/scene3d', exist_ok=True)
json.dump(dict(meta=meta, parts=parts), open('sim_out/scene3d/scene.json', 'w'))
print('저장 sim_out/scene3d/scene.json  (%.1f MB)' % (os.path.getsize('sim_out/scene3d/scene.json') / 1e6))
