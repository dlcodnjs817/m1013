#!/usr/bin/env python3
"""M1013 + 실물 기하 그리퍼 외관 렌더 — 부착 상태 확인용.

  cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/render_tool_view.py
출력: sim_out/tool_view/*.png
"""
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})

import numpy as np, traceback

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

    D = np.load("/home/kim/m1013/replay_ep000.npz")
    J = D["joints"]; TC = int(D["t_close"]); TG = min(TC + 15, len(J) - 1)
    CUBE_PICK = D["cube_pick"]; CUBE = float(D["cube_size"])
    TABLE_Z = float(D["table_top_z"])
    BEAM_L = float(D["finger_ext"]); JAW_Z0 = float(D["finger_z0"])
    JAW_W, JAW_T = map(float, D["jaw_wt"])
    BODY_X, BODY_Y, BODY_Z = map(float, D["body_xyz"])
    BODY_Z0, BODY_Z1 = map(float, D["body_z"])
    GAP_CLOSE = float(D["jaw_gap_closed"])
    GAP_OPEN = GAP_CLOSE + 2 * float(D["jaw_stroke_half"])
    OUT = "/home/kim/m1013/sim_out/tool_view"; os.makedirs(OUT, exist_ok=True)
    kin = M1013Kin()

    world = World(stage_units_in_meters=1.0, physics_dt=1/60, rendering_dt=1/60)
    world.scene.add_default_ground_plane()
    stage = get_current_stage()
    add_reference_to_stage("/home/kim/m1013/doosan-robot2/dsr_description2/usd/m1013.usd", "/World/m1013")
    root_path = link6_path = None
    for prim in stage.Traverse():
        p = prim.GetPath().pathString
        if p.startswith("/World/m1013"):
            if prim.HasAPI(UsdPhysics.ArticulationRootAPI): root_path = p
            if prim.GetName() == "link_6": link6_path = p
    assert root_path and link6_path

    table = FixedCuboid("/World/table", name="table",
                        position=np.array([0.705, -0.15, TABLE_Z - 0.025]),
                        scale=np.array([0.85, 1.10, 0.05]), color=np.array([0.72, 0.72, 0.70]))
    world.scene.add(table)
    cube = DynamicCuboid("/World/cube", name="cube", position=CUBE_PICK, size=CUBE,
                         mass=0.015, color=np.array([0.1, 0.2, 0.9]))
    world.scene.add(cube)

    def quat_of(R):
        qx, qy, qz, qw = Rotation.from_matrix(R).as_quat()
        return Gf.Quatf(float(qw), float(qx), float(qy), float(qz))

    parts = []
    def box(path, off, half, color, geom_off=None):
        L = np.eye(4); L[:3, 3] = off
        xf = UsdGeom.Xform.Define(stage, path)
        top, rop = xf.AddTranslateOp(), xf.AddOrientOp()
        g = UsdGeom.Cube.Define(stage, path + "/geom"); g.CreateSizeAttr(1.0)
        if geom_off is not None: g.AddTranslateOp().Set(Gf.Vec3d(*map(float, geom_off)))
        g.AddScaleOp().Set(Gf.Vec3f(*[2*h for h in half]))
        g.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        parts.append((top, rop, L))

    ADAPT = (0.140, 0.070, 0.012)          # 어댑터 플레이트
    box("/World/adapter", (0, 0, 0.006), tuple(a/2 for a in ADAPT), (0.78, 0.78, 0.82))
    box("/World/gbody", (0, 0, (BODY_Z0+BODY_Z1)/2), (BODY_X/2, BODY_Y/2, BODY_Z/2), (0.85, 0.85, 0.9))
    def set_jaws(gap):
        x = gap/2 + JAW_T/2
        for i, sx in ((2, -1), (3, +1)):
            parts[i][2][0, 3] = sx * x
    box("/World/jawL", (-(GAP_CLOSE/2+JAW_T/2), 0, JAW_Z0), (JAW_T/2, JAW_W/2, BEAM_L/2),
        (0.20, 0.20, 0.25), geom_off=(0, 0, BEAM_L/2))
    box("/World/jawR", (+(GAP_CLOSE/2+JAW_T/2), 0, JAW_Z0), (JAW_T/2, JAW_W/2, BEAM_L/2),
        (0.20, 0.20, 0.25), geom_off=(0, 0, BEAM_L/2))

    def place(T):
        for top, rop, L in parts:
            M = T @ L
            top.Set(Gf.Vec3d(*map(float, M[:3, 3]))); rop.Set(quat_of(M[:3, :3]))

    art = SingleArticulation(root_path, name="m1013"); world.scene.add(art)
    UsdLux.DistantLight.Define(stage, "/World/sun").CreateIntensityAttr(3000.0)
    UsdGeom.Xformable(stage.GetPrimAtPath("/World/sun")).AddRotateXYZOp().Set(Gf.Vec3f(-40, 15, 0))
    UsdLux.DomeLight.Define(stage, "/World/dome").CreateIntensityAttr(900.0)

    def lq(f, u):
        f = np.asarray(f, float); f /= np.linalg.norm(f)
        y = np.cross(u, f); y /= np.linalg.norm(y); z = np.cross(f, y)
        qx, qy, qz, qw = Rotation.from_matrix(np.stack([f, y, z], 1)).as_quat()
        return np.array([qw, qx, qy, qz])

    cams = {}
    for n in ("wide", "tool", "tool2"):
        cams[n] = Camera(f"/World/cam_{n}", resolution=(1280, 960))
    world.reset()
    for n, c in cams.items():
        c.initialize(); c.set_focal_length(2.4 if n == "wide" else 5.0)
        c.set_horizontal_aperture(2.0955); c.set_vertical_aperture(2.0955*3/4)
        c.set_clipping_range(0.02, 40.0)

    dof = art.dof_names
    idx = np.array([dof.index(f"joint_{i}") for i in range(1, 7)])
    ctrl = art.get_articulation_controller()
    ctrl.set_gains(kps=np.full(art.num_dof, 1.0e6), kds=np.full(art.num_dof, 2.0e4))

    def shot(q, tag, gap):
        set_jaws(gap)
        art.set_joint_positions(q, joint_indices=idx)
        T = kin.fk(q); place(T)
        for _ in range(30):
            ctrl.apply_action(ArticulationAction(joint_positions=q, joint_indices=idx))
            world.step(render=False)
        fl = T[:3, 3]
        tool = fl + T[:3, :3] @ np.array([0, 0, 0.042])
        cams["wide"].set_world_pose(position=np.array([2.0, -1.4, 1.15]),
                                    orientation=lq(np.array([0.55, 0.30, 0.45]) - np.array([2.0, -1.4, 1.15]), [0, 0, 1]))
        p2 = tool + np.array([0.16, -0.26, 0.14])
        cams["tool"].set_world_pose(position=p2, orientation=lq(tool - p2, [0, 0, 1]))
        p3 = tool + np.array([-0.05, -0.30, 0.02])
        cams["tool2"].set_world_pose(position=p3, orientation=lq(tool - p3, [0, 0, 1]))
        for _ in range(45): world.step(render=True)
        for n, c in cams.items():
            rgba = c.get_rgba()
            for _ in range(60):
                if rgba is not None and getattr(rgba, "ndim", 0) == 3 and rgba.shape[0] > 1: break
                world.step(render=True); rgba = c.get_rgba()
            Image.fromarray(rgba[:, :, :3]).save(f"{OUT}/{tag}_{n}.png")
            print("SAVED", tag, n, flush=True)

    shot(J[0], "home", GAP_OPEN)
    shot(J[TG], "grasp", GAP_CLOSE)
    print("TOOLVIEW_DONE", flush=True)
except Exception:
    traceback.print_exc()
finally:
    app.close()
