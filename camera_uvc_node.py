#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U20CAM-720P → LeRobot 규격(640×480) 영상 토픽 발행.

physical_ai_server 의 기록기가 구독하는 토픽 형식(compressed)에 맞춘다.

    1280×720 캡처  →  960×720 중앙크롭  →  640×480 리사이즈
    (HFOV 102°)       (HFOV 85.6°)         4:3, v6 와 동일 해상도

왜 이 파이프라인인가 — 카메라 센서는 16:9(1280×720)인데 데이터셋은 4:3(640×480)이다.
카메라가 자체적으로 내주는 640×480 모드는 **가로를 절반만 쓰는 단순 크롭**이라 HFOV 가
63.4° 로 줄고, 그러면 파지 직전 큐브가 화면 밖으로 나간다(wristcam_check.py 로 확인,
8 에피소드 중 2개 이탈). 세로 720 을 다 쓰는 960 크롭이 4:3 에서 얻을 수 있는 최대 화각이다.

    python3 camera_uvc_node.py --dev 0 --name camera1     # 손목캠
    python3 camera_uvc_node.py --dev 2 --name camera2     # 정면캠
    python3 camera_uvc_node.py --dev 0 --preview          # ROS2 없이 크롭만 확인

2026-09-09 작성.
"""
from __future__ import annotations

import argparse

import cv2
import numpy as np

SRC_W, SRC_H = 1280, 720        # 센서 네이티브
CROP_W = 960                    # 4:3 중앙크롭 (세로는 720 전부 사용)
OUT_W, OUT_H = 640, 480         # 데이터셋 규격
FPS = 30


def open_cam(dev: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(dev)
    if not cap.isOpened():
        raise SystemExit(f"카메라 {dev} 를 열 수 없다. v4l2-ctl --list-devices 로 확인할 것")
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, SRC_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SRC_H)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if (w, h) != (SRC_W, SRC_H):
        print(f"⚠️ 요청 {SRC_W}×{SRC_H} 인데 실제 {w}×{h} 다. "
              f"MJPG 모드가 아니거나 카메라가 이 해상도를 지원하지 않는다 — 화각이 달라진다.")
    return cap


def crop_resize(frame: np.ndarray) -> np.ndarray:
    """1280×720 → 960×720 중앙크롭 → 640×480."""
    h, w = frame.shape[:2]
    x0 = max(0, (w - CROP_W) // 2)
    return cv2.resize(frame[:, x0:x0 + CROP_W], (OUT_W, OUT_H), interpolation=cv2.INTER_AREA)


def run_preview(dev: int) -> None:
    cap = open_cam(dev)
    print("q 로 종료. 좌: 원본 축소 / 우: 크롭 결과")
    while True:
        ok, f = cap.read()
        if not ok:
            print("프레임 수신 실패"); break
        out = crop_resize(f)
        left = cv2.resize(f, (OUT_W, int(OUT_W * f.shape[0] / f.shape[1])))
        pad = np.zeros((OUT_H, OUT_W, 3), np.uint8)
        pad[:left.shape[0]] = left
        cv2.imshow("src (16:9) | cropped 640x480 (HFOV 85.6)", np.hstack([pad, out]))
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release(); cv2.destroyAllWindows()


def run_node(dev: int, name: str) -> None:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import CompressedImage

    class Cam(Node):
        def __init__(self):
            super().__init__(f"uvc_{name}")
            self.cap = open_cam(dev)
            self.pub = self.create_publisher(CompressedImage, f"/{name}/image_raw/compressed", 10)
            self.create_timer(1.0 / FPS, self.tick)
            self.n_drop = 0
            self.get_logger().info(
                f"/dev/video{dev} → /{name}/image_raw/compressed  "
                f"{SRC_W}×{SRC_H} → 크롭 {CROP_W}×{SRC_H} → {OUT_W}×{OUT_H} (HFOV 85.6°)")

        def tick(self):
            ok, f = self.cap.read()
            if not ok:
                self.n_drop += 1
                if self.n_drop % 30 == 1:
                    self.get_logger().warn(f"프레임 유실 {self.n_drop} 회")
                return
            ok2, buf = cv2.imencode(".jpg", crop_resize(f), [cv2.IMWRITE_JPEG_QUALITY, 92])
            if not ok2:
                return
            m = CompressedImage()
            m.header.stamp = self.get_clock().now().to_msg()
            m.header.frame_id = name
            m.format = "jpeg"
            m.data = buf.tobytes()
            self.pub.publish(m)

    rclpy.init()
    node = Cam()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cap.release(); node.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", type=int, default=0)
    ap.add_argument("--name", default="camera1", choices=["camera1", "camera2"])
    ap.add_argument("--preview", action="store_true", help="ROS2 없이 크롭 결과만 확인")
    a = ap.parse_args()
    run_preview(a.dev) if a.preview else run_node(a.dev, a.name)
