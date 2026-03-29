"""角点邻域描述子：强度直方图 + 梯度方向直方图（加权）。"""

from __future__ import annotations

import cv2
import numpy as np


def build_corner_descriptors(
    gray: np.ndarray,
    pts: np.ndarray,
    patch_radius: int = 15,
    intensity_bins: int = 16,
    orientation_bins: int = 8,
) -> tuple[np.ndarray, np.ndarray]:
    """
    对每个角点取正方形邻域，拼接：
    - 灰度强度直方图（归一化）
    - 梯度方向直方图（0~π 无符号，按梯度幅值加权并归一化）
    整张向量再 L2 归一化。

    越界的角点跳过。返回 (描述子矩阵 N×D, 有效角点在 pts 中的下标)。
    """
    if pts.size == 0:
        return np.zeros((0, intensity_bins + orientation_bins), dtype=np.float32), np.zeros(
            (0,), dtype=np.int32
        )

    h, w = gray.shape[:2]
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)

    r = patch_radius
    desc_list: list[np.ndarray] = []
    indices: list[int] = []

    for k in range(pts.shape[0]):
        xi = int(round(float(pts[k, 0])))
        yi = int(round(float(pts[k, 1])))
        if xi - r < 0 or xi + r >= w or yi - r < 0 or yi + r >= h:
            continue

        patch = gray[yi - r : yi + r + 1, xi - r : xi + r + 1]
        pgx = gx[yi - r : yi + r + 1, xi - r : xi + r + 1]
        pgy = gy[yi - r : yi + r + 1, xi - r : xi + r + 1]

        ih, _ = np.histogram(patch, bins=intensity_bins, range=(0, 256))
        ih = ih.astype(np.float64)
        ih /= float(ih.sum()) + 1e-8

        mag = np.sqrt(pgx * pgx + pgy * pgy)
        ang = np.arctan2(pgy, pgx)
        ang = np.mod(ang, np.pi)
        obin = (ang / np.pi * orientation_bins).astype(np.int32)
        obin = np.clip(obin, 0, orientation_bins - 1)
        oh = np.bincount(obin.ravel(), weights=mag.ravel(), minlength=orientation_bins).astype(
            np.float64
        )
        oh /= float(oh.sum()) + 1e-8

        v = np.concatenate([ih, oh]).astype(np.float64)
        nrm = np.linalg.norm(v)
        if nrm < 1e-8:
            continue
        v /= nrm
        desc_list.append(v.astype(np.float32))
        indices.append(k)

    if not desc_list:
        return np.zeros((0, intensity_bins + orientation_bins), dtype=np.float32), np.zeros(
            (0,), dtype=np.int32
        )

    return np.stack(desc_list, axis=0), np.array(indices, dtype=np.int32)
