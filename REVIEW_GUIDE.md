# 재확인 가이드 — 2026-08-20 작업을 손으로 따라가기

> 목적: 다음 단계로 넘어가기 전에, 어제 무엇이 어떤 과정으로 만들어졌는지
> **직접 실행하면서** 확인한다. 순서대로 하면 약 1~2시간.
> 각 절의 ✅ 확인 포인트에 스스로 답할 수 있으면 통과.

---

## 0. 환경 지도 — 뭐가 어디서 도는가 (10분)

이 프로젝트는 **세 개의 파이썬 환경**을 쓴다. 이걸 헷갈리면 모든 게 헷갈린다.

| 환경 | 실행 방법 | 여기서 도는 것 |
|---|---|---|
| ① host 파이썬 | `python3 ...` | IK/스윕/변환/prep (numpy·pandas만 필요) |
| ② Isaac 파이썬 | `cd ~/isaacsim && ./python.sh ...` | 물리 재생 replay_isaac.py (Isaac 라이브러리 필요) |
| ③ Docker 컨테이너 `physical_ai_server` | `docker exec ...` | lerobot 학습/평가, 데이터셋 조립 (GPU+lerobot 설치돼 있음) |

컨테이너와 host 는 **마운트**로 연결된다. 직접 확인:

```bash
docker inspect physical_ai_server --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

- ✅ 확인 포인트: 컨테이너의 `/root/.cache/huggingface` 가 host 의 어디에 연결돼 있나?
  (답을 알면: host 에서 데이터셋 parquet 를 읽을 수 있는 이유, 그런데 **쓰기**는
  왜 컨테이너 안에서 해야 하는지도 설명할 수 있어야 함 → 힌트: `ls -la` 로 소유자 확인)

주요 경로:
```
/home/kim/m1013            ← 오늘의 작업 폴더 (= 이 저장소, github.com/dlcodnjs817/M1013)
/home/kim/tx90             ← 기존 TX90 프로젝트 (참조용)
/home/kim/isaacsim         ← Isaac Sim 5.1.0
/home/kim/doosan-robot2    ← 두산 공식 저장소 클론 (URDF/USD)
컨테이너 /root/train_m1013_act_v6   ← 학습 결과
컨테이너 /root/policy_rollouts      ← 정책 예측 npz
```

---

## 1. 로봇 모델 재료 (10분)

```bash
# USD (Isaac 용 완성품)와 URDF (기구학 정의) 가 어디 있나
ls ~/doosan-robot2/dsr_description2/usd/
ls ~/doosan-robot2/dsr_description2/urdf/ | grep m1013
```

- ✅ `m1013.urdf` 와 `m1013_isaac_sim.urdf` 두 개가 있다. **왜 우리는 표준 쪽만 쓰나?**
  (답: isaac_sim 판은 관절 리밋이 좁혀져 있고(J1 ±120°) 0.45m 받침대가 들어 있음.
  IK 를 그걸로 풀면 멀쩡한 자세가 "도달 불가" 판정됨)
- ✅ 링크 이름 규약이 TX90 과 같다 (`base_link/link_1~6`). 이 덕에 뭐가 쉬웠나?

---

## 2. 독립 IK — m1013_kin.py (15분)

```bash
cd ~/m1013
python3 m1013_kin.py        # 셀프테스트 (~3초)
```

기대 출력: `[task-like] n=1000: ok=1000 ... PASS`

읽어볼 코드 (순서대로):
1. `M1013Kin.fk_frames()` — URDF 의 조인트 원점들을 곱해가는 순기구학
2. `ik_dls()` — 자코비안 기반 감쇠최소제곱. **λ(감쇠)를 오차에 비례**시키는 한 줄이 특이점 안정성의 핵심
3. `solve()` — 시드 체인 규약: 접기(fold) → 브랜치 거부 → 섭동 재시도
4. `orient_corr()` — **손목 45° 보정**. 상수 회전 하나가 오늘의 반전이었음

- ✅ "브랜치 거부"가 왜 필요한가? (같은 손끝 위치에 팔꿈치 위/아래 등 여러 해가 있고,
  프레임마다 다른 가지를 고르면 관절이 널뜀)
- ✅ TX90 방식(MoveIt 서비스) 대신 이걸 만든 이유 세 가지는?

---

## 3. 배치 스윕 (15분, 실행 40초)

```bash
python3 sweep_m1013.py --out /tmp/sweep_check.json
```

- 1단계 54후보 로그가 흘러가고 → 2단계 5후보 → 최종 선정이 출력됨
- ✅ 채점 항목 세 개(min|q5|, j3여유, maxΔq)가 각각 뭘 지키는 건가?
- ✅ 스윕 점수 1위를 그대로 안 쓰고 별도 "기하검사"를 한 이유는?
  (힌트: 우리 IK 에 없는 검사가 하나 있다)
- 현재 확정값이 `convert_v6_m1013.py` 상단 `OFFSET = (+0.05, -0.15, +0.10)` 에 박혀 있음

---

## 4. 데이터셋 변환 (15분, 실행 6초)

```bash
python3 convert_v6_m1013.py        # 159ep 전체, ~6초
python3 knn_check_m1013.py         # 다봉성 검사
cat v6_staging/report.json | python3 -m json.tool | head -30
```

- ✅ 변환 규약 5개를 말할 수 있나? (7MA 평활 / 6Hz 앵커+보간 / state=action[t−1] /
  TCP 0.12 후퇴 / 손목 45° 보정)
- ✅ TCP 보정을 안 하면 무슨 일이 나나? (접근 틸트 44° × 그리퍼 12cm = 수평 84mm 오차)
- ✅ report.json 의 `max_dq_deg` 가 왜 중요한가? (실기에서 프레임 간 관절 점프 = 위험)

데이터셋 로드 확인 (컨테이너):
```bash
docker exec -i physical_ai_server python3 - <<'EOF'
from lerobot.datasets.lerobot_dataset import LeRobotDataset
ds = LeRobotDataset("dlcodnjs/m1013_act_pick_and_place_v6_joint")
print(ds.num_episodes, ds.num_frames, ds[0]["task"])
EOF
```

---

## 5. Isaac 물리 재생 (20분)

재생용 npz 가 뭘 담는지부터:
```bash
python3 prep_replay_ep.py --ep 0
python3 -c "import numpy as np; d=np.load('replay_ep000.npz'); print(list(d.keys())); print('큐브', d['cube_pick'], '핑거연장', d['finger_ext'])"
```

- ✅ 큐브를 왜 "그립 축 위의 큐브 중심 높이 지점"에 놓나? (테이블 상판 z=0.3746 과
  데이터의 파지 높이 관계 — 상판 ≠ 데이터의 '테이블 높이')

GUI 로 직접 보기 (모니터 필요):
```bash
cd ~/isaacsim && ./python.sh ~/m1013/replay_isaac.py --ep 0 --gui                      # GT
cd ~/isaacsim && ./python.sh ~/m1013/replay_isaac.py --ep 0 --gui --pred-npz ~/m1013/ep000_pred_m1013v6.npz   # 정책
```

- ✅ 파지 순간(~8초)에 핑거가 **수직으로 서 있는** 이유는? (손목 45° 보정)
- 영상 복습: `sim_out/grasp_fail_35mm.mp4` (실패) ↔ `sim_out/replay_35mm_success.mp4` (성공)
- ✅ 실패 영상의 "옆으로 쓸어내기"가 왜 일어났고, 실물 OMX 는 왜 괜찮았나? (폼 압축)

---

## 6. 학습·평가 결과물 (15분)

```bash
docker exec physical_ai_server tail -5 /root/train_m1013_act_v6.log
docker exec physical_ai_server ls /root/train_m1013_act_v6/checkpoints
docker exec physical_ai_server python3 /root/eval_m1013_v6.py 50      # 아무 ep 하나 평가 (~10초)
```

- ✅ open-loop 평가가 재는 것과 못 재는 것은? (재는 것: 정답 관측을 줬을 때의 모사 정확도.
  못 재는 것: 자기 예측 위에서 계속 실행할 때의 누적 오차 = closed-loop 에서 확인)
- ✅ TX90 대비 관절 오차가 절반이 된 원인 가설은?

---

## 7. 마지막 — 전체 흐름을 입으로 (10분)

아무것도 안 보고 아래 빈칸을 채울 수 있으면 재확인 끝:

> OMX 시연(v5, EE pose) → [ ① ] 오프셋 + TCP 후퇴 + [ ② ] 45° 보정을 넣어
> [ ③ ] 알고리즘으로 관절값을 풀고 → 6Hz 앵커를 30Hz 로 [ ④ ] →
> 검증 4종( [⑤] / [⑥] / [⑦] / [⑧] ) → lerobot 데이터셋 → ACT 100k →
> open-loop 평가 → Isaac 물리로 정책 실행 (놓기 오차 [ ⑨ ]mm)

(답: ①스윕으로 정한 배치 ②손목 ③적응감쇠 DLS+시드체인 ④선형보간
⑤IK 성공률 ⑥연속성 maxΔq ⑦FK 역검증 ⑧kNN 다봉성 ⑨7.8)

---

## 부록: 자주 쓰는 명령 모음

```bash
# 컨테이너 셸
docker exec -it physical_ai_server bash
# GPU 상태
nvidia-smi
# 전체 재변환 (OFFSET/TCP 바꿨을 때)
cd ~/m1013 && python3 convert_v6_m1013.py && python3 knn_check_m1013.py
# 데이터셋 재조립 (컨테이너 안에서 — 기존 것 rm 후)
docker exec physical_ai_server rm -rf /root/.cache/huggingface/lerobot/dlcodnjs/m1013_act_pick_and_place_v6_joint /root/v6_staging_m1013
docker cp ~/m1013/v6_staging physical_ai_server:/root/v6_staging_m1013
docker exec -i physical_ai_server python3 /dev/stdin --hf /root/.cache/huggingface/lerobot/dlcodnjs --staging /root/v6_staging_m1013 < ~/m1013/assemble_v6_m1013.py
# 학습 시작 (컨테이너, 백그라운드)
docker exec -d physical_ai_server bash -c 'cd /root/ros2_ws/src/physical_ai_tools/lerobot/src && nohup python3 -m lerobot.scripts.train --dataset.repo_id=dlcodnjs/m1013_act_pick_and_place_v6_joint --policy.type=act --policy.device=cuda --policy.push_to_hub=false --batch_size=8 --steps=100000 --save_freq=10000 --output_dir=/root/train_m1013_act_v6 --job_name=m1013_act_v6_joint > /root/train_m1013_act_v6.log 2>&1 &'
```
