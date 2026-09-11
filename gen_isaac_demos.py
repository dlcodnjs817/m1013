#!/usr/bin/env python3
"""Isaac 시연 대량 생성 — 스크립트 전문가 + weld + 두 카메라 렌더 → LeRobot v2.1 데이터셋.

  cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/gen_isaac_demos.py --n 10 --out m1013_isaac_v8_test

계획(2026-09-11, 사용자 ①안): OMX 사람 시연 대신 Isaac 안에서 큐브를 무작위로 놓고 IK 전문가가 집는 장면을
실제 M1013·툴·손목캠 기하로 찍어 ACT 사전학습 데이터를 만든다. 형식은 v6 와 완전히 같아 학습 스크립트를
안 고친다 (parquet + h264 mp4 + meta). 큐브는 닫힘 순간 플랜지에 **weld**(운동학 고정) — 생성엔 성공 시연만
필요하고 접촉 물리는 평가에서만 쓴다.

핵심 파라미터는 전부 CLI 로 — 특히 --table_z (작업대 높이) 는 월요일 실측 후 바꿔 재생성한다.
"""
import sys, os, json, time, argparse, subprocess
ap = argparse.ArgumentParser()
ap.add_argument('--n', type=int, default=10)
ap.add_argument('--start', type=int, default=0, help='시작 episode_index')
ap.add_argument('--out', default='m1013_isaac_v8_test', help='HF 캐시 dlcodnjs/ 아래 데이터셋 이름')
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--table_z', type=float, default=0.4624, help='상판 높이 (m). 큐브 중심 = table_z + 0.0175')
ap.add_argument('--ws_scale', type=float, default=1.5, help='v6 집는/놓는 영역 확장 배율')
ap.add_argument('--no_dr', action='store_true', help='도메인 무작위화 끄기')
ap.add_argument('--preview', action='store_true', help='에피소드별 4프레임 컨택트시트 저장')
ap.add_argument('--dry', action='store_true', help='Isaac 없이 전문가 궤적만 검증')
args = ap.parse_args()

import numpy as np
sys.path.insert(0, '/home/kim/m1013')
from m1013_kin import M1013Kin
import wristcam_pose as WP

HF = '/home/kim/physical_ai_tools/docker/huggingface/lerobot/dlcodnjs'
OUT = f'{HF}/{args.out}'
FPS = 30; W, H = 640, 480
CUBE = 0.035; TCP = WP.TCP
G_OPEN, G_CLOSED, G_TH, G_RAMP = 0.69, -0.02, 0.459, 5
TASK = 'Pick up the blue cube and place it in the place zone.'
# v6 시연 분포 (159 ep 실측, TCP 기준 m) — ws_scale 로 중심 기준 확장
PICK_BOX = np.array([[0.706, -0.325], [0.908, -0.200]])
PLACE_BOX = np.array([[0.684, -0.278], [0.877, 0.042]])
GRASP_YAW0 = np.radians(158.8)          # v6 파지 시 플랜지 x축 yaw 중앙값
Q0S = np.load('/home/kim/m1013/sim_out/v6_start_q.npy')
kin = M1013Kin()
rng = np.random.default_rng(args.seed + args.start)


# ============================ 전문가 ============================
def minjerk(n):
    s = np.linspace(0, 1, n); return 10 * s**3 - 15 * s**4 + 6 * s**5


def rotz(a):
    c, s = np.cos(a), np.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def rot_axis(axis, a):
    axis = axis / np.linalg.norm(axis); K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * (K @ K)


def slerp(R0, R1, s):
    from scipy.spatial.transform import Rotation as Rt, Slerp
    return Slerp([0, 1], Rt.from_matrix([R0, R1]))(s).as_matrix()


def expand(box, k):
    c = box.mean(0); return c + (box - c) * k


def grasp_R(cube_yaw, tilt_dir, tilt):
    """플랜지 z 가 아래(-Z), x 축 yaw 는 큐브 yaw 의 90° 배수 중 v6 관습(159°)에 가장 가까운 것. 사람 손처럼 살짝 기울임."""
    cands = [cube_yaw + k * np.pi / 2 for k in range(-4, 5)]
    psi = min(cands, key=lambda p: abs((p - GRASP_YAW0 + np.pi) % (2 * np.pi) - np.pi))
    R = rotz(psi) @ np.diag([1.0, -1.0, -1.0])        # x=yaw 방향, z=아래
    return rot_axis(np.array([np.cos(tilt_dir), np.sin(tilt_dir), 0]), tilt) @ R


