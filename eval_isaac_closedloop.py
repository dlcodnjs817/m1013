#!/usr/bin/env python3
"""ACT 정책 닫힌 루프 평가 — Isaac 이 매 스텝 두 카메라를 렌더해 컨테이너의 ACT 서버로 보내고, 받은 관절로 움직인다.

  cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/eval_isaac_closedloop.py \
      --ckpt /root/train_m1013_act_v6_tcp0725/checkpoints/last/pretrained_model --n 20

파지 판정은 기하 (weld 는 쓰지 않는다 — 정책이 큐브를 빗나가 닫아도 성공으로 찍히면 안 된다):
  닫힘 순간 큐브 중심이 플랜지 로컬에서 |x| ≤ 12 mm (조 사이), |y| ≤ 15 mm (조 폭), |z − TCP| ≤ 20 mm 이면 잡힘.
  잡힌 뒤 열면 큐브는 그 자리에 놓인다(상판 높이로 스냅).
지표: 파지율, 들기율(잡고 5 cm 이상 상승), 놓기율(들어서 집는 자리에서 8 cm 이상 떨어진 곳에 내려놓음), TCP–큐브 최소거리.
"""
import sys, os, json, time, argparse, subprocess, socket, struct, pickle
ap = argparse.ArgumentParser()
ap.add_argument('--ckpt', required=True, help='컨테이너 안 체크포인트 경로 (pretrained_model)')
ap.add_argument('--n', type=int, default=20); ap.add_argument('--seed', type=int, default=100)
ap.add_argument('--table_z', type=float, default=0.4624); ap.add_argument('--ws_scale', type=float, default=1.0, help='큐브 배치 영역 배율 (1.0 = v6 분포)')
ap.add_argument('--max_steps', type=int, default=600); ap.add_argument('--port', type=int, default=5555)
ap.add_argument('--dr', action='store_true'); ap.add_argument('--tag', default='eval')
ap.add_argument('--no_server', action='store_true', help='서버를 직접 띄웠을 때')
args = ap.parse_args()
import numpy as np
sys.path.insert(0, '/home/kim/m1013')
from m1013_kin import M1013Kin
import wristcam_pose as WP

FPS = 30; CUBE = 0.035; TCP = WP.TCP; G_TH = 0.459; G_OPEN = 0.69
PICK_BOX = np.array([[0.706, -0.325], [0.908, -0.200]])      # gen_isaac_demos 와 동일 (v6 분포)
Q0S = np.load('/home/kim/m1013/sim_out/v6_start_q.npy')
rng = np.random.default_rng(args.seed)
kin = M1013Kin()
OUT = f'/home/kim/m1013/sim_out/{args.tag}'; os.makedirs(OUT, exist_ok=True)


def rotz(a):
    c, s = np.cos(a), np.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


# ---------------- ACT 서버 ----------------
if not args.no_server:
    subprocess.run('docker exec -i physical_ai_server bash -c "cat > /workspace/act_server.py" < /home/kim/m1013/act_server.py', shell=True, check=True)   # workspace 는 root 소유
    subprocess.run(['docker', 'exec', 'physical_ai_server', 'bash', '-c', f'pkill -f "act_server.py --ckpt" ; true'], check=False)
    subprocess.Popen(['docker', 'exec', 'physical_ai_server', 'python3', '/workspace/act_server.py', '--ckpt', args.ckpt, '--port', str(args.port)],
                     stdout=open(f'{OUT}/act_server.log', 'w'), stderr=subprocess.STDOUT)
sock = None
for _ in range(120):
    try:
        sock = socket.create_connection(('127.0.0.1', args.port), timeout=2); break
    except OSError:
        time.sleep(1)
if sock is None: raise SystemExit('ACT 서버 연결 실패 — ' + f'{OUT}/act_server.log 확인')
sock.settimeout(60)


def rpc(m):
    b = pickle.dumps(m, protocol=4); sock.sendall(struct.pack('<I', len(b)) + b)
    n = struct.unpack('<I', sock.recv(4, socket.MSG_WAITALL))[0]; return pickle.loads(sock.recv(n, socket.MSG_WAITALL))


