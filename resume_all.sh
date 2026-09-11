#!/bin/bash
# 전원 차단 후 재개 — 월요일(2026-09-14) 출근해서 한 줄:  bash /home/kim/m1013/resume_all.sh
#   ① v8 시연 meta 복구(깨진 마지막 에피소드 삭제) → 1000개 안 됐으면 --start N 으로 이어 생성
#   ② split 학습(139/20): 마지막 10k 체크포인트부터 --resume
#   ③ v8 파이프라인(생성 대기 → 학습(재개 지원) → 평가 3종) 재시작
# 진행 확인: tail -f /home/kim/m1013/sim_out/v8_pipeline.log ,  docker exec physical_ai_server tail -2 /root/train_m1013_act_v6_split.log
set -u
log(){ echo "[$(date '+%m-%d %H:%M')] $*"; }
DS=m1013_isaac_v8; HFD=/home/kim/physical_ai_tools/docker/huggingface/lerobot/dlcodnjs/$DS
SPLIT=/root/train_m1013_act_v6_split

# ---- 컨테이너 ----
docker start physical_ai_server >/dev/null 2>&1
for i in $(seq 1 30); do docker exec physical_ai_server true 2>/dev/null && break; sleep 2; done
docker exec physical_ai_server true || { log "컨테이너가 안 뜸 — docker ps 확인"; exit 1; }
nvidia-smi --query-gpu=name,memory.used --format=csv,noheader || { log "GPU 안 보임"; exit 1; }

# ---- ① v8 meta 복구 ----
log "v8 meta 복구/검증"
cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/rebuild_v8_meta.py --out $DS 2>&1 | grep -v '^\[' | tail -6
N=$(cat $HFD/meta/next_start.txt)

# ---- ② split 학습 재개 ----
if docker exec physical_ai_server test -d $SPLIT/checkpoints/100000/pretrained_model; then
  log "split 학습은 이미 100k 완료"
elif docker exec physical_ai_server test -f $SPLIT/checkpoints/last/pretrained_model/train_config.json; then
  log "split 학습 재개 ($(docker exec physical_ai_server readlink $SPLIT/checkpoints/last) → 100k)"
  docker exec -d physical_ai_server bash -c "cd /root/ros2_ws/src/physical_ai_tools/lerobot/src && python3 -m lerobot.scripts.train \
    --resume=true --config_path=$SPLIT/checkpoints/last/pretrained_model/train_config.json >> $SPLIT.log 2>&1"
else
  log "split 체크포인트 없음 — 처음부터 다시 돌려야 함 (m1013/split_v6_seed0.json 참고)"
fi

# ---- ③ v8 생성 이어하기 + 파이프라인 ----
GEN_PID=0
if [ "$N" -lt 1000 ]; then
  log "v8 생성 이어하기: --start $N --n $((1000 - N)) (seed 1)"
  cd /home/kim/isaacsim && nohup ./python.sh /home/kim/m1013/gen_isaac_demos.py --n $((1000 - N)) --start $N --out $DS --seed 1 >> /home/kim/m1013/sim_out/gen_v8.log 2>&1 &
  GEN_PID=$!
else
  log "v8 생성 완료 상태 ($N 에피소드)"
fi
cd /home/kim/m1013 && nohup bash run_v8_pipeline.sh $GEN_PID >> sim_out/v8_pipeline.log 2>&1 &
log "v8 파이프라인 재시작 (생성기 PID $GEN_PID). 로그: sim_out/v8_pipeline.log"
