#!/usr/bin/env python3
"""Isaac Sim 물리 재생: v6-M1013 joint 궤적로 파란 큐브 pick&place 재현.

씬: m1013.usd + 테이블(상판 z=0.3746) + 파란 큐브(6cm) + LEHR 근사 평행 그리퍼
    (본체 + 핑거 연장 0.226m, 스트로크 개구 100→48mm 연속 매핑).
실행: cd ~/isaacsim && ./python.sh ~/tx90/m1013/replay_isaac.py [--ep 0] [--no-render]
출력: sim_out/replay_epXXX_result.json + 스냅샷 PNG
"""
import argparse
import json
import os
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--ep", type=int, default=0)
ap.add_argument("--no-render", action="store_true")
ap.add_argument("--calibrate", action="store_true",
                help="큐브 없이 재생하며 핑거 궤적만 기록 (큐브 위치 실증 결정용)")
ap.add_argument("--cube-at", default=None, help="큐브 위치 덮어쓰기 'x,y' (캘리브레이션 결과)")
ap.add_argument("--gap-close", type=float, default=0.031)
ap.add_argument("--video", action="store_true", help="프레임 캡처 → frames_<label>/ PNG")
ap.add_argument("--video-from", type=int, default=0)
ap.add_argument("--video-to", type=int, default=10**9)
ap.add_argument("--video-every", type=int, default=2)
ap.add_argument("--label", default="run")
ap.add_argument("--zoom", action="store_true", help="그립 지점 클로즈업 카메라")
ap.add_argument("--grip-lead", type=int, default=0,
                help="그리퍼 명령 시프트(프레임). 음수=지연 — 큐브가 슬롯에 안착한 뒤 닫기")
ap.add_argument("--pred-npz", default=None,
                help="정책 예측 npz (pred 키, T x 7) — 지정 시 GT 대신 예측 관절/그리퍼로 재생")
ap.add_argument("--gui", action="store_true",
                help="Isaac Sim 창을 띄워 실시간 관람 (마우스로 시점 조작 가능)")
args = ap.parse_args()

from isaacsim import SimulationApp
app = SimulationApp({"headless": not args.gui})

import numpy as np
import traceback

