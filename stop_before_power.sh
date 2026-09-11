#!/bin/bash
# 전원 차단 전 정리 (2026-09-11 18:00 콘센트 차단 확정). 17:45 에 자동 실행되도록 걸어 둠.
#   1) split 학습: 70k 체크포인트가 저장될 때까지(최대 17:52) 기다렸다가 종료 → 월요일 --resume
#   2) v8 파이프라인 bash 종료 (생성기 죽은 뒤 학습을 시작하지 않도록) → 생성기 종료 → meta 복구 (rebuild_v8_meta.py)
#   3) sync
# 월요일: bash /home/kim/m1013/resume_all.sh
log(){ echo "[$(date '+%m-%d %H:%M:%S')] $*"; }
log "전원 차단 전 정리 시작"

# ---- 1) split 학습 ----
while ! docker exec physical_ai_server test -d /root/train_m1013_act_v6_split/checkpoints/070000/training_state; do
  [ "$(date +%H%M)" -ge 1752 ] && { log "70k 체크포인트 못 기다림 — 60k 에서 재개하게 됨"; break; }
  sleep 10
done
LAST=$(docker exec physical_ai_server readlink /root/train_m1013_act_v6_split/checkpoints/last)
docker exec physical_ai_server pkill -f 'job_name=m1013_act_v6_split'; sleep 5
docker exec physical_ai_server pkill -9 -f 'job_name=m1013_act_v6_split' 2>/dev/null
log "split 학습 종료 (마지막 체크포인트 $LAST)"

# ---- 2) v8 파이프라인 + 생성기 ----
pkill -f run_v8_pipeline.sh && log "v8 파이프라인 bash 종료"
GEN=$(pgrep -f 'gen_isaac_demos.py --n 1000' | head -1)
if [ -n "$GEN" ]; then
  pkill -TERM -f 'gen_isaac_demos.py --n 1000'
  for i in $(seq 1 12); do pgrep -f 'gen_isaac_demos.py --n 1000' >/dev/null || break; sleep 5; done
  pkill -9 -f 'gen_isaac_demos.py --n 1000' 2>/dev/null; pkill -9 -f 'gen_isaac_demos.py' 2>/dev/null
  log "생성기 종료"
fi
sleep 3
cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/rebuild_v8_meta.py --out m1013_isaac_v8 2>&1 | grep -v '^\[' | tail -8
sync
log "정리 끝 — 이제 전원을 꺼도 됨. 월요일: bash /home/kim/m1013/resume_all.sh"
