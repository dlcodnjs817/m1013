#!/usr/bin/env python3
"""ACT 추론 서버 — 컨테이너(physical_ai_server) 안에서 실행. Isaac(호스트)이 localhost TCP 로 관측을 보내면 행동을 돌려준다.

  docker exec -d physical_ai_server python3 /root/ros2_ws/src/physical_ai_tools/../../../../home/kim/m1013/act_server.py ...
  (실제 실행은 eval_isaac_closedloop.py 가 docker exec 로 띄운다)

프로토콜: [4바이트 길이][pickle]  요청 {cmd: 'reset'|'act'|'quit', state: f32[7], img1: u8[H,W,3], img2: u8[H,W,3]}
         응답 {action: f32[7]} — 영상은 데이터셋과 같은 규약(uint8 RGB → float/255, CHW)으로 넣는다.
"""
import argparse, socket, struct, pickle, time
import numpy as np, torch
from lerobot.policies.act.modeling_act import ACTPolicy
ap = argparse.ArgumentParser(); ap.add_argument('--ckpt', required=True); ap.add_argument('--port', type=int, default=5555); ap.add_argument('--device', default='cuda')
a = ap.parse_args()
policy = ACTPolicy.from_pretrained(a.ckpt); policy.to(a.device).eval(); policy.reset()
print('정책 로드', a.ckpt, 'chunk', policy.config.chunk_size, 'n_action_steps', policy.config.n_action_steps, flush=True)
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); srv.bind(('127.0.0.1', a.port)); srv.listen(1)
print('listening', a.port, flush=True)


def recv(c):
    h = c.recv(4, socket.MSG_WAITALL)
    if len(h) < 4: return None
    n = struct.unpack('<I', h)[0]; b = c.recv(n, socket.MSG_WAITALL); return pickle.loads(b)


def send(c, o):
    b = pickle.dumps(o, protocol=4); c.sendall(struct.pack('<I', len(b)) + b)


while True:
    c, _ = srv.accept(); n_act = 0; t0 = time.time()
    while True:
        m = recv(c)
        if m is None or m['cmd'] == 'quit': break
        if m['cmd'] == 'reset': policy.reset(); send(c, {'ok': True}); continue
        with torch.inference_mode():
            batch = {'observation.state': torch.from_numpy(m['state']).float().unsqueeze(0).to(a.device)}
            for k, im in (('observation.images.camera1', m['img1']), ('observation.images.camera2', m['img2'])):
                batch[k] = torch.from_numpy(im).permute(2, 0, 1).float().div(255).unsqueeze(0).to(a.device)
            act = policy.select_action(batch).squeeze(0).cpu().numpy().astype(np.float32)
        send(c, {'action': act}); n_act += 1
    c.close(); print('세션 종료 %d 행동 %.1f s' % (n_act, time.time() - t0), flush=True)
    if m is not None and m['cmd'] == 'quit': break
