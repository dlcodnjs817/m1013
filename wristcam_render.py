#!/usr/bin/env python3
"""손목캠 실사 렌더 — 진짜 툴 메시(브래킷 포함)를 붙여 카메라가 뭘 보는지 확인한다.

  cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/wristcam_render.py [HFOV]

09-07 미완 항목 16 "Isaac 씬에 실제 형상 메시 부착"을 여기서 처리한다.
wristcam_solve.py 는 툴을 npz 의 박스 프리미티브로 근사했기 때문에 **브래킷이 화면을
가리는지 볼 수 없었다.** 이 스크립트는 `cad/tool_assembly_flangelocal.stl` 을 그대로
UsdGeom.Mesh 로 올린다 — 어댑터·그리퍼·조·핑거·밸브 브래킷·손목캠 브래킷 전부 포함.

출력: sim_out/wristcam_render/<ep>_<tag>.png
"""
import sys
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})

import numpy as np, traceback

try:
    import os, struct
    from isaacsim.core.api import World
    from isaacsim.core.api.objects import DynamicCuboid, FixedCuboid
    from isaacsim.core.utils.stage import add_reference_to_stage, get_current_stage
    from isaacsim.core.prims import SingleArticulation
    from isaacsim.core.utils.types import ArticulationAction
    from isaacsim.sensors.camera import Camera
    from pxr import UsdPhysics, UsdGeom, UsdLux, Gf, Vt
    from PIL import Image
    sys.path.insert(0, "/home/kim/m1013")
    from m1013_kin import M1013Kin

    # ---- 2026-09-11 확정 손목캠 (플랜지 로컬, m) ----
    CAM_POS = np.array([0.035, -0.045, 0.000])
    CAM_FWD = np.array([-0.487, 0.393, 0.780])
    HFOV = float(sys.argv[1]) if len(sys.argv) > 1 else 85.6
    AP_H = 20.955
    STL = "/home/kim/m1013/cad/tool_assembly_flangelocal.stl"
    OUT = "/home/kim/m1013/sim_out/wristcam_render"
    os.makedirs(OUT, exist_ok=True)
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

    # ---- 툴 메시 (플랜지 로컬 mm → m) ----
    raw = open(STL, "rb").read()
    ntri = struct.unpack("<I", raw[80:84])[0]
    tri = np.frombuffer(raw[84:84 + ntri * 50], dtype=np.uint8).reshape(ntri, 50)
    V = tri[:, 12:48].copy().view("<f4").reshape(-1, 3).astype(np.float64) / 1000.0
    print("툴 메시 %d 삼각형 · bbox(m) X %.3f~%.3f Y %.3f~%.3f Z %.3f~%.3f"
          % (ntri, V[:,0].min(), V[:,0].max(), V[:,1].min(), V[:,1].max(), V[:,2].min(), V[:,2].max()),
          flush=True)
    tool_xf = UsdGeom.Xform.Define(stage, "/World/tool")
    tool_top, tool_rop = tool_xf.AddTranslateOp(), tool_xf.AddOrientOp()
    mesh = UsdGeom.Mesh.Define(stage, "/World/tool/geom")
    mesh.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, p)) for p in V]))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray([3] * ntri))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(list(range(ntri * 3))))
    mesh.CreateDisplayColorAttr([Gf.Vec3f(0.80, 0.80, 0.84)])
    mesh.CreateSubdivisionSchemeAttr("none")

    def quat_of(R):
        w = np.sqrt(max(0.0, 1 + R[0,0] + R[1,1] + R[2,2])) / 2
        if w > 1e-8:
            x, y, z = (R[2,1]-R[1,2])/(4*w), (R[0,2]-R[2,0])/(4*w), (R[1,0]-R[0,1])/(4*w)
        else:
            x, y, z = 1.0, 0.0, 0.0
        return Gf.Quatf(float(w), float(x), float(y), float(z))

    def place_tool(T):
        tool_top.Set(Gf.Vec3d(*map(float, T[:3, 3])))
        tool_rop.Set(quat_of(T[:3, :3]))

    art = SingleArticulation(root_path, name="m1013"); world.scene.add(art)
    UsdLux.DistantLight.Define(stage, "/World/sun").CreateIntensityAttr(3000.0)
    UsdGeom.Xformable(stage.GetPrimAtPath("/World/sun")).AddRotateXYZOp().Set(Gf.Vec3f(-40, 15, 0))
    UsdLux.DomeLight.Define(stage, "/World/dome").CreateIntensityAttr(900.0)

    D0 = np.load("/home/kim/m1013/replay_ep000.npz")
    TABLE_Z = float(D0["table_top_z"]); CUBE = float(D0["cube_size"]); GZ = float(D0["tcp"])
    world.scene.add(FixedCuboid("/World/table", name="table",
        position=np.array([0.705, -0.15, TABLE_Z - 0.025]),
        scale=np.array([1.4, 1.8, 0.05]), color=np.array([0.72, 0.72, 0.70])))
    world.scene.add(FixedCuboid("/World/wall", name="wall",
        position=np.array([-0.55, 0.0, 1.25]), scale=np.array([0.05, 4.0, 2.5]),
        color=np.array([0.92, 0.92, 0.90])))
    cube = world.scene.add(DynamicCuboid("/World/cube", name="cube",
        position=np.array(D0["cube_pick"]), size=CUBE, mass=0.015,
        color=np.array([0.1, 0.2, 0.9])))

    cam = Camera(f"{link6_path}/wristcam", resolution=(640, 480))
    cam_prim = stage.GetPrimAtPath(f"{link6_path}/wristcam")
    world.reset(); cam.initialize()
    fmm = AP_H / 2 / np.tan(np.radians(HFOV / 2))
    cam.set_focal_length(fmm / 10); cam.set_horizontal_aperture(AP_H / 10)
    cam.set_vertical_aperture(AP_H * 480 / 640 / 10); cam.set_clipping_range(0.005, 30.0)

    dof = art.dof_names
    idx = np.array([dof.index(f"joint_{i}") for i in range(1, 7)])
    ctrl = art.get_articulation_controller()
    ctrl.set_gains(kps=np.full(art.num_dof, 1.0e6), kds=np.full(art.num_dof, 2.0e4))

    def l6_world():
        M = UsdGeom.Xformable(stage.GetPrimAtPath(link6_path)).ComputeLocalToWorldTransform(0)
        A = np.array(M).T
        T = np.eye(4); T[:3, :3] = A[:3, :3]; T[:3, 3] = A[:3, 3]
        return T

    f = CAM_FWD / np.linalg.norm(CAM_FWD)
    v = np.array([0.0, 0.0, GZ]) - CAM_POS
    up = -(v - (v @ f) * f); up /= np.linalg.norm(up)
    yc = np.cross(up, f); yc /= np.linalg.norm(yc)
    T_cam_fl = np.eye(4)
    T_cam_fl[:3, 0] = -yc; T_cam_fl[:3, 1] = up; T_cam_fl[:3, 2] = -f
    T_cam_fl[:3, 3] = CAM_POS

    def goto(q, cube_pos):
        art.set_joint_positions(q, joint_indices=idx)
        cube.set_world_pose(position=cube_pos)
        for _ in range(30):
            ctrl.apply_action(ArticulationAction(joint_positions=q, joint_indices=idx))
            world.step(render=False)
        T_fl = kin.fk(q)
        place_tool(T_fl)
        # DELTA 는 자세마다 재계산 (09-09 버그 재발 방지)
        T = (np.linalg.inv(l6_world()) @ T_fl) @ T_cam_fl
        # Camera 프림에는 이미 quatd orient op 이 있어 AddOrientOp(float) 은 타입 충돌을
        # 일으킨다. 행렬 op 하나로 덮어쓰는 편이 안전하다.
        M = Gf.Matrix4d(*[float(x) for x in T.T.flatten()])
        UsdGeom.Xformable(cam_prim).MakeMatrixXform().Set(M)
        # 기하 자기일관성 체크 — 카메라 월드 == fk 로 계산한 값이어야 한다
        cw = l6_world() @ T
        want = T_fl @ T_cam_fl
        return float(np.linalg.norm(cw[:3, 3] - want[:3, 3])) * 1000.0

    print("HFOV %.1f°  카메라 플랜지로컬 (%.0f, %.0f, %.0f) mm"
          % (HFOV, *(CAM_POS * 1000)), flush=True)
    worst_err = 0.0
    for ep in ("000", "050", "130"):
        D = np.load(f"/home/kim/m1013/replay_ep{ep}.npz")
        J, TC = D["joints"], int(D["t_close"])
        cp = np.array(D["cube_pick"], dtype=float)
        for tag, t in (("a_approach", max(0, TC - 60)), ("b_mid", max(0, TC - 30)),
                       ("c_close", max(0, TC - 8)), ("d_grasp", min(TC + 15, len(J) - 1))):
            err = goto(J[t], cp)
            worst_err = max(worst_err, err)
            for _ in range(6):
                world.step(render=True)
            Image.fromarray(cam.get_rgba()[:, :, :3]).save(f"{OUT}/ep{ep}_{tag}.png")
            print("  ep%s %-11s frame %4d  카메라 배치오차 %.4f mm" % (ep, tag, t, err), flush=True)
    print("\n최악 카메라 배치오차 %.4f mm (0 이어야 정상)" % worst_err)
    print("저장 위치:", OUT)

except Exception:
    traceback.print_exc()
finally:
    app.close()
