#!/usr/bin/env python3
"""정면캠(camera2) 구도 탐색 — 후보 포즈 N개를 한 번의 Isaac 부팅으로 렌더.

씬은 replay_isaac 과 동일(로봇 홈 + 테이블 + 큐브 + 그리퍼 근사)하되 물리 재생 없이
정지 상태만. 후보별 640x480 PNG 를 sim_out/frontcam_probe/ 에 저장.

  cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/frontcam_probe.py
"""
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})

import numpy as np
import traceback

# 후보: pos, tgt(look-at), focal(mm) — HFOV = 2*atan(20.955/2f) → 18.1mm=60°, 15.0mm=70°
CANDS = [
    dict(name="F1_base",  pos=(1.20, -0.25, 0.46), tgt=(0.45, -0.15, 0.52), f=15.0),
    dict(name="F2_back",  pos=(1.30, -0.22, 0.47), tgt=(0.42, -0.15, 0.52), f=15.0),
    dict(name="F3_level", pos=(1.25, -0.20, 0.44), tgt=(0.45, -0.17, 0.50), f=15.0),
]

try:
    from isaacsim.core.api import World
    from isaacsim.core.api.objects import DynamicCuboid, FixedCuboid
    from isaacsim.core.utils.stage import add_reference_to_stage, get_current_stage
    from isaacsim.core.prims import SingleArticulation
    from isaacsim.core.utils.types import ArticulationAction
    from isaacsim.sensors.camera import Camera
    from pxr import UsdPhysics, UsdGeom, UsdLux, Gf
    from PIL import Image
    import os

    DATA = np.load("/home/kim/m1013/replay_ep000.npz")
    HOME = DATA["joints"][0]
    CUBE_PICK = DATA["cube_pick"]
    CUBE = float(DATA["cube_size"])
    TABLE_Z = float(DATA["table_top_z"])
    FLANGE0 = DATA["flange0"]
    BEAM_L = float(DATA["finger_ext"])
    OUT = "/home/kim/m1013/sim_out/frontcam_probe"
    os.makedirs(OUT, exist_ok=True)

    world = World(stage_units_in_meters=1.0, physics_dt=1 / 60, rendering_dt=1 / 60)
    world.scene.add_default_ground_plane()
    stage = get_current_stage()

    add_reference_to_stage("/home/kim/m1013/doosan-robot2/dsr_description2/usd/m1013.usd", "/World/m1013")
    root_path = None
    for prim in stage.Traverse():
        p = prim.GetPath().pathString
        if p.startswith("/World/m1013") and prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            root_path = p
    assert root_path

    table = FixedCuboid("/World/table", name="table",
                        position=np.array([0.705, -0.15, TABLE_Z - 0.025]),
                        scale=np.array([0.49, 0.60, 0.05]),
                        color=np.array([0.72, 0.72, 0.70]))   # 실사 테이블 = 밝은 회색
    world.scene.add(table)
    # 실사 배경 = 흰 벽 (로봇 뒤 수직 플레인)
    wall = FixedCuboid("/World/wall", name="wall",
                       position=np.array([-0.55, 0.0, 1.25]),
                       scale=np.array([0.05, 4.0, 2.5]), color=np.array([0.92, 0.92, 0.90]))
    world.scene.add(wall)
    cube = DynamicCuboid("/World/cube", name="cube",
                         position=CUBE_PICK, size=CUBE, mass=0.015,
                         color=np.array([0.1, 0.2, 0.9]))
    world.scene.add(cube)
    # 실사 구도의 place 옆 노란 주사위 (시각 참조용)
    CUBE_PLACE = DATA["cube_place"]
    ycube = DynamicCuboid("/World/ycube", name="ycube",
                          position=CUBE_PLACE + np.array([0.0, 0.07, 0.0]),
                          size=CUBE, mass=0.015, color=np.array([0.9, 0.8, 0.1]))
    world.scene.add(ycube)

    # 그리퍼 근사 (정지 렌더 전용 — 물리 조인트 없이 형상만 flange0 기준 배치)
    def quat_of(R):
        w = np.sqrt(max(0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
        return Gf.Quatf(float(w), float((R[2, 1] - R[1, 2]) / (4 * w)),
                        float((R[0, 2] - R[2, 0]) / (4 * w)),
                        float((R[1, 0] - R[0, 1]) / (4 * w)))

    def static_box(path, T_local, half, color, geom_off=None):
        L = np.eye(4); L[:3, 3] = T_local
        T = FLANGE0 @ L
        xf = UsdGeom.Xform.Define(stage, path)
        xf.AddTranslateOp().Set(Gf.Vec3d(*map(float, T[:3, 3])))
        xf.AddOrientOp().Set(quat_of(T[:3, :3]))
        geo = UsdGeom.Cube.Define(stage, path + "/geom")
        geo.CreateSizeAttr(1.0)
        if geom_off is not None:
            geo.AddTranslateOp().Set(Gf.Vec3d(*map(float, geom_off)))
        geo.AddScaleOp().Set(Gf.Vec3f(2 * half[0], 2 * half[1], 2 * half[2]))
        geo.CreateDisplayColorAttr([Gf.Vec3f(*color)])

    F_HALF = (0.008, 0.012, BEAM_L / 2)
    goff = (0.0, 0.0, BEAM_L / 2)
    static_box("/World/gbase", (0, 0, 0.035), (0.042, 0.032, 0.035), (0.85, 0.85, 0.9))
    x_open = 0.070 / 2 + F_HALF[0]   # 열린 갭 기준 핑거 중심 |x|
    static_box("/World/gfL", (-x_open, 0, 0.07), F_HALF, (0.2, 0.2, 0.25), geom_off=goff)
    static_box("/World/gfR", (+x_open, 0, 0.07), F_HALF, (0.2, 0.2, 0.25), geom_off=goff)

    art = SingleArticulation(root_path, name="m1013")
    world.scene.add(art)

    sun = UsdLux.DistantLight.Define(stage, "/World/sun")
    sun.CreateIntensityAttr(3000.0)
    UsdGeom.Xformable(sun.GetPrim()).AddRotateXYZOp().Set(Gf.Vec3f(-40, 15, 0))
    dome = UsdLux.DomeLight.Define(stage, "/World/dome")
    dome.CreateIntensityAttr(800.0)

    def make_cam(path, pos, tgt, focal):
        # Camera 클래스 world-axes 규약: +X 전방, +Z 상방
        pos = np.asarray(pos, float); tgt = np.asarray(tgt, float)
        xc = tgt - pos; xc /= np.linalg.norm(xc)
        yc = np.cross([0, 0, 1.0], xc); yc /= np.linalg.norm(yc)
        zc = np.cross(xc, yc)
        Rc = np.stack([xc, yc, zc], axis=1)
        # 단순 공식은 180° 회전(w=0)에서 0-나눗셈 — scipy 로 견고하게 변환
        from scipy.spatial.transform import Rotation
        qx, qy, qz, qw = Rotation.from_matrix(Rc).as_quat()
        q = np.array([qw, qx, qy, qz])
        cam = Camera(path, resolution=(640, 480))
        cam.set_world_pose(position=pos, orientation=q)
        return cam

    cams = [(c, make_cam(f"/World/probe_{c['name']}", c["pos"], c["tgt"], c["f"])) for c in CANDS]

    world.reset()
    for c, cam in cams:
        cam.initialize()
        cam.set_focal_length(c["f"] / 10)          # Camera 클래스는 cm 단위
        cam.set_horizontal_aperture(20.955 / 10)
        cam.set_vertical_aperture(20.955 * 480 / 640 / 10)
        cam.set_clipping_range(0.05, 20.0)

    dof = art.dof_names
    arm_idx = np.array([dof.index(f"joint_{i}") for i in range(1, 7)])
    art.set_joint_positions(HOME, joint_indices=arm_idx)
    ctrl = art.get_articulation_controller()
    n = art.num_dof
    ctrl.set_gains(kps=np.full(n, 1.0e6), kds=np.full(n, 2.0e4))
    for _ in range(30):
        ctrl.apply_action(ArticulationAction(joint_positions=HOME, joint_indices=arm_idx))
        world.step(render=False)
    for _ in range(30):
        world.step(render=True)

    for c, cam in cams:
        rgba = cam.get_rgba()
        for _ in range(60):
            if rgba is not None and getattr(rgba, "ndim", 0) == 3 and rgba.shape[0] > 1:
                break
            world.step(render=True)
            rgba = cam.get_rgba()
        Image.fromarray(rgba[:, :, :3]).save(f"{OUT}/{c['name']}.png")
        print("SAVED:", c["name"], flush=True)

    print("PROBE_DONE", flush=True)
except Exception:
    traceback.print_exc()
finally:
    app.close()
