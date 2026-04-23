"""Harris 角点检测：输出角点坐标与带角点标注的图像。"""

from __future__ import annotations

import cv2
import numpy as np


def detect_harris_corners(
    gray: np.ndarray,
    max_corners: int = 1200,
    quality_level: float = 0.005,
    min_distance: float = 6.0,
    block_size: int = 3,
    k: float = 0.04,
) -> np.ndarray:
    """使用 goodFeaturesToTrack(Harris) + cornerSubPix，返回 Nx2 float32。"""
    if gray.ndim != 2:
        raise ValueError("gray must be single-channel image")
    corners = cv2.goodFeaturesToTrack(
        gray,
        maxCorners=max_corners,
        qualityLevel=quality_level,
        minDistance=min_distance,
        blockSize=block_size,
        useHarrisDetector=True,
        k=k,
    )
    if corners is None or len(corners) == 0:
        return np.zeros((0, 2), dtype=np.float32)
    corners = corners.reshape(-1, 2).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.01)
    refined = cv2.cornerSubPix(gray, corners, (5, 5), (-1, -1), criteria)
    return refined.astype(np.float32)


def draw_corners(
    image_bgr: np.ndarray,
    corners_xy: np.ndarray,
    radius: int = 3,
    color: tuple[int, int, int] = (0, 255, 255),
) -> np.ndarray:
    """返回带角点绘制结果的新图像。"""
    out = image_bgr.copy()
    for x, y in corners_xy:
        p = (int(round(float(x))), int(round(float(y))))
        cv2.circle(out, p, radius, color, 1, lineType=cv2.LINE_AA)
    return out
