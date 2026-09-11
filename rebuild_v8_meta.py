#!/usr/bin/env python3
"""Isaac 시연 데이터셋 meta 복구 — 생성 도중 전원이 나갔을 때 (2026-09-11).

  cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/rebuild_v8_meta.py --out m1013_isaac_v8

1. data/chunk-000/episode_*.parquet 를 훑어 parquet 와 mp4 두 개가 모두 정상인지 검사 (깨진 것은 삭제 — 보통 꺼지는 순간 쓰던 마지막 1개)
2. meta/episodes.jsonl · episodes_stats.jsonl 에 없는 에피소드는 parquet + mp4 에서 통계를 다시 계산해 채운다
   (이미지 통계는 생성기와 같은 규칙: 10프레임마다 1장, 컨테이너 ffmpeg 로 디코드. pick/place 는 FK 로 복원, rebuilt=true 표시)
3. tasks.jsonl · info.json 을 episodes.jsonl 전체로 다시 쓴다
끝나면 "다음 --start 번호" 를 출력한다. 생성기(gen_isaac_demos.py)도 마지막에 write_info() 를 같이 쓴다.
"""
import sys, os, json, glob, subprocess, argparse
import numpy as np

HF = '/home/kim/physical_ai_tools/docker/huggingface/lerobot/dlcodnjs'
FPS = 30; W, H = 640, 480; G_TH = 0.459
TASK = 'Pick up the blue cube and place it in the place zone.'
NAMES = ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6', 'gripper']

def cpath(p): return p.replace('/home/kim/physical_ai_tools/docker/huggingface', '/root/.cache/huggingface')

def decode_every10(path):
    """컨테이너 ffmpeg 로 10프레임마다 1장 rgb24 → (k,H,W,3). 실패하면 None (= mp4 깨짐)."""
    cmd = ['docker', 'exec', 'physical_ai_server', 'ffmpeg', '-loglevel', 'error', '-i', cpath(path), '-vf', 'select=not(mod(n\\,10))', '-vsync', 'vfr',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or len(r.stdout) == 0 or len(r.stdout) % (W * H * 3): return None
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3)

