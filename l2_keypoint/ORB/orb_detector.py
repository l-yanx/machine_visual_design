"""ORB 角点检测与可视化。"""

from __future__ import annotations

import cv2
import numpy as np


def detect_orb_features(
    gray: np.ndarray,
    nfeatures: int = 1200,
    scale_factor: float = 1.2,
    nlevels: int = 8,
    fast_threshold: int = 20,
) -> tuple[np.ndarray, np.ndarray]:
    """
    返回:
        pts_xy: Nx2 float32 关键点坐标
        desc: Nx32 uint8 ORB 描述子（可能为空）
    """
    if gray.ndim != 2:
        raise ValueError("gray must be single-channel image")

    orb = cv2.ORB_create(
        nfeatures=nfeatures,
        scaleFactor=scale_factor,
        nlevels=nlevels,
        fastThreshold=fast_threshold,
    )
    keypoints, desc = orb.detectAndCompute(gray, None)
    if keypoints is None or len(keypoints) == 0:
        return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 32), dtype=np.uint8)

    pts = np.array([kp.pt for kp in keypoints], dtype=np.float32)
    if desc is None:
        desc = np.zeros((0, 32), dtype=np.uint8)
    return pts, desc


def draw_keypoints(
    image_bgr: np.ndarray,
    pts_xy: np.ndarray,
    radius: int = 3,
    color: tuple[int, int, int] = (0, 255, 255),
) -> np.ndarray:
    """在图上绘制关键点。"""
    out = image_bgr.copy()
    for x, y in pts_xy:
        p = (int(round(float(x))), int(round(float(y))))
        cv2.circle(out, p, radius, color, 1, lineType=cv2.LINE_AA)
    return out
