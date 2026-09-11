#!/usr/bin/env python3
"""scene.json 을 Isaac 에 올려 턴테이블 프레임을 찍는다 — WebGL 없는 뷰어용 폴백.

  cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/isaac_turntable.py
출력: sim_out/scene3d/turn/<set>_<el>_<az>.jpg   (set: tool / full)
"""
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})
import numpy as np, traceback, functools, json, base64, os
print = functools.partial(print, flush=True)
try:
    from isaacsim.core.api import World
    from isaacsim.core.utils.stage import get_current_stage
    from isaacsim.sensors.camera import Camera
    from pxr import UsdGeom, UsdLux, Gf, Vt, Sdf
    from PIL import Image
    S = json.load(open('/home/kim/m1013/sim_out/scene3d/scene.json')); M = S['meta']
    OUT = '/home/kim/m1013/sim_out/scene3d/turn'; os.makedirs(OUT, exist_ok=True)
    world = World(stage_units_in_meters=1.0); stage = get_current_stage()
    def b64(s, dt): b = base64.b64decode(s); return np.frombuffer(b, dtype=dt)
    for i, p in enumerate(S['parts']):
        V = b64(p['v'], np.float32).reshape(-1, 3); F = b64(p['f'], np.uint32)
        m = UsdGeom.Mesh.Define(stage, '/World/p%02d' % i)
        m.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, v)) for v in V]))
        m.CreateFaceVertexCountsAttr(Vt.IntArray([3] * (len(F) // 3)))
        m.CreateFaceVertexIndicesAttr(Vt.IntArray([int(x) for x in F]))
        c = p['color'].lstrip('#'); rgb = [int(c[k:k+2], 16) / 255 for k in (0, 2, 4)]
        m.CreateDisplayColorAttr([Gf.Vec3f(*rgb)]); m.CreateSubdivisionSchemeAttr('none')
        m.CreateDoubleSidedAttr(True)
    # 바닥
    g = UsdGeom.Mesh.Define(stage, '/World/floor'); s_ = 3.0
    g.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(-s_, -s_, 0), Gf.Vec3f(s_, -s_, 0), Gf.Vec3f(s_, s_, 0), Gf.Vec3f(-s_, s_, 0)]))
    g.CreateFaceVertexCountsAttr(Vt.IntArray([4])); g.CreateFaceVertexIndicesAttr(Vt.IntArray([0, 1, 2, 3]))
    g.CreateDisplayColorAttr([Gf.Vec3f(0.80, 0.81, 0.84)])
    UsdLux.DistantLight.Define(stage, '/World/sun').CreateIntensityAttr(1500.0)
    UsdGeom.Xformable(stage.GetPrimAtPath('/World/sun')).AddRotateXYZOp().Set(Gf.Vec3f(-45, 25, 0))
    UsdLux.DomeLight.Define(stage, '/World/dome').CreateIntensityAttr(500.0)
    cam = Camera('/World/cam', resolution=(720, 540)); world.reset(); cam.initialize(); cam.set_clipping_range(0.01, 30)
    cam.set_focal_length(2.4); cam.set_horizontal_aperture(2.0955); cam.set_vertical_aperture(2.0955 * 0.75)
    fl = np.array(M['flange']); SETS = {'tool': (fl + np.array([0, 0, 0.0]), 0.42), 'full': (np.array([0.45, -0.1, 0.5]), 2.1)}
    AZ = 24; ELS = [22.0, 50.0]
    def look(eye, tgt):
        f = tgt - eye; f /= np.linalg.norm(f); r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f)
        T = np.eye(4); T[:3, 0] = r; T[:3, 1] = u; T[:3, 2] = -f; T[:3, 3] = eye
        UsdGeom.Xformable(stage.GetPrimAtPath('/World/cam')).MakeMatrixXform().Set(Gf.Matrix4d(*[float(x) for x in T.T.flatten()]))
    for _ in range(30): world.step(render=True)
    n = 0
    for name, (tgt, rad) in SETS.items():
        for ei, el in enumerate(ELS):
            for ai in range(AZ):
                az = np.radians(-90 + 360.0 * ai / AZ); e = np.radians(el)
                eye = tgt + rad * np.array([np.cos(e) * np.cos(az), np.cos(e) * np.sin(az), np.sin(e)])
                look(eye, tgt)
                for _ in range(14): world.step(render=True)
                rgba = cam.get_rgba()
                for _ in range(40):
                    if getattr(rgba, 'ndim', 0) == 3: break
                    world.step(render=True); rgba = cam.get_rgba()
                Image.fromarray(rgba[:, :, :3]).save('%s/%s_%d_%02d.jpg' % (OUT, name, ei, ai), quality=82, optimize=True); n += 1
        print('%s 세트 완료' % name)
    print('저장 %d 장 → %s' % (n, OUT))
except Exception:
    traceback.print_exc()
finally:
    app.close()
