"""由图像 A 生成旋转、平移、模糊后的图像 B，并返回 A→B 的仿射矩阵。"""

from __future__ import annotations

import cv2
import numpy as np


def synthesize_b(
    img: np.ndarray,
    angle_deg: float | None = None,
    tx_px: float | None = None,
    ty_px: float | None = None,
    blur_ksize: int = 5,
    blur_sigma: float = 0.0,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    对输入 BGR/RGB 或灰度图做旋转、平移、高斯模糊。
    输出与输入同尺寸 (h, w)，边界复制填充。

    返回:
        b: 变换后图像
        M: 2x3 float64，满足 [x', y']^T = M @ [x, y, 1]^T（源为 a，目标为 b）
    """
    rng = rng or np.random.default_rng()
    h, w = img.shape[:2]

    if angle_deg is None:
        angle_deg = float(rng.uniform(-18.0, 18.0))
    if tx_px is None:
        tx_px = float(rng.uniform(-0.08, 0.08)) * w
    if ty_px is None:
        ty_px = float(rng.uniform(-0.08, 0.08)) * h

    center = (w * 0.5, h * 0.5)
    M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    M = M.astype(np.float64)
    M[0, 2] += tx_px
    M[1, 2] += ty_px

    b = cv2.warpAffine(
        img,
        M,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )

    k = int(blur_ksize)
    if k % 2 == 0:
        k += 1
    if k >= 3:
        b = cv2.GaussianBlur(b, (k, k), blur_sigma)

    return b, M
