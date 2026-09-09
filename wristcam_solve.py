#!/usr/bin/env python3
"""손목캠 §8 재정합 — link_6 prim 프레임 ↔ 운동학 플랜지 프레임 보정 후 배치·검증.

  cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/wristcam_solve.py
출력: sim_out/wristcam_solve/*.png  +  콘솔에 link6→flange 보정행렬
"""
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})

import numpy as np, traceback, sys

try:
    from isaacsim.core.api import World
    from isaacsim.core.api.objects import DynamicCuboid, FixedCuboid
    from isaacsim.core.utils.stage import add_reference_to_stage, get_current_stage
    from isaacsim.core.prims import SingleArticulation
    from isaacsim.core.utils.types import ArticulationAction
    from isaacsim.sensors.camera import Camera
    from pxr import UsdPhysics, UsdGeom, UsdLux, Gf
    from PIL import Image
    import os, sys
    sys.path.insert(0, "/home/kim/m1013")
    from m1013_kin import M1013Kin

    # ---- §8 확정 후보 (플랜지 로컬) ----
    CAM_POS = np.array([0.060, -0.075, 0.005])
    CAM_FWD = np.array([-0.487, 0.393, 0.780])
    # HFOV: 인자로 덮어쓸 수 있다 (기본 90.0 = §8 확정값).
    #   U20CAM-720P 를 1280x720 -> 960x720 중앙크롭 -> 640x480 으로 받으면 85.6
    HFOV = float(sys.argv[1]) if len(sys.argv) > 1 else 90.0
    AP_H = 20.955

    D = np.load("/home/kim/m1013/replay_ep000.npz")
    J = D["joints"]; TC = int(D["t_close"]); TG = min(TC + 15, len(J) - 1)
    CUBE_PICK = D["cube_pick"]; CUBE = float(D["cube_size"]); TABLE_Z = float(D["table_top_z"])
    BEAM_L = float(D["finger_ext"]); JAW_Z0 = float(D["finger_z0"])
    JAW_W, JAW_T = map(float, D["jaw_wt"]); GAP_CLOSE = float(D["jaw_gap_closed"])
    BODY_X, BODY_Y, BODY_Z = map(float, D["body_xyz"])
    BODY_Z0, BODY_Z1 = map(float, D["body_z"])
    GZ = float(D["tcp"])
    OUT = "/home/kim/m1013/sim_out/wristcam_solve"; os.makedirs(OUT, exist_ok=True)
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

    world.scene.add(FixedCuboid("/World/table", name="table",
        position=np.array([0.705, -0.15, TABLE_Z - 0.025]),
        scale=np.array([1.4, 1.8, 0.05]), color=np.array([0.72, 0.72, 0.70])))
    world.scene.add(FixedCuboid("/World/wall", name="wall",
        position=np.array([-0.55, 0.0, 1.25]), scale=np.array([0.05, 4.0, 2.5]),
        color=np.array([0.92, 0.92, 0.90])))
    world.scene.add(DynamicCuboid("/World/cube", name="cube", position=CUBE_PICK,
        size=CUBE, mass=0.015, color=np.array([0.1, 0.2, 0.9])))

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
    box("/World/adapter", (0, 0, 0.006), (0.070, 0.035, 0.006), (0.78, 0.78, 0.82))
    box("/World/gbody", (0, 0, (BODY_Z0+BODY_Z1)/2), (BODY_X/2, BODY_Y/2, BODY_Z/2), (0.85, 0.85, 0.9))
    xj = GAP_CLOSE/2 + JAW_T/2
    box("/World/jawL", (-xj, 0, JAW_Z0), (JAW_T/2, JAW_W/2, BEAM_L/2), (0.20,0.20,0.25), (0,0,BEAM_L/2))
    box("/World/jawR", (+xj, 0, JAW_Z0), (JAW_T/2, JAW_W/2, BEAM_L/2), (0.20,0.20,0.25), (0,0,BEAM_L/2))
    def quat_of(R):
        w = np.sqrt(max(0, 1+R[0,0]+R[1,1]+R[2,2]))/2
        if w > 1e-8:
            x,y,z = (R[2,1]-R[1,2])/(4*w), (R[0,2]-R[2,0])/(4*w), (R[1,0]-R[0,1])/(4*w)
        else: x,y,z = 1.0,0.0,0.0
        return Gf.Quatf(float(w), float(x), float(y), float(z))
    def place(T):
        for top, rop, L in parts:
            M = T @ L
            top.Set(Gf.Vec3d(*map(float, M[:3,3]))); rop.Set(quat_of(M[:3,:3]))

    art = SingleArticulation(root_path, name="m1013"); world.scene.add(art)
    UsdLux.DistantLight.Define(stage, "/World/sun").CreateIntensityAttr(3000.0)
    UsdGeom.Xformable(stage.GetPrimAtPath("/World/sun")).AddRotateXYZOp().Set(Gf.Vec3f(-40,15,0))
    UsdLux.DomeLight.Define(stage, "/World/dome").CreateIntensityAttr(900.0)

    cam = Camera(f"{link6_path}/wristcam", resolution=(640, 480))
    cam_prim = stage.GetPrimAtPath(f"{link6_path}/wristcam")
    world.reset()
    cam.initialize()
    fmm = AP_H / 2 / np.tan(np.radians(HFOV/2))
    cam.set_focal_length(fmm/10); cam.set_horizontal_aperture(AP_H/10)
    cam.set_vertical_aperture(AP_H*480/640/10); cam.set_clipping_range(0.01, 30.0)

    dof = art.dof_names
    idx = np.array([dof.index(f"joint_{i}") for i in range(1,7)])
    ctrl = art.get_articulation_controller()
    ctrl.set_gains(kps=np.full(art.num_dof, 1.0e6), kds=np.full(art.num_dof, 2.0e4))

    def goto(q):
        art.set_joint_positions(q, joint_indices=idx); place(kin.fk(q))
        for _ in range(30):
            ctrl.apply_action(ArticulationAction(joint_positions=q, joint_indices=idx))
            world.step(render=False)

    def l6_world():
        M = UsdGeom.Xformable(stage.GetPrimAtPath(link6_path)).ComputeLocalToWorldTransform(0)
        A = np.array(M).T                      # Gf 는 행 우선
        T = np.eye(4); T[:3,:3] = A[:3,:3]; T[:3,3] = A[:3,3]
        return T

    # ---- link_6 prim → 운동학 플랜지 보정 ----
    goto(J[TG])
    T_l6, T_fl = l6_world(), kin.fk(J[TG])
    DELTA = np.linalg.inv(T_l6) @ T_fl          # 플랜지 프레임을 link_6 좌표로
    print("link6→flange 보정 DELTA:"); print(np.round(DELTA, 5), flush=True)

    # ---- 카메라 배치 (USD 카메라 규약: -Z 전방 / +Y 상방) ----
    f = CAM_FWD / np.linalg.norm(CAM_FWD)
    v = np.array([0.0, 0.0, GZ]) - CAM_POS
    up = -(v - (v @ f) * f); up /= np.linalg.norm(up)     # 파지점을 화면 아래로
    yc = np.cross(up, f); yc /= np.linalg.norm(yc)
    T_cam_fl = np.eye(4)
    T_cam_fl[:3, 0] = -yc; T_cam_fl[:3, 1] = up; T_cam_fl[:3, 2] = -f
    T_cam_fl[:3, 3] = CAM_POS
    def place_cam(q):
        # ★ DELTA 를 자세마다 다시 계산해야 한다.
        #   USD 아티큘레이션의 운동학과 m1013_kin.fk 가 완전히 같지 않아서,
        #   J[TG] 에서 구한 정적 DELTA 를 쓰면 다른 자세에서 카메라가 최대 190 mm 어긋난다.
        T = (np.linalg.inv(l6_world()) @ kin.fk(q)) @ T_cam_fl
        xf = UsdGeom.Xformable(cam_prim); xf.ClearXformOpOrder()
        xf.AddTransformOp().Set(Gf.Matrix4d(*T.T.flatten().tolist()))

    place_cam(J[TG])

    def shot(t, tag):
        goto(J[t])
        place_cam(J[t])                       # 자세가 바뀌었으니 카메라를 다시 건다
        for _ in range(45): world.step(render=True)
        cw, _ = cam.get_world_pose(); Tf = kin.fk(J[t])
        loc = Tf[:3,:3].T @ (cw - Tf[:3,3])
        px = cam.get_image_coords_from_world_points(np.array([CUBE_PICK]))[0]
        qerr = np.abs(loc - CAM_POS).max()*1000   # mm
        print(f"{tag}: 카메라 플랜지로컬(mm)={np.round(loc*1000,1)}  큐브 px={np.round(px,1)} "
              f"(정규화 u={(px[0]-320)/320:+.2f} v={(px[1]-240)/240:+.2f})  카메라오차 {qerr:.3f} mm", flush=True)
        rgba = cam.get_rgba()
        for _ in range(60):
            if rgba is not None and getattr(rgba,"ndim",0)==3 and rgba.shape[0]>1: break
            world.step(render=True); rgba = cam.get_rgba()
        try:
            Image.fromarray(rgba[:,:,:3]).save(f"{OUT}/{tag}.png")
        except Exception as e:
            # 렌더 버퍼가 안 올라와도 픽셀 좌표 출력은 살린다 (검증의 본체는 좌표다)
            print(f"{tag}: RGBA 저장 실패 — {e}", flush=True)

    for t, tag in [(max(0,TC-90),"a_approach90"), (max(0,TC-45),"b_approach45"),
                   (TC,"c_close"), (TG,"d_grasp")]:
        shot(t, tag)
    print("SOLVE_DONE", flush=True)
except Exception:
    traceback.print_exc()
finally:
    app.close()