def expert(cube_pick, cube_yaw, cube_place, table_z):
    """→ (q[T,6], grip[T], t_close, t_open, cube_pose_fn) 또는 None(IK 실패)."""
    zc = table_z + CUBE / 2
    q_start = Q0S[rng.integers(len(Q0S))] + rng.normal(0, np.radians(1.0), 6)
    T0 = kin.fk(q_start); p0 = T0[:3, 3] + T0[:3, 2] * TCP; R0 = T0[:3, :3]
    tilt = abs(rng.normal(0, np.radians(6))); tdir = rng.uniform(0, 2 * np.pi)
    Rg = grasp_R(cube_yaw, tdir, tilt)
    Rp = grasp_R(cube_yaw + rng.normal(0, np.radians(10)), rng.uniform(0, 2 * np.pi), abs(rng.normal(0, np.radians(6))))
    lift = rng.uniform(0.06, 0.11)
    jit = lambda s: rng.normal(0, s, 3) * np.array([1, 1, 0.5])
    P_pick = np.array([cube_pick[0], cube_pick[1], zc]); P_place = np.array([cube_place[0], cube_place[1], zc])
    tscale = rng.uniform(0.85, 1.3)
    # (목표 TCP, 목표 R, 구간 시간 s, 구간 뒤 그리퍼 상태)
    W_ = [(P_pick + [0, 0, lift] + jit(0.01), Rg, 3.0, 'open'),
          (P_pick + jit(0.003), Rg, 1.3, 'open'), (None, None, 0.45, 'close'),
          (P_pick + [0, 0, lift] + jit(0.01), Rg, 1.2, 'closed'),
          (P_place + [0, 0, lift] + jit(0.012), Rp, 3.0, 'closed'),
          (P_place + jit(0.004), Rp, 1.3, 'closed'), (None, None, 0.45, 'open_'),
          (P_place + [0, 0, lift] + jit(0.01), Rp, 1.2, 'open'), (None, None, 0.5, 'open')]
    qs, grips, p_cur, R_cur, q_cur = [], [], p0.copy(), R0.copy(), q_start.copy()
    g_cur = G_OPEN; t_close = t_open = None
    # 저주파 흔들림 (사람 손)
    wob_f = rng.uniform(0.15, 0.4, 3); wob_a = rng.uniform(0.0, 0.004, 3); wob_p = rng.uniform(0, 2 * np.pi, 3)
    for (p_tgt, R_tgt, dur, gstate) in W_:
        n = max(2, int(round(dur * tscale * FPS)))
        if p_tgt is None:                                   # 정지 구간 (그리퍼 동작)
            for i in range(n):
                qs.append(q_cur.copy()); grips.append(g_cur)
            if gstate == 'close': t_close = len(qs) - n; g_cur = G_CLOSED
            elif gstate == 'open_': t_open = len(qs) - n; g_cur = G_OPEN
            continue
        s = minjerk(n + 1)[1:]
        for i in range(n):
            tt = len(qs) / FPS
            p = p_cur + (p_tgt - p_cur) * s[i] + wob_a * np.sin(2 * np.pi * wob_f * tt + wob_p)
            R = slerp(R_cur, R_tgt, s[i])
            p_fl = p - R[:, 2] * TCP                        # TCP → 플랜지
            q, st = kin.solve(p_fl, R, q_cur)
            if st != 'ok' or np.abs(q - q_cur).max() > np.radians(6):
                return None
            q_cur = q; qs.append(q.copy()); grips.append(g_cur)
        p_cur, R_cur = p_tgt.copy(), R_tgt.copy()
    q = np.array(qs); grip = np.array(grips, float)
    # 그리퍼 값 램프 (v6 전이 ~5 프레임)
    for t_ev, (a, b) in ((t_close, (G_OPEN, G_CLOSED)), (t_open, (G_CLOSED, G_OPEN))):
        for k in range(G_RAMP):
            if t_ev + k < len(grip): grip[t_ev + k] = a + (b - a) * (k + 1) / G_RAMP
    return q, grip, t_close, t_open


def sample_episode(table_z):
    for _ in range(20):
        pk = rng.uniform(*expand(PICK_BOX, args.ws_scale)); pl = rng.uniform(*expand(PLACE_BOX, args.ws_scale))
        if np.linalg.norm(pk - pl) < 0.08: continue
        yaw = rng.uniform(0, np.pi / 2)
        r = expert(pk, yaw, pl, table_z)
        if r is not None:
            return dict(pick=pk, place=pl, yaw=yaw, q=r[0], grip=r[1], t_close=r[2], t_open=r[3])
    return None


