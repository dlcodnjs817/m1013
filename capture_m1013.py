#!/usr/bin/env python3
"""M1013 전신 캡처 (PPT 용) — Isaac Sim 헤드리스 렌더 2장.

  cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/capture_m1013.py

출력:
  sim_out/m1013_full_alone.png  — 바닥 + 로봇 전신 (에셋 검증 슬라이드용)
  sim_out/m1013_full_scene.png  — 테이블 + 큐브 포함 전체 씬
"""

from isaacsim import SimulationApp
app = SimulationApp({"headless": True})

import numpy as np
import traceback

try:
    from isaacsim.core.api import World
    from isaacsim.core.api.objects import DynamicCuboid, FixedCuboid
    from isaacsim.core.utils.stage import add_reference_to_stage, get_current_stage
    from isaacsim.core.prims import SingleArticulation
    from isaacsim.core.utils.types import ArticulationAction
    from isaacsim.sensors.camera import Camera
    from pxr import UsdPhysics, UsdGeom, UsdLux, Gf
    from PIL import Image

    DATA = np.load("/home/kim/m1013/replay_ep000.npz")
    HOME = DATA["joints"][0]
    CUBE_PICK = DATA["cube_pick"]
    CUBE = float(DATA["cube_size"])
    TABLE_Z = float(DATA["table_top_z"])
    OUT = "/home/kim/m1013/sim_out"

    world = World(stage_units_in_meters=1.0, physics_dt=1 / 60, rendering_dt=1 / 60)
    world.scene.add_default_ground_plane()
    stage = get_current_stage()

    add_reference_to_stage("/home/kim/m1013/doosan-robot2/dsr_description2/usd/m1013.usd", "/World/m1013")
    root_path = None
    for prim in stage.Traverse():
        p = prim.GetPath().pathString
        if p.startswith("/World/m1013") and prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            root_path = p
    print("ART_ROOT:", root_path, flush=True)
    assert root_path

    table = FixedCuboid("/World/table", name="table",
                        position=np.array([0.705, -0.15, TABLE_Z - 0.025]),
                        scale=np.array([0.49, 0.60, 0.05]), color=np.array([0.55, 0.4, 0.25]))
    world.scene.add(table)
    cube = DynamicCuboid("/World/cube", name="cube",
                         position=CUBE_PICK, size=CUBE, mass=0.015,
                         color=np.array([0.1, 0.2, 0.9]))
    world.scene.add(cube)

    art = SingleArticulation(root_path, name="m1013")
    world.scene.add(art)

    sun = UsdLux.DistantLight.Define(stage, "/World/sun")
    sun.CreateIntensityAttr(3000.0)
    UsdGeom.Xformable(sun.GetPrim()).AddRotateXYZOp().Set(Gf.Vec3f(-40, 15, 0))
    dome = UsdLux.DomeLight.Define(stage, "/World/dome")
    dome.CreateIntensityAttr(800.0)

    def make_cam(path, pos, tgt, res=(1920, 1080)):
        # Camera 클래스 world-axes 규약: +X 전방, +Z 상방
        pos = np.asarray(pos, float); tgt = np.asarray(tgt, float)
        xc = tgt - pos; xc /= np.linalg.norm(xc)
        yc = np.cross([0, 0, 1.0], xc); yc /= np.linalg.norm(yc)
        zc = np.cross(xc, yc)
        Rc = np.stack([xc, yc, zc], axis=1)
        w = np.sqrt(max(0, 1 + Rc[0, 0] + Rc[1, 1] + Rc[2, 2])) / 2
        q = np.array([w, (Rc[2, 1] - Rc[1, 2]) / (4 * w), (Rc[0, 2] - Rc[2, 0]) / (4 * w),
                      (Rc[1, 0] - Rc[0, 1]) / (4 * w)])
        cam = Camera(path, resolution=res)
        cam.set_world_pose(position=pos, orientation=q)
        return cam

    # 컷 1: 로봇 전신 (베이스~팔꿈치 정점까지 다 보이게, 약간 위에서)
    cam1 = make_cam("/World/cam1", pos=[3.5, 2.85, 1.5], tgt=[0.15, -0.05, 0.5])
    # 컷 2: 씬 전체 (로봇 + 테이블 + 큐브)
    cam2 = make_cam("/World/cam2", pos=[3.8, -2.9, 2.2], tgt=[0.5, -0.1, 0.75])

    world.reset()
    cam1.initialize(); cam2.initialize()

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

    for cam, name in ((cam1, "m1013_full_alone.png"), (cam2, "m1013_full_scene.png")):
        rgba = cam.get_rgba()
        for _ in range(60):
            if rgba is not None and getattr(rgba, "ndim", 0) == 3 and rgba.shape[0] > 1:
                break
            world.step(render=True)
            rgba = cam.get_rgba()
        img = Image.fromarray(rgba[:, :, :3])
        img.save(f"{OUT}/{name}")
        print("SAVED:", f"{OUT}/{name}", flush=True)

    print("CAPTURE_DONE", flush=True)
except Exception:
    traceback.print_exc()
finally:
    app.close()
