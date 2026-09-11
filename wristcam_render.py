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
    from isaacsim.core.api.objects import VisualCuboid
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
    _pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    HFOV = float(_pos[0]) if _pos else 85.6
    AP_H = 20.955
    STL = "/home/kim/m1013/cad/tool_assembly_flangelocal.stl"
    HIDE_ROBOT = "--norobot" in sys.argv                    # A/B: 로봇 링크가 화면에 들어오는지 확인용
    HIDE_TOOL = "--notool" in sys.argv                      # A/B: 툴 메시가 뭘 가리는지 확인용
    OUT = "/home/kim/m1013/sim_out/wristcam_render" + ("_norobot" if HIDE_ROBOT else "") + ("_notool" if HIDE_TOOL else "")
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
    if HIDE_TOOL:
        UsdGeom.Imageable(stage.GetPrimAtPath("/World/tool")).MakeInvisible()

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
    if HIDE_ROBOT:
        UsdGeom.Imageable(stage.GetPrimAtPath("/World/m1013")).MakeInvisible()
    # 조명 — 3000/900 은 흰 재질에서 클리핑됐다 (큐브까지 245,245,245). 낮춘다.
    UsdLux.DistantLight.Define(stage, "/World/sun").CreateIntensityAttr(1200.0)
    UsdGeom.Xformable(stage.GetPrimAtPath("/World/sun")).AddRotateXYZOp().Set(Gf.Vec3f(-40, 15, 0))
    UsdLux.DomeLight.Define(stage, "/World/dome").CreateIntensityAttr(350.0)

    D0 = np.load("/home/kim/m1013/replay_ep000.npz")
    TABLE_Z = float(D0["table_top_z"]); CUBE = float(D0["cube_size"]); GZ = float(D0["tcp"])
    # 상판·벽·큐브는 **시각 전용**. 렌더용으로 키운 상판(1.4×1.8, x 0.005~)이 충돌체이면
    # 로봇 어깨(link_2)를 관통해 팔이 명령 자세로 못 올라간다 — 2026-09-11 에 관절 2 가 −0.4 rad 에
    # 못 박히고 link_6 가 fk 에서 95~858 mm 어긋난 채 렌더된 원인. 물리는 로봇만 돌리면 된다.
    world.scene.add(VisualCuboid("/World/table", name="table",
        position=np.array([0.705, -0.15, TABLE_Z - 0.025]),
        scale=np.array([1.4, 1.8, 0.05]), color=np.array([0.72, 0.72, 0.70])))
    world.scene.add(VisualCuboid("/World/wall", name="wall",
        position=np.array([-0.55, 0.0, 1.25]), scale=np.array([0.05, 4.0, 2.5]),
        color=np.array([0.92, 0.92, 0.90])))
    cube = world.scene.add(VisualCuboid("/World/cube", name="cube",
        position=np.array(D0["cube_pick"]), size=CUBE,
        color=np.array([0.1, 0.2, 0.9])))

    # 카메라를 link_6 자식이 아니라 **월드 프림**으로 둔다. 툴 메시와 같이 운동학 플랜지 자세에
    # 직접 놓으면 DELTA(link_6 prim ↔ fk 플랜지 보정)가 아예 필요 없다 — 09-09 버그 계열 원천 차단.
    # 물리 팔이 자세에서 몇 mm 흔들려도 카메라·툴·큐브·상판은 전부 운동학 프레임에 정합된다.
    cam = Camera("/World/wristcam", resolution=(640, 480))
    cam_prim = stage.GetPrimAtPath("/World/wristcam")
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

    def hold(q, n, render):
        """드라이브 명령을 **매 스텝** 재적용하며 진행한다. 렌더 스텝에서 apply_action 을 빼먹으면
        어깨(joint_2)가 중력에 처져 캡처 순간 link_6 가 수백 mm 어긋난다 (2026-09-11 실측 95~766 mm).
        카메라·툴은 운동학으로 놓이므로 제자리지만, 처진 팔의 손목이 화면에 들어온다."""
        for _ in range(n):
            ctrl.apply_action(ArticulationAction(joint_positions=q, joint_indices=idx))
            world.step(render=render)

    def goto(q, cube_pos):
        art.set_joint_positions(q, joint_indices=idx)
        cube.set_world_pose(position=cube_pos)
        hold(q, 30, False)
        T_fl = kin.fk(q)
        place_tool(T_fl)
        return T_fl

    def place_cam(T_fl):
        T = T_fl @ T_cam_fl                                      # 월드 = 플랜지(fk) · 카메라(플랜지로컬)
        # Camera 프림에는 이미 quatd orient op 이 있어 AddOrientOp(float) 은 타입 충돌을
        # 일으킨다. 행렬 op 하나로 덮어쓴다 (Gf 는 행벡터 규약이라 T.T 로 채운다 — 진단으로 확인).
        M = Gf.Matrix4d(*[float(x) for x in T.T.flatten()])
        UsdGeom.Xformable(cam_prim).MakeMatrixXform().Set(M)

    def verify(T_fl):
        """프림에서 실제 자세를 읽어 검산 — 카메라 위치·전방, 툴 위치.
        (l6 @ inv(l6) @ X == X 식은 동어반복이라 아무것도 검증하지 못한다.)"""
        A = np.array(UsdGeom.Xformable(cam_prim).ComputeLocalToWorldTransform(0)).T
        cam_p = T_fl[:3, :3].T @ (A[:3, 3] - T_fl[:3, 3])          # 플랜지 로컬 (m)
        cam_f = T_fl[:3, :3].T @ (-A[:3, 2] / np.linalg.norm(A[:3, 2]))
        B = np.array(UsdGeom.Xformable(stage.GetPrimAtPath("/World/tool")).ComputeLocalToWorldTransform(0)).T
        tool_err = np.linalg.norm(B[:3, 3] - T_fl[:3, 3]) * 1000.0
        f_ = CAM_FWD / np.linalg.norm(CAM_FWD)
        # 캡처 순간 로봇(USD link_6)이 명령 자세에 있는가 — 카메라·툴은 운동학이라 이걸 안 보면 모른다
        L6 = np.array(UsdGeom.Xformable(stage.GetPrimAtPath(link6_path)).ComputeLocalToWorldTransform(0)).T
        rob_err = np.linalg.norm(L6[:3, 3] - T_fl[:3, 3]) * 1000.0
        qn = art.get_joint_positions()[idx]
        print("      로봇 link_6 ↔ fk 플랜지 %.2f mm · 관절 %s" % (rob_err, np.round(qn, 2)), flush=True)
        # Isaac 이 큐브를 어디로 투영하는지 vs 내 기하 투영 — 둘이 다르면 카메라 규약 문제
        cp_w = np.array(cube.get_world_pose()[0], dtype=float)
        px = cam.get_image_coords_from_world_points(cp_w[None, :])[0]
        Tc = T_fl @ T_cam_fl
        Pc = Tc[:3, :3].T @ (cp_w - Tc[:3, 3])
        th = np.tan(np.radians(HFOV / 2))
        mine = ((Pc[0] / -Pc[2]) / th + 1) * 320, (-(Pc[1] / -Pc[2]) / (th * 0.75) + 1) * 240
        print("      큐브 px  Isaac (%.0f, %.0f)   내 투영 (%.0f, %.0f)   카메라앞 %s"
              % (px[0], px[1], mine[0], mine[1], Pc[2] < 0), flush=True)
        return (np.linalg.norm(cam_p - CAM_POS) * 1000.0,
                float(np.degrees(np.arccos(np.clip(cam_f @ f_, -1, 1)))), tool_err)

    print("HFOV %.1f°  카메라 플랜지로컬 (%.0f, %.0f, %.0f) mm"
          % (HFOV, *(CAM_POS * 1000)), flush=True)
    # 초기 워밍업 — 재부팅 직후 셰이더 컴파일이 수백 프레임을 잡아먹는다. 한 번만 치른다.
    D_ = np.load("/home/kim/m1013/replay_ep000.npz")
    place_cam(goto(D_["joints"][0], np.array(D_["cube_pick"], dtype=float)))
    for i in range(600):
        hold(D_["joints"][0], 1, True)
        r_ = cam.get_rgba()
        if r_ is not None and getattr(r_, "ndim", 0) == 3 and r_.shape[0] > 1:
            print("렌더 파이프라인 준비 완료 (%d 프레임)" % (i + 1), flush=True); break
    else:
        print("경고: 600 프레임 후에도 렌더 버퍼 없음", flush=True)

    worst_err = 0.0
    for ep in ("000", "050", "130"):
        D = np.load(f"/home/kim/m1013/replay_ep{ep}.npz")
        J, TC = D["joints"], int(D["t_close"])
        cp = np.array(D["cube_pick"], dtype=float)
        # 프레임을 TCP-큐브 3D 거리로 고른다 (wristcam_preview.py 와 동일). t_close+15 는
        # 이미 큐브를 든 뒤라 (큐브가 집는 위치에 고정된 이 렌더에서는) 파지 순간이 아니다.
        Ts_ = [kin.fk(J[k]) for k in range(len(J))]
        tcp_ = np.array([T_[:3, 3] + T_[:3, 2] * GZ for T_ in Ts_])
        dist_ = np.linalg.norm(tcp_ - cp, axis=1) * 1000.0
        g_ = int(np.argmin(dist_[:min(TC + 20, len(J))]))
        def before(d_mm):
            c_ = np.where(dist_[:g_ + 1] >= d_mm)[0]
            return int(c_[-1]) if len(c_) else 0
        for tag, t in (("a_far", before(300)), ("b_near", before(180)),
                       ("c_pre", before(110)), ("d_grasp", g_)):
            T_fl_ = goto(J[t], cp)
            place_cam(T_fl_)
            hold(J[t], 60, True)                      # 팔 유지 + 디노이저 수렴
            pe, ae, te = verify(T_fl_)
            worst_err = max(worst_err, pe, te)
            rgba = cam.get_rgba()
            for _ in range(90):
                if rgba is not None and getattr(rgba, "ndim", 0) == 3 and rgba.shape[0] > 1:
                    break
                hold(J[t], 1, True); rgba = cam.get_rgba()
            if getattr(rgba, "ndim", 0) != 3:
                print("  ep%s %-11s 렌더 버퍼 없음 — 건너뜀" % (ep, tag), flush=True); continue
            Image.fromarray(rgba[:, :, :3]).save(f"{OUT}/ep{ep}_{tag}.png")
            print("  ep%s %-11s frame %4d  카메라 위치오차 %.3f mm · 전방각오차 %.3f° · 툴 위치오차 %.3f mm"
                  % (ep, tag, t, pe, ae, te), flush=True)
    print("\n최악 위치오차 %.3f mm (0 이어야 정상)" % worst_err)
    print("저장 위치:", OUT)

except Exception:
    traceback.print_exc()
finally:
    app.close()
