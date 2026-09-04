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

# ★ 2026-09-04 §8 재정합. TCP 정정(플랜지→파지점 67.5mm)으로 종전 구성
# (pos 0.060*U_APP+[0,0,0.05], forward [0,0,1]) 은 파지 순간 이탈각 73.7° = 완전 화면 밖.
# 위치·틸트·FOV 를 다시 풀었다. 조준은 파지점이 화면 세로 0.55 지점에 오도록.
AP_H = 20.955
def _focal(hfov):
    return AP_H / 2 / np.tan(np.radians(hfov / 2))
def _roll(pos, f, deg):
    """f 를 광축으로 하는 up 힌트. deg=0 은 파지점 방향을 화면 아래로 두는 기준."""
    f = f / np.linalg.norm(f)
    v = np.array([0.0, 0.0, 0.0675]) - pos
    u0 = -(v - (v @ f) * f); u0 /= np.linalg.norm(u0)      # 파지점 반대편 = 화면 위
    yc0 = np.cross(u0, f); yc0 /= np.linalg.norm(yc0)
    th = np.radians(deg)
    return np.cos(th) * u0 + np.sin(th) * yc0

WSET = [("P1", np.array([0.060, -0.075, 0.005]), np.array([-0.487, 0.393, 0.780]), 90.0),
        ("P2", np.array([0.040, -0.060, 0.010]), None, 90.0)]
# P2 는 짧은 팔 대안 — forward 는 P1 과 같은 조준 규칙으로 근사
WSET[1] = ("P2", WSET[1][1], np.array([-0.487, 0.393, 0.780]), 90.0)
WCANDS = [dict(name=f"{tag}_r{r:03d}", pos=pos, f=_focal(h), u=_roll(pos, fwd, r), fwd=fwd)
          for tag, pos, fwd, h in WSET for r in (0, 90, 180, 270)]
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
    JAW_Z0 = float(DATA["finger_z0"])
    JAW_W, JAW_T = map(float, DATA["jaw_wt"])
    BODY_X, BODY_Y, BODY_Z = map(float, DATA["body_xyz"])
    BODY_Z0, BODY_Z1 = map(float, DATA["body_z"])
    GAP_CLOSE = float(DATA["jaw_gap_closed"])
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
                        scale=np.array([1.60, 2.00, 0.05]), color=np.array([0.72, 0.72, 0.70]))
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
    F_HALF = (JAW_T / 2, JAW_W / 2, BEAM_L / 2)
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

    x_open = GAP_CLOSE / 2 + F_HALF[0]   # 파지 순간이므로 닫힘 기준
    static_box("/World/gbase", (0, 0, (BODY_Z0 + BODY_Z1) / 2),
               (BODY_X / 2, BODY_Y / 2, BODY_Z / 2), (0.85, 0.85, 0.9))
    static_box("/World/gfL", (-x_open, 0, JAW_Z0), F_HALF, (0.2, 0.2, 0.25), geom_off=(0, 0, BEAM_L / 2))
    static_box("/World/gfR", (+x_open, 0, JAW_Z0), F_HALF, (0.2, 0.2, 0.25), geom_off=(0, 0, BEAM_L / 2))

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
        q_w = lookat_quat_wxyz(c["fwd"], c["u"])      # 전방 = 조준 벡터 (틸트 반영)
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
        for c, cam in wcams:
            try:
                wp, wq = cam.prim.GetAttribute("xformOp:translate"), None
            except Exception:
                pass
            try:
                cw, cq = cam.get_world_pose()
                Tf = kin.fk(q)
                Rw = Rotation.from_quat([cq[1], cq[2], cq[3], cq[0]]).as_matrix()
                loc_p = Tf[:3, :3].T @ (cw - Tf[:3, 3])
                loc_R = Tf[:3, :3].T @ Rw
                print(f"POSE {c['name']} {tag}: local_pos(mm)={np.round(loc_p*1000,1)}\n"
                      f"     local_R cols x={np.round(loc_R[:,0],3)} y={np.round(loc_R[:,1],3)} "
                      f"z={np.round(loc_R[:,2],3)}\n"
                      f"     기대 fwd={np.round(c['fwd'],3)}", flush=True)
                K = cam.get_intrinsics_matrix()
                px = cam.get_image_coords_from_world_points(np.array([CUBE_PICK]))
                print(f"DIAG {c['name']} {tag}: K_fx={K[0,0]:.1f} K_fy={K[1,1]:.1f} "
                      f"cx={K[0,2]:.1f} cy={K[1,2]:.1f} HFOV={2*np.degrees(np.arctan(320/K[0,0])):.1f}° "
                      f"cube_px={np.round(px,1)}", flush=True)
            except Exception as e:
                print("DIAG fail", c["name"], repr(e), flush=True)
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
