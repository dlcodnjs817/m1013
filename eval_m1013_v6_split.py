"""검증셋 분리 학습 모델의 held-out 평가 (논문 6절용).

  docker exec -i physical_ai_server python3 - [--ckpt DIR] [--split JSON] [--n-train 20] < eval_m1013_v6_split.py

held-out 20 ep(미학습) 과 학습 ep 중 같은 수를 뽑아 open-loop 관절오차·그리퍼 일치·연속성을 같은 잣대로 잰다.
결과: /root/policy_rollouts/split_eval.json + ep별 pred npz (Isaac 재생용)
"""
import argparse, json, time
import numpy as np, torch
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies.act.modeling_act import ACTPolicy

ap = argparse.ArgumentParser()
ap.add_argument("--ckpt", default="/root/train_m1013_act_v6_split/checkpoints/last/pretrained_model")
ap.add_argument("--split", default="/root/split_v6_seed0.json")
ap.add_argument("--n-train", type=int, default=20)
ap.add_argument("--tag", default="split")
a = ap.parse_args()

REPO = "dlcodnjs/m1013_act_pick_and_place_v6_joint"
GRIP_TH = 0.459
sp = json.load(open(a.split))
held = sp["held_out"]
train_ref = [int(v) for v in np.random.default_rng(1).choice(sp["train"], a.n_train, replace=False)]
train_ref.sort()

policy = ACTPolicy.from_pretrained(a.ckpt).to("cuda").eval()
ds = LeRobotDataset(REPO)
img_keys = [k for k in ds.meta.features if k.startswith("observation.images")]
print(f"[정책] {a.ckpt}\n[held-out] {held}\n[train-ref] {train_ref}")

def run_ep(ep):
    policy.reset()
    i0 = ds.episode_data_index["from"][ep].item(); i1 = ds.episode_data_index["to"][ep].item()
    preds, gts = [], []
    with torch.inference_mode():
        for idx in range(i0, i1):
            it = ds[idx]
            b = {"observation.state": it["observation.state"].unsqueeze(0).cuda()}
            for k in img_keys: b[k] = it[k].unsqueeze(0).cuda()
            preds.append(policy.select_action(b).squeeze(0).cpu().numpy()); gts.append(it["action"].numpy())
    pred, gt = np.array(preds), np.array(gts)
    jerr = np.degrees(np.abs(pred[:, :6] - gt[:, :6]))
    step = np.degrees(np.abs(np.diff(pred[:, :6], axis=0)))
    np.savez(f"/root/policy_rollouts/ep{ep:03d}_pred_m1013v6_{a.tag}.npz", pred=pred, gt=gt)
    return dict(ep=ep, frames=len(pred), mean=float(jerr.mean()), median=float(np.median(jerr)),
                max=float(jerr.max()), per_joint=jerr.mean(0).round(3).tolist(),
                grip_ok=float(((pred[:, 6] < GRIP_TH) == (gt[:, 6] < GRIP_TH)).mean() * 100),
                max_step=float(step.max()))

out = {"ckpt": a.ckpt, "held_out": [], "train_ref": []}
for name, eps in (("held_out", held), ("train_ref", train_ref)):
    t0 = time.time()
    for ep in eps:
        r = run_ep(ep); out[name].append(r)
        print(f"  {name:9s} ep{ep:3d}  mean {r['mean']:.2f}°  med {r['median']:.2f}°  max {r['max']:.2f}°  grip {r['grip_ok']:.1f}%  step {r['max_step']:.2f}°")
    print(f"  ({time.time()-t0:.0f}s)")

def agg(rs, k): v = np.array([r[k] for r in rs]); return f"{v.mean():.2f} ± {v.std():.2f}"
print("\n==== 요약 (ep 평균 ± std) ====")
print(f"{'':10s} {'관절오차 mean':>14s} {'median':>8s} {'max':>8s} {'그리퍼일치%':>10s} {'출력 maxΔ°':>10s}")
for name in ("held_out", "train_ref"):
    rs = out[name]
    print(f"{name:10s} {agg(rs,'mean'):>14s} {agg(rs,'median'):>8s} {agg(rs,'max'):>8s} {agg(rs,'grip_ok'):>10s} {agg(rs,'max_step'):>10s}")
json.dump(out, open(f"/root/policy_rollouts/split_eval_{a.tag}.json", "w"), indent=1)
print("저장: /root/policy_rollouts/split_eval_%s.json" % a.tag)