if args.dry:
    ok = 0; lens = []
    for i in range(args.n):
        e = sample_episode(args.table_z)
        if e: ok += 1; lens.append(len(e['q'])); print('ep%03d  %d 프레임 (%.1f s)  닫힘 %d 열림 %d  큐브 (%.3f, %.3f) yaw %.0f°' % (i, len(e['q']), len(e['q']) / FPS, e['t_close'], e['t_open'], *e['pick'], np.degrees(e['yaw'])))
    print('전문가 성공 %d/%d · 평균 %.0f 프레임' % (ok, args.n, np.mean(lens) if lens else 0)); sys.exit(0)


# ============================ Isaac ============================
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})
import traceback, struct, io
try:
    from isaacsim.core.api import World
    from isaacsim.core.api.objects import VisualCuboid
    from isaacsim.core.utils.stage import add_reference_to_stage, get_current_stage
    from isaacsim.core.prims import SingleArticulation
    from isaacsim.core.utils.types import ArticulationAction
    from isaacsim.sensors.camera import Camera
    from pxr import UsdPhysics, UsdGeom, UsdLux, Gf, Vt
    from PIL import Image
    import pandas as pd

    world = World(stage_units_in_meters=1.0, physics_dt=1 / 60, rendering_dt=1 / 60); stage = get_current_stage()
    add_reference_to_stage("/home/kim/m1013/doosan-robot2/dsr_description2/usd/m1013.usd", "/World/m1013")
    root = [p.GetPath().pathString for p in stage.Traverse() if p.GetPath().pathString.startswith("/World/m1013") and p.HasAPI(UsdPhysics.ArticulationRootAPI)][0]
    # 툴 메시
    raw = open('/home/kim/m1013/cad/tool_assembly_flangelocal.stl', 'rb').read(); ntri = struct.unpack('<I', raw[80:84])[0]
    V = np.frombuffer(raw[84:84 + ntri * 50], dtype=np.uint8).reshape(ntri, 50)[:, 12:48].copy().view('<f4').reshape(-1, 3).astype(float) / 1000
    txf = UsdGeom.Xform.Define(stage, '/World/tool'); t_top, t_rop = txf.AddTranslateOp(), txf.AddOrientOp()
    tm = UsdGeom.Mesh.Define(stage, '/World/tool/geom'); tm.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, p)) for p in V]))
    tm.CreateFaceVertexCountsAttr(Vt.IntArray([3] * ntri)); tm.CreateFaceVertexIndicesAttr(Vt.IntArray(list(range(ntri * 3))))
    tm.CreateDisplayColorAttr([Gf.Vec3f(0.80, 0.80, 0.84)]); tm.CreateSubdivisionSchemeAttr('none')
    art = SingleArticulation(root, name='m1013'); world.scene.add(art)
    sun = UsdLux.DistantLight.Define(stage, '/World/sun'); sun.CreateIntensityAttr(1200.0)
    sun_x = UsdGeom.Xformable(stage.GetPrimAtPath('/World/sun')).AddRotateXYZOp(); sun_x.Set(Gf.Vec3f(-40, 15, 0))
    dome = UsdLux.DomeLight.Define(stage, '/World/dome'); dome.CreateIntensityAttr(350.0)
    table = world.scene.add(VisualCuboid('/World/table', name='table', position=np.array([0.705, -0.15, args.table_z - 0.025]), scale=np.array([1.4, 1.8, 0.05]), color=np.array([0.72, 0.72, 0.70])))
    world.scene.add(VisualCuboid('/World/wall', name='wall', position=np.array([-0.55, 0.0, 1.25]), scale=np.array([0.05, 4.0, 2.5]), color=np.array([0.92, 0.92, 0.90])))
    world.scene.add(VisualCuboid('/World/floor', name='floor', position=np.array([0.5, 0, -0.01]), scale=np.array([6, 6, 0.02]), color=np.array([0.55, 0.56, 0.58])))
    cube = world.scene.add(VisualCuboid('/World/cube', name='cube', position=np.array([0.8, -0.25, args.table_z + CUBE / 2]), size=CUBE, color=np.array([0.1, 0.2, 0.9])))
    cam_w = Camera('/World/wristcam', resolution=(W, H)); cam_f = Camera('/World/frontcam', resolution=(W, H))
    world.reset(); cam_w.initialize(); cam_f.initialize()
    AP = 20.955
    def set_intr(cam, hfov):
        fmm = AP / 2 / np.tan(np.radians(hfov / 2)); cam.set_focal_length(fmm / 10); cam.set_horizontal_aperture(AP / 10); cam.set_vertical_aperture(AP * 0.75 / 10); cam.set_clipping_range(0.005, 30)
    FC = json.load(open('/home/kim/m1013/cameras_v6match.json'))['front_cam']
    # 정면캠은 옛 상판(0.3746)에 맞춰 fit 된 값(z=0.46) — 상판이 올라간 만큼 같이 올려 상판 대비 구도를 보존한다.
    # (09-04 정정 후 "정면캠 재검토 미수행" 항목. 상판 안에 묻혀 검게 찍히던 원인.)
    FRONT_DZ = args.table_z - 0.3746
    FC_POS = np.array(FC['pos']) + [0, 0, FRONT_DZ]; FC_AT = np.array(FC['look_at']) + [0, 0, FRONT_DZ]
    print('정면캠 위치 %s → 상판 대비 %.3f m 위' % (np.round(FC_POS, 3), FC_POS[2] - args.table_z), flush=True)
    set_intr(cam_w, WP.HFOV); set_intr(cam_f, FC['hfov_deg'])
    idx = np.array([art.dof_names.index(f'joint_{i}') for i in range(1, 7)])
    ctrl = art.get_articulation_controller(); ctrl.set_gains(kps=np.full(art.num_dof, 1e6), kds=np.full(art.num_dof, 2e4))

    def quat(R):
        w = np.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
        return Gf.Quatf(float(w), float((R[2, 1] - R[1, 2]) / (4 * w)), float((R[0, 2] - R[2, 0]) / (4 * w)), float((R[1, 0] - R[0, 1]) / (4 * w)))
    def set_xf(path, T):
        UsdGeom.Xformable(stage.GetPrimAtPath(path)).MakeMatrixXform().Set(Gf.Matrix4d(*[float(x) for x in T.T.flatten()]))
    def look(eye, tgt):
        f = tgt - eye; f /= np.linalg.norm(f); r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f)
        T = np.eye(4); T[:3, 0] = r; T[:3, 1] = u; T[:3, 2] = -f; T[:3, 3] = eye; return T
    def hold(q, n, render):
        for _ in range(n):
            ctrl.apply_action(ArticulationAction(joint_positions=q, joint_indices=idx)); world.step(render=render)
    def grab(cam):
        rgba = cam.get_rgba()
        for _ in range(60):
            if getattr(rgba, 'ndim', 0) == 3 and rgba.shape[0] > 1: break
            world.step(render=True); rgba = cam.get_rgba()
        return rgba[:, :, :3].copy()

    def encode(frames, path):
        """h264 yuv420p — v5 와 동일 코덱. 컨테이너의 ffmpeg 로 파이프."""
        cpath = path.replace('/home/kim/physical_ai_tools/docker/huggingface', '/root/.cache/huggingface')
        cmd = ['docker', 'exec', '-i', 'physical_ai_server', 'ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
               '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'medium', '-crf', '18', '-g', '2', cpath]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE); p.stdin.write(np.stack(frames).tobytes()); p.stdin.close(); p.wait()
        if p.returncode != 0: raise RuntimeError('ffmpeg 실패 ' + path)

    # HF 캐시는 컨테이너(root) 소유 → 디렉터리는 컨테이너에서 만들고 모두에게 쓰기 권한을 준다
    C_OUT = OUT.replace('/home/kim/physical_ai_tools/docker/huggingface', '/root/.cache/huggingface')
    subs = ['data/chunk-000', 'videos/chunk-000/observation.images.camera1', 'videos/chunk-000/observation.images.camera2', 'meta'] + (['preview'] if args.preview else [])
    subprocess.run(['docker', 'exec', 'physical_ai_server', 'bash', '-c', 'mkdir -p ' + ' '.join(f'{C_OUT}/{d}' for d in subs) + f' && chmod -R a+rwX {C_OUT}'], check=True)

    # 워밍업
    q_w = Q0S[0]; art.set_joint_positions(q_w, joint_indices=idx); hold(q_w, 30, False)
    for i in range(400):
        hold(q_w, 1, True); r_ = cam_w.get_rgba()
        if getattr(r_, 'ndim', 0) == 3 and r_.shape[0] > 1: break

    ep_meta, ep_stats = [], []
    t_all = time.time()
    for k in range(args.n):
        ep = args.start + k; t0 = time.time()
        e = sample_episode(args.table_z)
        if e is None: print('ep%03d 전문가 실패 — 건너뜀' % ep, flush=True); continue
        q, grip, tc, to = e['q'], e['grip'], e['t_close'], e['t_open']; n = len(q)
        # ---- 도메인 무작위화 ----
        if not args.no_dr:
            sun.GetIntensityAttr().Set(float(rng.uniform(700, 2000))); sun_x.Set(Gf.Vec3f(float(rng.uniform(-70, -25)), float(rng.uniform(-40, 40)), 0))
            dome.GetIntensityAttr().Set(float(rng.uniform(150, 600)))
            g_ = rng.uniform(0.55, 0.85)
            UsdGeom.Gprim(stage.GetPrimAtPath('/World/table')).GetDisplayColorAttr().Set([Gf.Vec3f(g_ + rng.uniform(-0.04, 0.04), g_, g_ - rng.uniform(0, 0.06))])
            UsdGeom.Gprim(stage.GetPrimAtPath('/World/cube')).GetDisplayColorAttr().Set([Gf.Vec3f(float(rng.uniform(0.05, 0.25)), float(rng.uniform(0.15, 0.35)), float(rng.uniform(0.75, 1.0)))])
            cam_jit = np.r_[rng.normal(0, 0.003, 3)]; cam_rot = rng.normal(0, np.radians(2), 3)
            f_jit = rng.normal(0, 0.01, 3)
        else:
            cam_jit = np.zeros(3); cam_rot = np.zeros(3); f_jit = np.zeros(3)
        T_cam_fl = WP.basis(); T_cam_fl[:3, 3] += cam_jit
        T_cam_fl[:3, :3] = rot_axis(np.array([1.0, 0, 0]), cam_rot[0]) @ rot_axis(np.array([0, 1.0, 0]), cam_rot[1]) @ T_cam_fl[:3, :3]
        set_xf('/World/frontcam', look(FC_POS + f_jit, FC_AT))
        # ---- 큐브 초기 자세 ----
        Rc = rotz(e['yaw']); Tc_w = np.eye(4); Tc_w[:3, :3] = Rc; Tc_w[:3, 3] = [e['pick'][0], e['pick'][1], args.table_z + CUBE / 2]
        Tc_in_fl = None
        # ---- 기록 ----
        art.set_joint_positions(q[0], joint_indices=idx); hold(q[0], 20, False)
        T_fl = kin.fk(q[0]); t_top.Set(Gf.Vec3d(*map(float, T_fl[:3, 3]))); t_rop.Set(quat(T_fl[:3, :3]))
        set_xf('/World/wristcam', T_fl @ T_cam_fl); cube.set_world_pose(position=Tc_w[:3, 3])
        hold(q[0], 8, True)                                   # 텔레포트 직후 첫 프레임이 검게 나오는 것 방지
        F1, F2, states, actions = [], [], [], []
        for t in range(n):
            T_fl = kin.fk(q[t])
            t_top.Set(Gf.Vec3d(*map(float, T_fl[:3, 3]))); t_rop.Set(quat(T_fl[:3, :3]))
            set_xf('/World/wristcam', T_fl @ T_cam_fl)
            if tc is not None and t == tc + G_RAMP: Tc_in_fl = np.linalg.inv(T_fl) @ Tc_w        # weld
            if to is not None and t == to: Tc_in_fl = None; Tc_w[2, 3] = args.table_z + CUBE / 2   # 놓기 → 상판 위
            if Tc_in_fl is not None: Tc_w = T_fl @ Tc_in_fl
            Qc = quat(Tc_w[:3, :3]); cube.set_world_pose(position=Tc_w[:3, 3], orientation=np.array([Qc.GetReal(), *Qc.GetImaginary()]))
            art.set_joint_positions(q[t], joint_indices=idx); hold(q[t], 1, True)
            F1.append(grab(cam_w)); F2.append(grab(cam_f))
            a = np.r_[q[t], grip[t]].astype(np.float32); s = np.r_[q[max(0, t - 1)], grip[max(0, t - 1)]].astype(np.float32)   # state = action[t-1]
            actions.append(a); states.append(s)
        # ---- 저장 ----
        df = pd.DataFrame({'timestamp': (np.arange(n) / FPS).astype(np.float32), 'frame_index': np.arange(n), 'episode_index': np.full(n, ep),
                           'index': np.arange(n), 'task_index': np.zeros(n, int), 'observation.state': list(states), 'action': list(actions)})
        df.to_parquet(f'{OUT}/data/chunk-000/episode_{ep:06d}.parquet')
        encode(F1, f'{OUT}/videos/chunk-000/observation.images.camera1/episode_{ep:06d}.mp4')
        encode(F2, f'{OUT}/videos/chunk-000/observation.images.camera2/episode_{ep:06d}.mp4')
        if args.preview:
            sheet = Image.new('RGB', (W * 4, H * 2))
            for j, t in enumerate((0, tc, (tc + to) // 2, to)):
                sheet.paste(Image.fromarray(F1[t]), (j * W, 0)); sheet.paste(Image.fromarray(F2[t]), (j * W, H))
            sheet.resize((W * 2, H)).save(f'{OUT}/preview/ep{ep:06d}.jpg', quality=85)
        A, S = np.stack(actions).astype(float), np.stack(states).astype(float)
        st = {'observation.state': dict(min=S.min(0).tolist(), max=S.max(0).tolist(), mean=S.mean(0).tolist(), std=S.std(0).tolist(), count=[n]),
              'action': dict(min=A.min(0).tolist(), max=A.max(0).tolist(), mean=A.mean(0).tolist(), std=A.std(0).tolist(), count=[n])}
        for key, Fr in (('observation.images.camera1', F1), ('observation.images.camera2', F2)):
            X = np.stack(Fr[::10]).astype(float) / 255; ch = X.reshape(-1, 3)
            st[key] = dict(min=ch.min(0).reshape(3, 1, 1).tolist(), max=ch.max(0).reshape(3, 1, 1).tolist(), mean=ch.mean(0).reshape(3, 1, 1).tolist(), std=ch.std(0).reshape(3, 1, 1).tolist(), count=[len(X)])
        for key, arr in (('timestamp', np.arange(n) / FPS), ('frame_index', np.arange(n)), ('episode_index', np.full(n, ep)), ('index', np.arange(n)), ('task_index', np.zeros(n))):
            arr = np.asarray(arr, float); st[key] = dict(min=[arr.min()], max=[arr.max()], mean=[arr.mean()], std=[arr.std()], count=[n])
        ep_stats.append(dict(episode_index=ep, stats=st)); ep_meta.append(dict(episode_index=ep, tasks=[TASK], length=n, pick=e['pick'].tolist(), place=e['place'].tolist(), cube_yaw_deg=float(np.degrees(e['yaw'])), t_close=tc, t_open=to))
        print('ep%03d  %d 프레임  큐브 (%.3f, %.3f) yaw %3.0f° → (%.3f, %.3f)   %.1f s' % (ep, n, *e['pick'], np.degrees(e['yaw']), *e['place'], time.time() - t0), flush=True)

    # ---- meta ----
    with open(f'{OUT}/meta/episodes.jsonl', 'a') as f:
        for d in ep_meta: f.write(json.dumps(d) + '\n')
    with open(f'{OUT}/meta/episodes_stats.jsonl', 'a') as f:
        for d in ep_stats: f.write(json.dumps(d) + '\n')
    with open(f'{OUT}/meta/tasks.jsonl', 'w') as f: f.write(json.dumps(dict(task=TASK, task_index=0)) + '\n')
    eps = [json.loads(l) for l in open(f'{OUT}/meta/episodes.jsonl')]
    info = json.load(open(f'{HF}/m1013_act_pick_and_place_v6_joint/meta/info.json'))
    info.update(robot_type='m1013_isaac', total_episodes=len(eps), total_frames=int(sum(e['length'] for e in eps)), total_videos=2 * len(eps), total_tasks=1,
                splits={'train': f'0:{len(eps)}'})
    for key in ('observation.state', 'action'): info['features'][key]['names'] = ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6', 'gripper']
    info['isaac_gen'] = dict(table_z=args.table_z, ws_scale=args.ws_scale, dr=not args.no_dr, wristcam=dict(pos=WP.CAM_POS.tolist(), fwd=WP.CAM_FWD.tolist(), roll=WP.ROLL, hfov=WP.HFOV), tcp=TCP, seed=args.seed)
    json.dump(info, open(f'{OUT}/meta/info.json', 'w'), indent=1)
    print('\n완료 %d 에피소드 · 총 %d 프레임 · %.1f 분 → %s' % (len(ep_meta), sum(d['length'] for d in ep_meta), (time.time() - t_all) / 60, OUT), flush=True)
except Exception:
    traceback.print_exc()
finally:
    app.close()
