#!/usr/bin/env python3
"""손목캠(camera1) 장착 탐색 — link_6 에 카메라를 붙이고 후보 오프셋/FOV 를
홈 포즈 + 파지 포즈(t_close) 두 장면에서 렌더.

실물 거동: 이미지 위 = 접근 방향, 파지점은 화면 하단 중앙.
접근 방향(플랜지 로컬) ≈ (-0.655, -0.755, 0) — flange0 에서 역산.

  cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/wristcam_probe.py
"""
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})

import numpy as np
import traceback

U_APP = np.array([-0.655, -0.755, 0.0]); U_APP /= np.linalg.norm(U_APP)
# 롤 미세보정: WR90(큐브 좌하 215°)에서 +40°/+55° 더 돌려 하단 중앙(270°) 조준
ROT = {"R130": np.array([-0.999, 0.016, 0.0]), "R145": np.array([-0.970, -0.243, 0.0])}
WCANDS = [
    dict(name="V1_r130_off40", pos=0.040 * U_APP + [0, 0, 0.05], f=18.0, u=ROT["R130"]),
    dict(name="V2_r145_off40", pos=0.040 * U_APP + [0, 0, 0.05], f=18.0, u=ROT["R145"]),
    dict(name="V3_r145_off60", pos=0.060 * U_APP + [0, 0, 0.05], f=18.0, u=ROT["R145"]),
]
FRONT = dict(pos=(1.20, -0.25, 0.46), tgt=(0.45, -0.15, 0.52), f=15.0)  # F1_base 확정값

