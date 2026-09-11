#!/usr/bin/env python3
"""손목캠 시점 소프트웨어 렌더 — Isaac/GPU 없이 손목캠이 무엇을 보는지 그린다.

  python3 wristcam_preview.py [HFOV]

`cad/tool_assembly_flangelocal.stl`(어댑터·그리퍼·조·핑거·밸브/손목캠 브래킷 전부)을
플랜지 자세로 옮겨 카메라에 투영한다. 브래킷이 화면을 가리는지 **눈으로** 확인하는 용도.
Isaac 렌더(`wristcam_render.py`)는 GPU 가 필요하지만 이건 numpy 만 쓴다.

출력: sim_out/wristcam_preview/ep<NNN>_<tag>.png
"""
import os, struct, sys, glob
import numpy as np
from PIL import Image
from m1013_kin import M1013Kin

import wristcam_pose as WP
W, H = 640, 480
HFOV = float(sys.argv[1]) if len(sys.argv) > 1 else WP.HFOV
CAM_POS, CAM_FWD = WP.CAM_POS, WP.CAM_FWD        # 단일 소스
OUT = 'sim_out/wristcam_preview'
os.makedirs(OUT, exist_ok=True)


def cam_local(gz):
    return WP.basis(tcp=gz)


def load_stl(p):
    raw = open(p, 'rb').read()
    n = struct.unpack('<I', raw[80:84])[0]
    d = np.frombuffer(raw[84:84 + n * 50], dtype=np.uint8).reshape(n, 50)
    return d[:, 12:48].copy().view('<f4').reshape(n, 3, 3).astype(np.float64) / 1000.0


def quad(p0, p1, p2, p3):
    return np.array([[p0, p1, p2], [p0, p2, p3]], dtype=float)


def box(c, s):
    x, y, z = c; a, b, d = np.array(s) / 2.0
    v = [(x-a,y-b,z-d),(x+a,y-b,z-d),(x+a,y+b,z-d),(x-a,y+b,z-d),
         (x-a,y-b,z+d),(x+a,y-b,z+d),(x+a,y+b,z+d),(x-a,y+b,z+d)]
    fs = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return np.array([t for f in fs for t in quad(*[v[i] for i in f])], dtype=float)


def render(tris, cols, T_cam_w, bg=(232, 234, 238)):
    R, t = T_cam_w[:3, :3], T_cam_w[:3, 3]
    P = (tris.reshape(-1, 3) - t) @ R                      # 월드 -> 카메라
    P = P.reshape(-1, 3, 3)
    th = np.tan(np.radians(HFOV / 2)); asp = H / W
    img = np.full((H, W, 3), bg, dtype=np.float64)
    zb = np.full((H, W), np.inf)
    light = np.array([0.3, 0.4, 0.86]); light /= np.linalg.norm(light)

    keep = (P[:, :, 2] < -1e-6).all(axis=1)                # 전부 카메라 앞
    P, cols2 = P[keep], cols[keep]
    d = -P[:, :, 2]
    sx = (P[:, :, 0] / d / th + 1) * 0.5 * W
    sy = (-(P[:, :, 1] / d / (th * asp)) + 1) * 0.5 * H
    order = np.argsort(-d.min(axis=1))                     # 먼 것부터 (보조)
    for i in order:
        x, y, z = sx[i], sy[i], d[i]
        x0, x1 = int(max(0, np.floor(x.min()))), int(min(W - 1, np.ceil(x.max())))
        y0, y1 = int(max(0, np.floor(y.min()))), int(min(H - 1, np.ceil(y.max())))
        if x1 < x0 or y1 < y0:
            continue
        e = ((x[1]-x[0])*(y[2]-y[0]) - (x[2]-x[0])*(y[1]-y[0]))
        if abs(e) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((x[1]-gx)*(y[2]-gy) - (x[2]-gx)*(y[1]-gy)) / e
        w1 = ((x[2]-gx)*(y[0]-gy) - (x[0]-gx)*(y[2]-gy)) / e
        w2 = 1.0 - w0 - w1
        m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not m.any():
            continue
        zz = w0*z[0] + w1*z[1] + w2*z[2]
        sub = zb[y0:y1+1, x0:x1+1]
        upd = m & (zz < sub)
        if not upd.any():
            continue
        v0, v1 = P[i, 1] - P[i, 0], P[i, 2] - P[i, 0]
        nrm = np.cross(v0, v1); ln = np.linalg.norm(nrm)
        sh = 0.55 if ln < 1e-12 else 0.42 + 0.58 * abs(float(nrm @ np.array([0.3, 0.4, -0.86])) / ln)
        sub[upd] = zz[upd]
        zb[y0:y1+1, x0:x1+1] = sub
        tile = img[y0:y1+1, x0:x1+1]
        tile[upd] = np.clip(cols2[i] * sh, 0, 255)
        img[y0:y1+1, x0:x1+1] = tile
    return img.astype(np.uint8)


