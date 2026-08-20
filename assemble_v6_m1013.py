#!/usr/bin/env python3
"""v6_staging → 정식 LeRobot 데이터셋 dlcodnjs/m1013_act_pick_and_place_v6_joint 조립.

TX90 assemble_v6.py 이식 (host 에서 실행, HF 캐시는 컨테이너 마운트와 공유):
- data: staging parquet 복사
- meta: v5 복사 + episodes_stats.jsonl 의 state/action 통계 재계산
- tasks.jsonl: VLA 대비 자연어 지시문으로 교체 (두 task_index 모두 같은 과제 —
  pick zone 의 파란 큐브를 place zone 에 놓기. 2026-08-20 사용자 확인)
- videos: v5 의 상대 심볼릭 링크 복제 (원본 v4 영상 재사용)
"""
import glob
import json
import os
import shutil
import sys

import numpy as np
import pandas as pd

# HF 캐시는 컨테이너가 root 로 쓰므로 조립은 컨테이너 안에서 실행:
#   docker cp 또는 workspace 마운트로 staging 반입 후
#   docker exec -i physical_ai_server python3 - --hf /root/.cache/huggingface/lerobot/dlcodnjs --staging /workspace/v6_staging_m1013 < assemble_v6_m1013.py
import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument("--hf", default="/home/kim/physical_ai_tools/docker/huggingface/lerobot/dlcodnjs")
_ap.add_argument("--staging", default="/home/kim/tx90/m1013/v6_staging")
_a = _ap.parse_args()
HF = _a.hf
V5 = f"{HF}/tx90_act_pick_and_place_v5_ee"
V6S = _a.staging
OUT = f"{HF}/m1013_act_pick_and_place_v6_joint"

TASK_TEXT = "Pick up the blue cube and place it in the place zone."

if os.path.exists(OUT):
    print("이미 존재 — 중단 (기존 것 보호). 재조립하려면 먼저 rm -rf 할 것:", OUT)
    sys.exit(1)

os.makedirs(f"{OUT}/data/chunk-000")
os.makedirs(f"{OUT}/meta")

info = json.load(open(f"{V5}/meta/info.json"))
N = info["total_episodes"]

# 1) data
for ep in range(N):
    shutil.copy(f"{V6S}/data/chunk-000/episode_{ep:06d}.parquet",
                f"{OUT}/data/chunk-000/episode_{ep:06d}.parquet")

# 2) meta — info/episodes 복사, tasks 는 자연어로 교체, stats 재계산
for f in ("info.json", "episodes.jsonl", "transform.npy"):
    src = f"{V5}/meta/{f}"
    if os.path.exists(src):
        shutil.copy(src, f"{OUT}/meta/{f}")

with open(f"{V5}/meta/tasks.jsonl") as fin, open(f"{OUT}/meta/tasks.jsonl", "w") as fout:
    for line in fin:
        d = json.loads(line)
        d["task"] = TASK_TEXT
        fout.write(json.dumps(d) + "\n")

# episodes.jsonl 의 tasks 필드도 자연어로 교체
with open(f"{V5}/meta/episodes.jsonl") as fin, open(f"{OUT}/meta/episodes.jsonl", "w") as fout:
    for line in fin:
        d = json.loads(line)
        if "tasks" in d:
            d["tasks"] = [TASK_TEXT]
        fout.write(json.dumps(d) + "\n")

with open(f"{V5}/meta/episodes_stats.jsonl") as fin, \
        open(f"{OUT}/meta/episodes_stats.jsonl", "w") as fout:
    for line in fin:
        d = json.loads(line)
        ep = d["episode_index"]
        df = pd.read_parquet(f"{OUT}/data/chunk-000/episode_{ep:06d}.parquet")
        for key in ("observation.state", "action"):
            arr = np.stack(df[key]).astype(np.float64)
            d["stats"][key] = {
                "min": arr.min(0).tolist(),
                "max": arr.max(0).tolist(),
                "mean": arr.mean(0).tolist(),
                "std": arr.std(0).tolist(),
                "count": [int(len(arr))],
            }
        fout.write(json.dumps(d) + "\n")

# 3) videos — v5 링크 구조 복제 (상대 링크라 host/컨테이너 양쪽에서 유효)
for cam_dir in sorted(os.listdir(f"{V5}/videos/chunk-000")):
    src_dir = f"{V5}/videos/chunk-000/{cam_dir}"
    dst_dir = f"{OUT}/videos/chunk-000/{cam_dir}"
    os.makedirs(dst_dir)
    for name in sorted(os.listdir(src_dir)):
        sp = os.path.join(src_dir, name)
        if os.path.islink(sp):
            os.symlink(os.readlink(sp), os.path.join(dst_dir, name))
        else:
            os.symlink(os.path.relpath(sp, dst_dir), os.path.join(dst_dir, name))

# 4) 변환 규약 기록
rep = json.load(open(f"{V6S}/report.json"))
meta = {
    "source": "dlcodnjs/tx90_act_pick_and_place_v5_ee",
    "date": "2026-08-20",
    "robot": "Doosan M1013 (표준 m1013.urdf, EE=link_6, 접근축 +Z)",
    "ik": "m1013_kin.py 독립 DLS IK (ROS/MoveIt 불사용)",
    "offset_m": rep["summary"]["offset_m"],
    "offset_rationale": "54후보 스윕 + 기하 자기충돌 검사 (sweep_result.json)",
    "anchor_hz": 6, "anchor_k": rep["summary"]["anchor_k"],
    "smooth_window": rep["summary"]["smooth_window"],
    "state_def": rep["summary"]["state_def"],
    "task_text": TASK_TEXT,
    "validation": {
        "episodes_ok": f"{rep['summary']['n_ok']}/{rep['summary']['n_total']}",
        "max_frame_jump_deg": rep["summary"]["max_dq_deg"],
        "fk_pos_err_max_mm": rep["summary"]["fk_pos_err_max_mm"],
        "fk_ang_err_max_deg": rep["summary"]["fk_ang_err_max_deg"],
        "min_q5_deg": rep["summary"]["min_q5_deg"],
    },
}
json.dump(meta, open(f"{OUT}/meta/conversion_meta.json", "w"), indent=1, ensure_ascii=False)
shutil.copy(f"{V6S}/report.json", f"{OUT}/meta/conversion_report.json")

mp4 = sorted(glob.glob(f"{OUT}/videos/chunk-000/*/episode_000000.mp4"))[0]
print("link ok:", os.path.exists(mp4), mp4)
print("조립 완료:", OUT)