def nframes(path):
    r = subprocess.run(['docker', 'exec', 'physical_ai_server', 'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                        '-show_entries', 'stream=nb_frames', '-of', 'csv=p=0', cpath(path)], capture_output=True, text=True)   # 헤더만 읽음 (빠름)
    try: return int(r.stdout.strip())
    except ValueError: return -1

def stat(arr, n):
    arr = np.asarray(arr, float)
    return dict(min=arr.min(0).tolist() if arr.ndim > 1 else [arr.min()], max=arr.max(0).tolist() if arr.ndim > 1 else [arr.max()],
                mean=arr.mean(0).tolist() if arr.ndim > 1 else [arr.mean()], std=arr.std(0).tolist() if arr.ndim > 1 else [arr.std()], count=[n])

def episode_meta(OUT, ep, kin):
    """parquet + mp4 → (episodes.jsonl 행, episodes_stats.jsonl 행). 파일이 깨졌으면 None."""
    import pandas as pd
    pq = f'{OUT}/data/chunk-000/episode_{ep:06d}.parquet'
    v1 = f'{OUT}/videos/chunk-000/observation.images.camera1/episode_{ep:06d}.mp4'
    v2 = f'{OUT}/videos/chunk-000/observation.images.camera2/episode_{ep:06d}.mp4'
    try: df = pd.read_parquet(pq)
    except Exception as e: print(f'ep{ep:03d} parquet 깨짐: {e}'); return None
    n = len(df)
    if n == 0 or not os.path.exists(v1) or not os.path.exists(v2): print(f'ep{ep:03d} mp4 없음'); return None
    if nframes(v1) != n or nframes(v2) != n: print(f'ep{ep:03d} mp4 프레임 수 불일치 (parquet {n})'); return None
    A = np.stack(df['action'].to_numpy()).astype(float); S = np.stack(df['observation.state'].to_numpy()).astype(float)
    st = {'observation.state': stat(S, n), 'action': stat(A, n)}
    for key, path in (('observation.images.camera1', v1), ('observation.images.camera2', v2)):
        X = decode_every10(path)
        if X is None or len(X) != (n + 9) // 10: print(f'ep{ep:03d} {key} 디코드 실패/프레임 부족'); return None
        ch = X.astype(float).reshape(-1, 3) / 255
        st[key] = dict(min=ch.min(0).reshape(3, 1, 1).tolist(), max=ch.max(0).reshape(3, 1, 1).tolist(), mean=ch.mean(0).reshape(3, 1, 1).tolist(), std=ch.std(0).reshape(3, 1, 1).tolist(), count=[len(X)])
    for key, arr in (('timestamp', np.arange(n) / FPS), ('frame_index', np.arange(n)), ('episode_index', np.full(n, ep)), ('index', np.arange(n)), ('task_index', np.zeros(n))):
        st[key] = stat(arr, n)
    # 그리퍼 열로 닫힘/열림 시점, FK 로 집는/놓는 위치 복원 (생성기 값과 완전히 같진 않다 — 표시용)
    closed = A[:, 6] < G_TH; idx = np.flatnonzero(closed)
    tc = int(idx[0]) if len(idx) else None; to = int(idx[-1] + 1) if len(idx) and idx[-1] + 1 < n else None
    pick = kin.fk(A[tc, :6])[:3, 3].tolist() if (kin is not None and tc is not None) else None
    place = kin.fk(A[to, :6])[:3, 3].tolist() if (kin is not None and to is not None) else None
    meta = dict(episode_index=ep, tasks=[TASK], length=n, pick=pick, place=place, cube_yaw_deg=None, t_close=tc, t_open=to, rebuilt=True)
    return meta, dict(episode_index=ep, stats=st)

def write_info(OUT, isaac_gen=None):
    """episodes.jsonl 전체로 tasks.jsonl · info.json 을 다시 쓴다 (생성기 마지막에도 호출)."""
    eps = sorted((json.loads(l) for l in open(f'{OUT}/meta/episodes.jsonl') if l.strip()), key=lambda d: d['episode_index'])
    with open(f'{OUT}/meta/tasks.jsonl', 'w') as f: f.write(json.dumps(dict(task=TASK, task_index=0)) + '\n')
    old = json.load(open(f'{OUT}/meta/info.json')) if os.path.exists(f'{OUT}/meta/info.json') else None
    info = json.load(open(f'{HF}/m1013_act_pick_and_place_v6_joint/meta/info.json'))
    info.update(robot_type='m1013_isaac', total_episodes=len(eps), total_frames=int(sum(e['length'] for e in eps)), total_videos=2 * len(eps), total_tasks=1,
                splits={'train': f'0:{len(eps)}'})
    for key in ('observation.state', 'action'): info['features'][key]['names'] = NAMES
    if isaac_gen is not None: info['isaac_gen'] = isaac_gen
    elif old and 'isaac_gen' in old: info['isaac_gen'] = old['isaac_gen']
    json.dump(info, open(f'{OUT}/meta/info.json', 'w'), indent=1)
    return eps

def rebuild(OUT, remove_broken=True, jobs=8):
    sys.path.insert(0, '/home/kim/m1013')
    try:
        from m1013_kin import M1013Kin; kin = M1013Kin()
    except Exception: kin = None
    os.makedirs(f'{OUT}/meta', exist_ok=True)
    have = {}
    for fn in ('episodes.jsonl', 'episodes_stats.jsonl'):
        p = f'{OUT}/meta/{fn}'
        have[fn] = {d['episode_index']: d for d in (json.loads(l) for l in open(p) if l.strip())} if os.path.exists(p) else {}
    files = sorted(glob.glob(f'{OUT}/data/chunk-000/episode_*.parquet'))
    eps = [int(os.path.basename(f)[8:14]) for f in files]
    print(f'{OUT}: parquet {len(eps)}개, meta 행 {len(have["episodes.jsonl"])}개')
    # 번호가 연속인지 — 빠진 번호가 있으면 생성기가 '전문가 실패 — 건너뜀' 한 것이라 정상
    todo = [ep for ep in eps if not (ep in have['episodes.jsonl'] and ep in have['episodes_stats.jsonl'])]
    from concurrent.futures import ThreadPoolExecutor            # ffmpeg 서브프로세스 대기가 대부분이라 스레드로 병렬
    with ThreadPoolExecutor(jobs) as ex: results = list(ex.map(lambda ep: (ep, episode_meta(OUT, ep, kin)), todo))
    for ep, r in results:
        if r is None:
            if remove_broken:
                for p in (f'{OUT}/data/chunk-000/episode_{ep:06d}.parquet', f'{OUT}/videos/chunk-000/observation.images.camera1/episode_{ep:06d}.mp4',
                          f'{OUT}/videos/chunk-000/observation.images.camera2/episode_{ep:06d}.mp4'):
                    if os.path.exists(p): os.remove(p); print('  삭제', os.path.basename(p))
            have['episodes.jsonl'].pop(ep, None); have['episodes_stats.jsonl'].pop(ep, None); continue
        have['episodes.jsonl'][ep] = r[0]; have['episodes_stats.jsonl'][ep] = r[1]
        print(f'ep{ep:03d} meta 복구 ({r[0]["length"]} 프레임)')
    # 파일이 없는데 meta 만 있는 행은 버린다
    keep = set(int(os.path.basename(f)[8:14]) for f in glob.glob(f'{OUT}/data/chunk-000/episode_*.parquet'))
    for fn in have:
        rows = [have[fn][k] for k in sorted(have[fn]) if k in keep]
        with open(f'{OUT}/meta/{fn}', 'w') as f:
            for d in rows: f.write(json.dumps(d) + '\n')
    eps_out = write_info(OUT)
    nxt = (max(keep) + 1) if keep else 0
    print(f'완료: {len(eps_out)} 에피소드, {sum(e["length"] for e in eps_out)} 프레임 → 다음 --start {nxt}')
    return nxt

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='m1013_isaac_v8'); ap.add_argument('--keep_broken', action='store_true'); ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    nxt = rebuild(f'{HF}/{a.out}', remove_broken=not a.keep_broken, jobs=a.jobs)
    open(f'{HF}/{a.out}/meta/next_start.txt', 'w').write(str(nxt))