try:
    from isaacsim.core.api import World
    from isaacsim.core.api.objects import DynamicCuboid, FixedCuboid
    from isaacsim.core.api.materials import PhysicsMaterial
    from isaacsim.core.utils.stage import add_reference_to_stage, get_current_stage
    from isaacsim.core.prims import SingleArticulation
    from isaacsim.core.utils.types import ArticulationAction
    from pxr import UsdPhysics, UsdGeom, UsdShade, Gf

    DATA = np.load(f"/home/kim/m1013/replay_ep{args.ep:03d}.npz")
    JOINTS = DATA["joints"]; GRIP = DATA["grip"]
    if args.pred_npz:
        P = np.load(args.pred_npz)["pred"]
        JOINTS = P[:, :6]; GRIP = P[:, 6]
        print(f"정책 예측 재생: {args.pred_npz} ({len(JOINTS)}프레임)", flush=True)
    CUBE_PICK = DATA["cube_pick"]; CUBE_PLACE = DATA["cube_place"]
    CUBE = float(DATA["cube_size"]); TABLE_Z = float(DATA["table_top_z"])
    FLANGE0 = DATA["flange0"]
    OUT = "/home/kim/m1013/sim_out"
    os.makedirs(OUT, exist_ok=True)

    # 그리퍼 기하 (LEHR 일자 장착 + 일자 어태치먼트):
    # 손목 45° 보정 데이터셋에서는 파지 시 플랜지 z 가 세계 수직 → 빔 = 플랜지 z 방향.
    X0 = 0.058            # 핑거 마운트 |x| (개구 폭 기준)
    D_LOCAL = np.array([0.0, 0.0, 1.0])
    BEAM_L = float(DATA["finger_ext"])   # prep 이 파지 기하에서 계산 (마운트→팁)
    F_HALF = (0.008, 0.012, BEAM_L / 2)
    GAP_OPEN, GAP_CLOSE = 0.070, args.gap_close

    def gap_of(a):
        return float(np.clip(np.interp(a, [-0.02, 0.695], [GAP_CLOSE, GAP_OPEN]),
                             GAP_CLOSE, GAP_OPEN))

    def quat_of(R):
        w = np.sqrt(max(0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
        if w > 1e-6:
            x = (R[2, 1] - R[1, 2]) / (4 * w); y = (R[0, 2] - R[2, 0]) / (4 * w)
            z = (R[1, 0] - R[0, 1]) / (4 * w)
        else:
            x, y, z = 1.0, 0.0, 0.0
        return Gf.Quatf(float(w), float(x), float(y), float(z))

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
    print("ART_ROOT:", root_path, "LINK6:", link6_path, flush=True)
    assert root_path and link6_path

    def make_body(path, T, half, mass, color, geom_off=None, geom_quat=None):
        xf = UsdGeom.Xform.Define(stage, path)
        xf.AddTranslateOp().Set(Gf.Vec3d(*map(float, T[:3, 3])))
        xf.AddOrientOp().Set(quat_of(T[:3, :3]))
        UsdPhysics.RigidBodyAPI.Apply(xf.GetPrim())
        m = UsdPhysics.MassAPI.Apply(xf.GetPrim())
        m.CreateMassAttr(mass)
        geo = UsdGeom.Cube.Define(stage, path + "/geom")
        geo.CreateSizeAttr(1.0)
        if geom_off is not None:
            geo.AddTranslateOp().Set(Gf.Vec3d(*map(float, geom_off)))
        if geom_quat is not None:
            geo.AddOrientOp().Set(geom_quat)
        geo.AddScaleOp().Set(Gf.Vec3f(2 * half[0], 2 * half[1], 2 * half[2]))
        geo.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        UsdPhysics.CollisionAPI.Apply(geo.GetPrim())
        return xf.GetPrim(), geo.GetPrim()

    def quat_align_z(d):
        z = np.array([0.0, 0.0, 1.0])
        v = np.cross(z, d)
        w = np.sqrt((1.0 + float(z @ d)) / 2.0)
        return Gf.Quatf(float(w), *map(float, v / (2 * w)))

    def local_T(dx, dy, dz):
        L = np.eye(4); L[:3, 3] = [dx, dy, dz]
        return FLANGE0 @ L

    base_prim, _ = make_body("/World/gripper_base", local_T(0, 0, 0.035),
                             (0.042, 0.032, 0.035), 0.9, (0.85, 0.85, 0.9))
    gq = quat_align_z(D_LOCAL)
    goff = D_LOCAL * BEAM_L / 2
    fingerL, geoL = make_body("/World/fingerL", local_T(-X0, 0, 0.07),
                              F_HALF, 0.05, (0.2, 0.2, 0.25), geom_off=goff, geom_quat=gq)
    fingerR, geoR = make_body("/World/fingerR", local_T(+X0, 0, 0.07),
                              F_HALF, 0.05, (0.2, 0.2, 0.25), geom_off=goff, geom_quat=gq)

    fj = UsdPhysics.FixedJoint.Define(stage, "/World/gripper_fj")
    fj.CreateBody0Rel().SetTargets([link6_path])
    fj.CreateBody1Rel().SetTargets(["/World/gripper_base"])
    fj.CreateLocalPos0Attr(Gf.Vec3f(0, 0, 0))
    fj.CreateLocalPos1Attr(Gf.Vec3f(0, 0, -0.035))

    drives = {}
    for tag, body, sx in [("L", "/World/fingerL", -1.0), ("R", "/World/fingerR", +1.0)]:
        pj = UsdPhysics.PrismaticJoint.Define(stage, f"/World/pj{tag}")
        pj.CreateBody0Rel().SetTargets(["/World/gripper_base"])
        pj.CreateBody1Rel().SetTargets([body])
        pj.CreateAxisAttr("X")
        pj.CreateLocalPos0Attr(Gf.Vec3f(sx * X0, 0, 0.035))
        pj.CreateLocalPos1Attr(Gf.Vec3f(0, 0, 0))
        pj.CreateLowerLimitAttr(-0.06)
        pj.CreateUpperLimitAttr(0.06)
        dr = UsdPhysics.DriveAPI.Apply(pj.GetPrim(), "linear")
        dr.CreateTypeAttr("force")
        dr.CreateStiffnessAttr(8000.0)
        dr.CreateDampingAttr(400.0)
        dr.CreateMaxForceAttr(150.0)
        dr.CreateTargetPositionAttr(0.0)
        drives[tag] = (dr, sx)

    def set_gap(g):
        d = X0 - (g / 2 + F_HALF[0])   # 각 핑거가 안쪽으로 이동할 거리
        for tag, (dr, sx) in drives.items():
            dr.GetTargetPositionAttr().Set(float(-sx * d))

    # 핑거: 고마찰 + 유연 접촉(폼 눌림 근사). 큐브: 보통 마찰(테이블 위에서 그립 안으로 정렬 가능해야 함)
    from pxr import PhysxSchema
    pm = PhysicsMaterial("/World/pm", static_friction=2.0, dynamic_friction=1.8, restitution=0.0)
    pxm = PhysxSchema.PhysxMaterialAPI.Apply(pm.material.GetPrim())
    pxm.CreateCompliantContactStiffnessAttr(3000.0)
    pxm.CreateCompliantContactDampingAttr(100.0)
    for g in (geoL, geoR):
        UsdShade.MaterialBindingAPI.Apply(g).Bind(
            pm.material, bindingStrength=UsdShade.Tokens.strongerThanDescendants,
            materialPurpose="physics")
    pm_cube = PhysicsMaterial("/World/pm_cube", static_friction=0.6, dynamic_friction=0.5,
                              restitution=0.0)

    table = FixedCuboid("/World/table", name="table",
                        position=np.array([0.705, -0.15, TABLE_Z - 0.025]),
                        scale=np.array([0.49, 0.60, 0.05]), color=np.array([0.55, 0.4, 0.25]))
    world.scene.add(table)
    cube = None
    if not args.calibrate:
        cpos = CUBE_PICK.copy()
        if args.cube_at:
            cx, cy = map(float, args.cube_at.split(","))
            cpos = np.array([cx, cy, CUBE_PICK[2]])
        cube = DynamicCuboid("/World/cube", name="cube", position=cpos,
                             size=CUBE, mass=0.015, color=np.array([0.1, 0.2, 0.9]),
                             physics_material=pm_cube)
        world.scene.add(cube)

    art = SingleArticulation(root_path, name="m1013")
    world.scene.add(art)

    cam = None
    if not args.no_render or args.gui:
        from pxr import UsdLux
        sun = UsdLux.DistantLight.Define(stage, "/World/sun")
        sun.CreateIntensityAttr(3000.0)
        UsdGeom.Xformable(sun.GetPrim()).AddRotateXYZOp().Set(Gf.Vec3f(-40, 15, 0))
        dome = UsdLux.DomeLight.Define(stage, "/World/dome")
        dome.CreateIntensityAttr(800.0)

    if not args.no_render and not args.gui:
        from isaacsim.sensors.camera import Camera
        # Camera 클래스 world-axes 규약: +X 전방, +Z 상방
        if args.zoom:
            tgt = CUBE_PICK + np.array([0.0, 0.0, 0.02])
            pos = tgt + np.array([1.15, -1.20, 0.60]) * 0.5
        else:
            pos = np.array([1.75, -1.35, 1.05]); tgt = np.array([0.60, -0.15, 0.45])
        xc = tgt - pos; xc /= np.linalg.norm(xc)
        yc = np.cross([0, 0, 1.0], xc); yc /= np.linalg.norm(yc)
        zc = np.cross(xc, yc)
        Rc = np.stack([xc, yc, zc], axis=1)
        w = np.sqrt(max(0, 1 + Rc[0, 0] + Rc[1, 1] + Rc[2, 2])) / 2
        q = np.array([w, (Rc[2, 1] - Rc[1, 2]) / (4 * w), (Rc[0, 2] - Rc[2, 0]) / (4 * w),
                      (Rc[1, 0] - Rc[0, 1]) / (4 * w)])
        cam = Camera("/World/cam", resolution=(1280, 720))
        cam.set_world_pose(position=pos, orientation=q)

    world.reset()
    if cam:
        cam.initialize()

    dof = art.dof_names
    print("DOFS:", dof, flush=True)
    arm_idx = np.array([dof.index(f"joint_{i}") for i in range(1, 7)])
    art.set_joint_positions(JOINTS[0], joint_indices=arm_idx)
    ctrl = art.get_articulation_controller()
    n = art.num_dof
    kps = np.full(n, 1.0e6); kds = np.full(n, 2.0e4)
    ctrl.set_gains(kps=kps, kds=kds)
    set_gap(gap_of(GRIP[0]))

    # 정착
    for _ in range(30):
        ctrl.apply_action(ArticulationAction(joint_positions=JOINTS[0], joint_indices=arm_idx))
        world.step(render=False)

    qs = art.get_joint_positions(joint_indices=arm_idx)
    print("정착 후 관절 오차(deg):", np.round(np.degrees(qs - JOINTS[0]), 3), flush=True)

    if cam and args.video:
        for _ in range(12):
            world.render()

    T = len(JOINTS)
    from isaacsim.core.prims import SingleXFormPrim
    xfL, xfR = SingleXFormPrim("/World/fingerL"), SingleXFormPrim("/World/fingerR")
    traj = {"t": [], "pL": [], "qL": [], "pR": [], "qR": []}
    snap_frames = sorted({0, 150, int(DATA["t_close"]), int(DATA["t_close"]) + 40,
                          320, int(DATA["t_open"]), T - 1}
                         | ({224, 232, 240, 248, 256, 264, 272} if args.zoom else set()))
    track_err_max = 0.0; cube_z_max = -1.0
    log = []
    for t in range(T):
        ctrl.apply_action(ArticulationAction(joint_positions=JOINTS[t], joint_indices=arm_idx))
        set_gap(gap_of(GRIP[int(np.clip(t + args.grip_lead, 0, T - 1))]))
        for _ in range(2):
            world.step(render=bool(args.gui))
        qnow = art.get_joint_positions(joint_indices=arm_idx)
        track_err_max = max(track_err_max, float(np.degrees(np.max(np.abs(qnow - JOINTS[t])))))
        cp = np.zeros(3)
        if cube is not None:
            cp, _ = cube.get_world_pose()
            cube_z_max = max(cube_z_max, float(cp[2]))
        if 150 <= t <= 430:
            pL, qL = xfL.get_world_pose(); pR, qR = xfR.get_world_pose()
            traj["t"].append(t)
            traj["pL"].append(np.asarray(pL)); traj["qL"].append(np.asarray(qL))
            traj["pR"].append(np.asarray(pR)); traj["qR"].append(np.asarray(qR))
        if 226 <= t <= 300 and t % 4 == 2:
            allq = art.get_joint_positions()
            iL, iR = dof.index("pjL"), dof.index("pjR")
            gap_meas = 2 * (X0 - abs(float(allq[iL]))) - 2 * F_HALF[0]
            gap_cmd = gap_of(GRIP[t])
            print(f"  갭 f{t}: 명령={gap_cmd*1000:.0f}mm 실측={gap_meas*1000:.0f}mm "
                  f"(pjL={float(allq[iL])*1000:+.1f} pjR={float(allq[iR])*1000:+.1f}) "
                  f"큐브 z={float(cp[2]):.3f} xy=({float(cp[0]):.3f},{float(cp[1]):.3f})", flush=True)
        if t % 60 == 0:
            log.append(dict(t=t, cube=[round(float(v), 3) for v in cp]))
            print(f"f{t}: cube={np.round(np.asarray(cp),3)} trackErr(max)={track_err_max:.2f}°", flush=True)
        if (cam and args.video and args.video_from <= t <= args.video_to
                and t % args.video_every == 0):
            world.render()
            rgba = cam.get_rgba()
            if rgba is not None and getattr(rgba, "size", 0):
                from PIL import Image
                os.makedirs(f"{OUT}/frames_{args.label}", exist_ok=True)
                Image.fromarray(rgba[..., :3].astype(np.uint8)).save(
                    f"{OUT}/frames_{args.label}/{t:04d}.png")
        elif cam and t in snap_frames:
            for _ in range(3):
                world.render()
            rgba = cam.get_rgba()
            if rgba is not None and getattr(rgba, "size", 0):
                from PIL import Image
                Image.fromarray(rgba[..., :3].astype(np.uint8)).save(f"{OUT}/ep{args.ep:03d}_f{t:04d}.png")

    np.savez(f"{OUT}/fingertraj_{args.label}.npz",
             **{k: np.asarray(v) for k, v in traj.items()})
    if cube is None:
        print("RESULT: calibrate 완료 (큐브 없음)", flush=True)
        raise SystemExit(0)
    cp, _ = cube.get_world_pose()
    err_xy = float(np.linalg.norm(np.asarray(cp[:2]) - CUBE_PLACE[:2]))
    lifted = cube_z_max > CUBE_PICK[2] + 0.05
    on_table = abs(float(cp[2]) - CUBE_PICK[2]) < 0.02
    success = err_xy < 0.05 and lifted and on_table
    res = dict(ep=args.ep, success=bool(success), cube_final=[round(float(v), 4) for v in cp],
               cube_place_target=[round(float(v), 4) for v in CUBE_PLACE],
               err_xy_mm=round(err_xy * 1000, 1), lifted=bool(lifted),
               cube_z_max=round(cube_z_max, 3), on_table_final=bool(on_table),
               track_err_max_deg=round(track_err_max, 2), log=log)
    json.dump(res, open(f"{OUT}/replay_ep{args.ep:03d}_result.json", "w"), indent=1)
    print("RESULT:", json.dumps(res), flush=True)
    if args.gui:
        print("재생 끝 — 창을 닫으면 종료됩니다 (마우스로 자유롭게 둘러보세요)", flush=True)
        while app.is_running():
            world.render()
except Exception:
    traceback.print_exc()
    sys.exit(1)
finally:
    app.close()
