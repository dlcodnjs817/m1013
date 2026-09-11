#!/usr/bin/env python3
"""U20CAM-720P 체커보드 캘리브레이션 → cam_calib_<name>.npz (K, D, 1280×720 기준).

  python3 cam_calibrate.py --dev /dev/v4l/by-id/...  --name camera1 --cols 9 --rows 6 --square 0.025

매뉴얼 스펙 TV distortion < -17% (배럴). Isaac 렌더는 핀홀이라 실물 프레임을 언디스토션해야 sim↔real 화면이 맞는다.
스페이스로 프레임 채택(20장 이상, 화면 구석까지 골고루), q 로 종료·저장. RMS 재투영오차 0.5 px 이하면 양호.
"""
import argparse, cv2, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument('--dev', default='0'); ap.add_argument('--name', default='camera1')
ap.add_argument('--cols', type=int, default=9); ap.add_argument('--rows', type=int, default=6); ap.add_argument('--square', type=float, default=0.025)
a = ap.parse_args(); dev = int(a.dev) if a.dev.isdigit() else a.dev
cap = cv2.VideoCapture(dev); cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG')); cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
objp = np.zeros((a.rows * a.cols, 3), np.float32); objp[:, :2] = np.mgrid[0:a.cols, 0:a.rows].T.reshape(-1, 2) * a.square
objs, imgs = [], []
print('스페이스 = 채택, q = 종료·저장')
while True:
    ok, f = cap.read()
    if not ok: break
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY); found, c = cv2.findChessboardCorners(g, (a.cols, a.rows), cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE)
    show = f.copy()
    if found: cv2.drawChessboardCorners(show, (a.cols, a.rows), c, found)
    cv2.putText(show, f'{len(imgs)} 장', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2); cv2.imshow('calib', show)
    k = cv2.waitKey(1) & 0xFF
    if k == ord(' ') and found:
        c = cv2.cornerSubPix(g, c, (11, 11), (-1, -1), (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)); objs.append(objp); imgs.append(c); print('채택', len(imgs))
    elif k == ord('q'): break
cap.release(); cv2.destroyAllWindows()
if len(imgs) < 10: raise SystemExit('프레임이 %d 장뿐 — 10장 이상 필요' % len(imgs))
rms, K, D, _, _ = cv2.calibrateCamera(objs, imgs, (1280, 720), None, None)
print('RMS %.3f px\nK=\n%s\nD=%s' % (rms, np.round(K, 2), np.round(D.ravel(), 4)))
fx = K[0, 0]; print('추정 HFOV(1280) %.1f°  · 960 크롭 HFOV %.1f°' % (2 * np.degrees(np.arctan(640 / fx)), 2 * np.degrees(np.arctan(480 / fx))))
np.savez(f'cam_calib_{a.name}.npz', K=K, D=D, rms=rms, size=(1280, 720)); print('저장 cam_calib_%s.npz' % a.name)
