#!/bin/bash
# Isaac 시연 v8 파이프라인 — 생성 완료 대기 → ACT 학습(컨테이너) → 닫힌 루프 평가. 2026-09-11.
#   nohup bash run_v8_pipeline.sh <생성기 PID> > sim_out/v8_pipeline.log 2>&1 &
set -u
GEN_PID=${1:-0}; DS=m1013_isaac_v8; TRAIN=/root/train_m1013_act_isaac_v8
log(){ echo "[$(date '+%m-%d %H:%M')] $*"; }

if [ "$GEN_PID" != "0" ]; then
  log "생성기(PID $GEN_PID) 종료 대기"
  while kill -0 "$GEN_PID" 2>/dev/null; do sleep 60; done
fi
N=$(python3 -c "import json;print(json.load(open('/home/kim/physical_ai_tools/docker/huggingface/lerobot/dlcodnjs/$DS/meta/info.json'))['total_episodes'])")
F=$(python3 -c "import json;print(json.load(open('/home/kim/physical_ai_tools/docker/huggingface/lerobot/dlcodnjs/$DS/meta/info.json'))['total_frames'])")
log "데이터셋 $DS: $N 에피소드, $F 프레임"
[ "$N" -lt 100 ] && { log "에피소드가 너무 적음 — 중단"; exit 1; }

log "ACT 학습 시작 → $TRAIN (100k 스텝, batch 8 — v6 와 동일 설정)"
docker exec physical_ai_server bash -c "cd /root/ros2_ws/src/physical_ai_tools/lerobot/src && python3 -m lerobot.scripts.train \
  --dataset.repo_id=dlcodnjs/$DS --policy.type=act --policy.device=cuda --policy.push_to_hub=false \
  --batch_size=8 --steps=100000 --log_freq=200 --save_freq=10000 --output_dir=$TRAIN --job_name=m1013_act_isaac_v8 > $TRAIN.log 2>&1"
docker exec physical_ai_server bash -c "grep -a 'step:100K\|Error\|Traceback' $TRAIN.log | tail -2"
docker exec physical_ai_server test -d $TRAIN/checkpoints/last/pretrained_model || { log "학습 실패 — $TRAIN.log 확인"; exit 1; }
log "학습 완료"

log "닫힌 루프 평가 30 에피소드 (v6 분포 위치) + 30 에피소드 (1.5배 영역)"
cd /home/kim/isaacsim
./python.sh /home/kim/m1013/eval_isaac_closedloop.py --ckpt $TRAIN/checkpoints/last/pretrained_model --n 30 --tag eval_isaac_v8 > /home/kim/m1013/sim_out/eval_isaac_v8.log 2>&1
grep -a "요약" /home/kim/m1013/sim_out/eval_isaac_v8.log
./python.sh /home/kim/m1013/eval_isaac_closedloop.py --ckpt $TRAIN/checkpoints/last/pretrained_model --n 30 --ws_scale 1.5 --tag eval_isaac_v8_ws15 > /home/kim/m1013/sim_out/eval_isaac_v8_ws15.log 2>&1
grep -a "요약" /home/kim/m1013/sim_out/eval_isaac_v8_ws15.log
./python.sh /home/kim/m1013/eval_isaac_closedloop.py --ckpt /root/train_m1013_act_v6_tcp0725/checkpoints/last/pretrained_model --n 30 --tag eval_v6_baseline > /home/kim/m1013/sim_out/eval_v6_baseline.log 2>&1
grep -a "요약" /home/kim/m1013/sim_out/eval_v6_baseline.log
log "파이프라인 끝"