TOOL = load_stl('cad/tool_assembly_nowrist.stl')      # 브래킷 뺀 나머지 (회색)
BRACK = load_stl('cad/wristcam_bracket_v2.stl')       # 손목캠 브래킷 (주황) — 시야 침범 확인용
kin = M1013Kin()
D0 = np.load('replay_ep000.npz')
TABLE_Z = float(D0['table_top_z']); CUBE = float(D0['cube_size']); GZ = float(D0['tcp'])
T_cam_fl = cam_local(GZ)
def grid_quad(x0, x1, y0, y1, z, n=24):
    """상판을 잘게 쪼갠다 — 큰 삼각형은 한 꼭짓점만 카메라 뒤여도 통째로 컬링된다."""
    xs, ys, out = np.linspace(x0, x1, n + 1), np.linspace(y0, y1, n + 1), []
    for i in range(n):
        for j in range(n):
            out.append(quad((xs[i], ys[j], z), (xs[i+1], ys[j], z),
                            (xs[i+1], ys[j+1], z), (xs[i], ys[j+1], z)))
    return np.concatenate(out)


TABLE = grid_quad(0.005, 1.405, -1.05, 0.75, TABLE_Z)
print('HFOV %.1f°  카메라 플랜지로컬 (%.0f, %.0f, %.0f) mm  툴 %d 삼각형'
      % (HFOV, *(CAM_POS * 1000), len(TOOL)))

for ep in ('000', '050', '130'):
    D = np.load(f'replay_ep{ep}.npz')
    J, TC = D['joints'], int(D['t_close'])
    cp = np.array(D['cube_pick'], dtype=float)
    # 프레임을 고정 오프셋이 아니라 **기하**로 고른다 — t_close+15 는 이미 큐브를 든 뒤라
    # (큐브가 집는 위치에 고정된 이 렌더에서는) 파지 순간이 아니다.
    # TCP(플랜지 +Z 72.5 mm) 와 큐브의 3D 거리로 고른다. Z 성분만 보면 팔이 지나가다
    # 우연히 같은 높이가 되는 엉뚱한 프레임이 잡힌다.
    Ts = [kin.fk(J[k]) for k in range(len(J))]
    tcp = np.array([T[:3, 3] + T[:3, 2] * GZ for T in Ts])
    dist = np.linalg.norm(tcp - cp, axis=1) * 1000.0
    g = int(np.argmin(dist[:min(TC + 20, len(J))]))             # 실제 파지 순간
    def before(d_mm):
        c = np.where(dist[:g + 1] >= d_mm)[0]
        return int(c[-1]) if len(c) else 0
    for tag, t in (('a_far', before(300)), ('b_near', before(180)),
                   ('c_pre', before(110)), ('d_grasp', g)):
        T_fl = kin.fk(J[t])
        R_, t_ = T_fl[:3, :3], T_fl[:3, 3]
        tool_w = (TOOL.reshape(-1, 3) @ R_.T + t_).reshape(-1, 3, 3)
        brack_w = (BRACK.reshape(-1, 3) @ R_.T + t_).reshape(-1, 3, 3)
        cube_w = box(cp, (CUBE, CUBE, CUBE))
        tris = np.concatenate([TABLE, cube_w, tool_w, brack_w])
        cols = np.concatenate([
            np.tile([203, 188, 158], (len(TABLE), 1)),     # 상판 = 베이지
            np.tile([40, 70, 225], (len(cube_w), 1)),      # 큐브 = 파랑
            np.tile([205, 205, 215], (len(tool_w), 1)),    # 툴 = 회색
            np.tile([235, 120, 40], (len(brack_w), 1))]).astype(float)  # 브래킷 = 주황
        img = render(tris, cols, T_fl @ T_cam_fl)
        Image.fromarray(img).save(f'{OUT}/ep{ep}_{tag}.png')
        print('  ep%s %-11s frame %4d 저장' % (ep, tag, t), flush=True)
print('저장 위치:', OUT)