# ---------------- Isaac ----------------
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})
import traceback
try:
    from isaac_scene import PickScene
    from PIL import Image
    sc = PickScene(args.table_z, kin); sc.warmup(Q0S[0])
    results = []
    for ep in range(args.n):
        pk = rng.uniform(*PICK_BOX) if args.ws_scale == 1.0 else rng.uniform(*(PICK_BOX.mean(0) + (PICK_BOX - PICK_BOX.mean(0)) * args.ws_scale))
        yaw = rng.uniform(0, np.pi / 2); q = Q0S[rng.integers(len(Q0S))] + rng.normal(0, np.radians(1.0), 6)
        if args.dr: sc.randomize(rng)
        Tc = np.eye(4); Tc[:3, :3] = rotz(yaw); Tc[:3, 3] = [pk[0], pk[1], args.table_z + CUBE / 2]
        sc.teleport(q); sc.pose_tool(kin.fk(q)); sc.set_cube(Tc); sc.hold(q, 8, True)
        rpc({'cmd': 'reset'})
        state = np.r_[q, G_OPEN].astype(np.float32)
        attached = None; grasped = lifted = placed = False; min_d = 1e9; max_dq = 0.0; t_grasp = t_place = None; frames_keep = {}
        g_prev = G_OPEN; pick0 = Tc[:3, 3].copy(); t_end = args.max_steps
        for t in range(args.max_steps):
            im1, im2 = sc.frames()
            if t in (0,): frames_keep[t] = (im1, im2)
            act = rpc({'cmd': 'act', 'state': state, 'img1': im1, 'img2': im2})['action']
            q_new, g = act[:6].astype(float), float(act[6])
            max_dq = max(max_dq, float(np.degrees(np.abs(q_new - state[:6]).max())))
            T_fl = sc.step_robot(q_new)
            tcp = T_fl[:3, 3] + T_fl[:3, 2] * TCP; d = np.linalg.norm(tcp - Tc[:3, 3]); min_d = min(min_d, d)
            if attached is None and g_prev >= G_TH > g:                       # 닫힘 순간 — 기하 판정
                loc = T_fl[:3, :3].T @ (Tc[:3, 3] - T_fl[:3, 3])
                if abs(loc[0]) <= 0.012 and abs(loc[1]) <= 0.015 and abs(loc[2] - TCP) <= 0.020:
                    attached = np.linalg.inv(T_fl) @ Tc; grasped = True; t_grasp = t; frames_keep['grasp'] = (im1, im2)
            if attached is not None:
                Tc = T_fl @ attached
                if Tc[2, 3] > args.table_z + CUBE / 2 + 0.05: lifted = True
                if g_prev < G_TH <= g:                                        # 열림 → 놓기
                    attached = None; Tc[2, 3] = args.table_z + CUBE / 2; Tc[:3, :3] = rotz(np.arctan2(Tc[1, 0], Tc[0, 0]))
                    if lifted and np.linalg.norm(Tc[:2, 3] - pick0[:2]) >= 0.08: placed = True; t_place = t; frames_keep['place'] = (im1, im2)
                    t_end = min(args.max_steps, t + 30)
            sc.set_cube(Tc)
            g_prev = g; state = act.astype(np.float32)                        # state = action[t-1]
            if t >= t_end: break
        frames_keep['end'] = sc.frames()
        r = dict(ep=ep, pick=pk.tolist(), yaw_deg=float(np.degrees(yaw)), grasped=grasped, lifted=lifted, placed=placed, t_grasp=t_grasp, t_place=t_place,
                 min_tcp_cube_mm=round(min_d * 1000, 1), max_dq_deg=round(max_dq, 2), steps=t + 1, final_cube=Tc[:3, 3].tolist())
        results.append(r)
        sheet = Image.new('RGB', (640 * 4, 480 * 2))
        for j, k in enumerate((0, 'grasp', 'place', 'end')):
            if k in frames_keep: sheet.paste(Image.fromarray(frames_keep[k][0]), (j * 640, 0)); sheet.paste(Image.fromarray(frames_keep[k][1]), (j * 640, 480))
        sheet.resize((1280, 480)).save(f'{OUT}/ep{ep:03d}.jpg', quality=85)
        print('ep%02d  큐브 (%.3f, %.3f) yaw %2.0f°  파지 %s 들기 %s 놓기 %s  최소거리 %5.1f mm  maxΔq %.1f°  %d 스텝'
              % (ep, *pk, np.degrees(yaw), '✅' if grasped else '❌', '✅' if lifted else '❌', '✅' if placed else '❌', min_d * 1000, max_dq, t + 1), flush=True)
    n = len(results)
    summ = dict(ckpt=args.ckpt, n=n, grasp_rate=sum(r['grasped'] for r in results) / n, lift_rate=sum(r['lifted'] for r in results) / n,
                place_rate=sum(r['placed'] for r in results) / n, median_min_dist_mm=float(np.median([r['min_tcp_cube_mm'] for r in results])),
                table_z=args.table_z, ws_scale=args.ws_scale, dr=args.dr, seed=args.seed)
    json.dump(dict(summary=summ, episodes=results), open(f'{OUT}/results.json', 'w'), indent=1)
    print('\n요약  파지 %.0f%%  들기 %.0f%%  놓기 %.0f%%  · TCP-큐브 최소거리 중앙값 %.1f mm  (%d 에피소드)  → %s/results.json'
          % (summ['grasp_rate'] * 100, summ['lift_rate'] * 100, summ['place_rate'] * 100, summ['median_min_dist_mm'], n, OUT), flush=True)
except Exception:
    traceback.print_exc()
finally:
    try: rpc({'cmd': 'quit'})
    except Exception: pass
    app.close()
