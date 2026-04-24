"""SIFT 关键点检测与可视化。"""

from __future__ import annotations

import cv2
import numpy as np


def detect_sift_features(
    gray: np.ndarray,
    nfeatures: int = 1200,
    contrast_threshold: float = 0.04,
    edge_threshold: float = 10.0,
    sigma: float = 1.6,
) -> tuple[np.ndarray, np.ndarray]:
    """
    返回:
        pts_xy: Nx2 float32 关键点坐标
        desc: Nx128 float32 SIFT 描述子（可能为空）
    """
    if gray.ndim != 2:
        raise ValueError("gray must be single-channel image")

    sift = cv2.SIFT_create(
        nfeatures=nfeatures,
        contrastThreshold=contrast_threshold,
        edgeThreshold=edge_threshold,
        sigma=sigma,
    )
    keypoints, desc = sift.detectAndCompute(gray, None)
    if keypoints is None or len(keypoints) == 0:
        return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 128), dtype=np.float32)

    pts = np.array([kp.pt for kp in keypoints], dtype=np.float32)
    if desc is None:
        desc = np.zeros((0, 128), dtype=np.float32)
    return pts, desc.astype(np.float32)


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
