#!/usr/bin/env python3
"""sim_out/frames_<label>/ PNG 프레임을 mp4 로 조립 (Isaac python 의 cv2 사용).

  cd /home/kim/isaacsim && ./python.sh /home/kim/m1013/frames_to_mp4.py <label> [fps]

기본 fps=15 (30Hz 궤적을 2프레임마다 캡처 → 실시간 속도).
출력: sim_out/replay_<label>.mp4
"""

import glob
import os
import sys

import cv2

label = sys.argv[1]
fps = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
d = f"/home/kim/m1013/sim_out/frames_{label}"
files = sorted(glob.glob(os.path.join(d, "*.png")))
assert files, f"프레임 없음: {d}"
h, w = cv2.imread(files[0]).shape[:2]
out = f"/home/kim/m1013/sim_out/replay_{label}.mp4"
vw = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
for f in files:
    vw.write(cv2.imread(f))
vw.release()
print("SAVED:", out, f"({len(files)}프레임, {fps}fps, {w}x{h})")
