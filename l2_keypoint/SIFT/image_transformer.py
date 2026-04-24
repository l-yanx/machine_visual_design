"""从输入图像 A 生成变换后的图像 B。"""

from __future__ import annotations

import cv2
import numpy as np


def transform_image(
    img: np.ndarray,
    angle_deg: float = 12.0,
    tx_px: float = 20.0,
    ty_px: float = 12.0,
    perspective: float = 0.02,
    blur_ksize: int = 5,
    blur_sigma: float = 0.0,
) -> np.ndarray:
    """执行旋转、平移、轻微透视映射和高斯模糊，输出图像 B。"""
    h, w = img.shape[:2]

    center = (w * 0.5, h * 0.5)
    M_rot = cv2.getRotationMatrix2D(center, angle_deg, 1.0).astype(np.float64)
    M_rot[0, 2] += tx_px
    M_rot[1, 2] += ty_px
    b = cv2.warpAffine(
        img,
        M_rot,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )

    dx = float(w) * perspective
    dy = float(h) * perspective
    src = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    dst = np.array([[dx, dy], [w - 1 - dx, 0], [w - 1, h - 1 - dy], [0, h - 1]], dtype=np.float32)
    H = cv2.getPerspectiveTransform(src, dst)
    b = cv2.warpPerspective(
        b,
        H,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )

    k = int(blur_ksize)
    if k % 2 == 0:
        k += 1
    if k >= 3:
        b = cv2.GaussianBlur(b, (k, k), blur_sigma)
    return b
