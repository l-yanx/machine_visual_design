"""Harris 角点检测与亚像素细化。"""

from __future__ import annotations

import cv2
import numpy as np


def detect_harris_corners(
    gray: np.ndarray,
    max_corners: int = 800,
    quality_level: float = 0.01,
    min_distance: float = 8.0,
    block_size: int = 3,
    k: float = 0.04,
) -> np.ndarray:
    """
    使用 goodFeaturesToTrack + Harris 响应（OpenCV 等价于 Shi-Tomasi 接口但启用 Harris）。
    返回 float32 Nx2 角点坐标。
    """
    if gray.ndim != 2:
        raise ValueError("gray 必须为单通道灰度图")
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


def affine_apply_xy(M: np.ndarray, xy: np.ndarray) -> np.ndarray:
    """2x3 仿射矩阵作用于 Nx2 点集，结果为 Nx2。"""
    if xy.size == 0:
        return xy.copy()
    ones = np.ones((xy.shape[0], 1), dtype=np.float64)
    hom = np.hstack([xy.astype(np.float64), ones])
    return (hom @ M.T).astype(np.float32)