try:
    from isaacsim.core.api import World
    from isaacsim.core.api.objects import DynamicCuboid, FixedCuboid
    from isaacsim.core.utils.stage import add_reference_to_stage, get_current_stage
    from isaacsim.core.prims import SingleArticulation
    from isaacsim.core.utils.types import ArticulationAction
    from isaacsim.sensors.camera import Camera
    from pxr import UsdPhysics, UsdGeom, UsdLux, Gf
    from scipy.spatial.transform import Rotation
    from PIL import Image
    import os, sys
    sys.path.insert(0, "/home/kim/m1013")
    from m1013_kin import M1013Kin

    DATA = np.load("/home/kim/m1013/replay_ep000.npz")
    JOINTS = DATA["joints"]
    HOME = JOINTS[0]
    T_CLOSE = int(DATA["t_close"])
    CUBE_PICK = DATA["cube_pick"]; CUBE_PLACE = DATA["cube_place"]
    CUBE = float(DATA["cube_size"])
    TABLE_Z = float(DATA["table_top_z"])
    FLANGE0 = DATA["flange0"]
    BEAM_L = float(DATA["finger_ext"])
    OUT = "/home/kim/m1013/sim_out/wristcam_probe"
    os.makedirs(OUT, exist_ok=True)

    kin = M1013Kin()
    print("FK-FLANGE0 오차(mm):", 1000 * np.abs(kin.fk(HOME)[:3, 3] - FLANGE0[:3, 3]).max(), flush=True)

    world = World(stage_units_in_meters=1.0, physics_dt=1 / 60, rendering_dt=1 / 60)
    world.scene.add_default_ground_plane()
    stage = get_current_stage()

    add_reference_to_stage("/home/kim/m1013/doosan-robot2/dsr_description2/usd/m1013.usd", "/World/m1013")
    root_path = link6_path = None
    for prim in stage.Traverse():
        p = prim.GetPath().pathString
        if p.startswith("/World/m1013"):
            if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
                root_path = p
            if prim.GetName() == "link_6":
                link6_path = p
    assert root_path and link6_path

    # 렌더용 확대 테이블 — 실물처럼 손목캠 시야에 모서리가 안 들어오게 (상판 z 동일)
    table = FixedCuboid("/World/table", name="table",
                        position=np.array([0.705, -0.15, TABLE_Z - 0.025]),
                        scale=np.array([0.85, 1.10, 0.05]), color=np.array([0.72, 0.72, 0.70]))
    world.scene.add(table)
    wall = FixedCuboid("/World/wall", name="wall",
                       position=np.array([-0.55, 0.0, 1.25]),
                       scale=np.array([0.05, 4.0, 2.5]), color=np.array([0.92, 0.92, 0.90]))
    world.scene.add(wall)
    cube = DynamicCuboid("/World/cube", name="cube", position=CUBE_PICK, size=CUBE,
                         mass=0.015, color=np.array([0.1, 0.2, 0.9]))
    world.scene.add(cube)
    ycube = DynamicCuboid("/World/ycube", name="ycube",
                          position=CUBE_PLACE + np.array([0.0, 0.07, 0.0]),
                          size=CUBE, mass=0.015, color=np.array([0.9, 0.8, 0.1]))
    world.scene.add(ycube)

    def quat_of(R):
        qx, qy, qz, qw = Rotation.from_matrix(R).as_quat()
        return Gf.Quatf(float(qw), float(qx), float(qy), float(qz))

    # 그리퍼 정적 형상 — 포즈 갱신 가능하게 op 핸들 보관
    F_HALF = (0.008, 0.012, BEAM_L / 2)
    grip_parts = []   # (translate_op, orient_op, local_T)
    def static_box(path, local_off, half, color, geom_off=None):
        L = np.eye(4); L[:3, 3] = local_off
        xf = UsdGeom.Xform.Define(stage, path)
        top = xf.AddTranslateOp(); rop = xf.AddOrientOp()
        geo = UsdGeom.Cube.Define(stage, path + "/geom")
        geo.CreateSizeAttr(1.0)
        if geom_off is not None:
            geo.AddTranslateOp().Set(Gf.Vec3d(*map(float, geom_off)))
        geo.AddScaleOp().Set(Gf.Vec3f(2 * half[0], 2 * half[1], 2 * half[2]))
        geo.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        grip_parts.append((top, rop, L))

    x_open = 0.070 / 2 + F_HALF[0]
    static_box("/World/gbase", (0, 0, 0.035), (0.042, 0.032, 0.035), (0.85, 0.85, 0.9))
    static_box("/World/gfL", (-x_open, 0, 0.07), F_HALF, (0.2, 0.2, 0.25), geom_off=(0, 0, BEAM_L / 2))
    static_box("/World/gfR", (+x_open, 0, 0.07), F_HALF, (0.2, 0.2, 0.25), geom_off=(0, 0, BEAM_L / 2))

    def set_gripper(T_flange):
        for top, rop, L in grip_parts:
            T = T_flange @ L
            top.Set(Gf.Vec3d(*map(float, T[:3, 3])))
            rop.Set(quat_of(T[:3, :3]))

    set_gripper(FLANGE0)

    art = SingleArticulation(root_path, name="m1013")
    world.scene.add(art)

    sun = UsdLux.DistantLight.Define(stage, "/World/sun")
    sun.CreateIntensityAttr(3000.0)
    UsdGeom.Xformable(sun.GetPrim()).AddRotateXYZOp().Set(Gf.Vec3f(-40, 15, 0))
    dome = UsdLux.DomeLight.Define(stage, "/World/dome")
    dome.CreateIntensityAttr(800.0)

    def lookat_quat_wxyz(f, u):
        f = np.asarray(f, float); f = f / np.linalg.norm(f)
        yc = np.cross(u, f); yc /= np.linalg.norm(yc)
        zc = np.cross(f, yc)
        Rc = np.stack([f, yc, zc], axis=1)
        qx, qy, qz, qw = Rotation.from_matrix(Rc).as_quat()
        return np.array([qw, qx, qy, qz])

    def set_fov(cam, focal):
        cam.set_focal_length(focal / 10)
        cam.set_horizontal_aperture(20.955 / 10)
        cam.set_vertical_aperture(20.955 * 480 / 640 / 10)
        cam.set_clipping_range(0.02, 20.0)

    # 손목캠: link_6 하위 prim → 물리가 손목을 움직이면 함께 움직임
    wcams = []
    for c in WCANDS:
        q_w = lookat_quat_wxyz([0, 0, 1.0], c["u"])   # 전방=로컬+z(하강 방향)
        cam = Camera(f"{link6_path}/{c['name']}", resolution=(640, 480))
        cam.set_local_pose(np.asarray(c["pos"], float), q_w, camera_axes="world")
        wcams.append((c, cam))

    # 정면캠 (확정 F1) — 동시 검증용
    p, t = np.asarray(FRONT["pos"]), np.asarray(FRONT["tgt"])
    fdir = t - p
    fcam = Camera("/World/frontcam", resolution=(640, 480))
    fcam.set_world_pose(position=p, orientation=lookat_quat_wxyz(fdir, [0, 0, 1.0]))

    world.reset()
    for c, cam in wcams:
        cam.initialize(); set_fov(cam, c["f"])
    fcam.initialize(); set_fov(fcam, FRONT["f"])

    dof = art.dof_names
    arm_idx = np.array([dof.index(f"joint_{i}") for i in range(1, 7)])
    ctrl = art.get_articulation_controller()
    n = art.num_dof
    ctrl.set_gains(kps=np.full(n, 1.0e6), kds=np.full(n, 2.0e4))

    def render_pose(q, tag):
        art.set_joint_positions(q, joint_indices=arm_idx)
        set_gripper(kin.fk(q))
        for _ in range(30):
            ctrl.apply_action(ArticulationAction(joint_positions=q, joint_indices=arm_idx))
            world.step(render=False)
        for _ in range(30):
            world.step(render=True)
        for c, cam in list(wcams) + [(dict(name="front"), fcam)]:
            rgba = cam.get_rgba()
            for _ in range(60):
                if rgba is not None and getattr(rgba, "ndim", 0) == 3 and rgba.shape[0] > 1:
                    break
                world.step(render=True)
                rgba = cam.get_rgba()
            Image.fromarray(rgba[:, :, :3]).save(f"{OUT}/{c['name']}_{tag}.png")
            print("SAVED", c["name"], tag, flush=True)

    render_pose(HOME, "home")
    render_pose(JOINTS[T_CLOSE], "grasp")
    print("WPROBE_DONE", flush=True)
except Exception:
    traceback.print_exc()
finally:
    app.close()
