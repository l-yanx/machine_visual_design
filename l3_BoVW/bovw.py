"""
3×3 空间分块 + Dense SIFT(128) + 共享视觉词典 KMeans(100)；
每块 L1-归一化直方图，9 块拼接为 9×K 维后再 L2-单位化。
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

# 子块内密集采样网格边长（5×5=25 个 SIFT/块）
REGION_GRID = 5
DESCRIPTOR_DIM = 128
K_VISUAL = 100
SPATIAL = 3
N_REGIONS = SPATIAL * SPATIAL
# 默认 k==K_VISUAL 时总维 900；任一块词表长度 k_word 时维数为 N_REGIONS * k_word
BOW_DIM_DEFAULT = N_REGIONS * K_VISUAL

TARGET_SIZE = (1920, 1080)  # (width, height)
SIFT_KEYPOINT_SIZE = 16.0


def list_image_files(folder: Path) -> list[Path]:
    return sorted(
        p
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
    )


def person_root_dirs(dataset_root: Path) -> list[Path]:
    return sorted(
        p
        for p in dataset_root.iterdir()
        if p.is_dir() and p.name != "vedio" and p.name != "video"
    )


def load_bgr(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"无法读取图像: {path}")
    return img


def to_fixed_resolution(bgr: np.ndarray) -> np.ndarray:
    w, h = TARGET_SIZE
    if bgr.shape[1] == w and bgr.shape[0] == h:
        return bgr
    return cv2.resize(bgr, (w, h), interpolation=cv2.INTER_AREA)


def _region_boundaries_3x3(h: int, w: int) -> list[tuple[int, int, int, int]]:
    """(y0, y1, x0, x1) 全闭开区间 [y0,y1) [x0,x1)，共 9 块，行主序：左上为 0，右下为 8。"""
    y_edges = [int(round(i * h / SPATIAL)) for i in range(SPATIAL + 1)]
    x_edges = [int(round(i * w / SPATIAL)) for i in range(SPATIAL + 1)]
    out: list[tuple[int, int, int, int]] = []
    for ri in range(SPATIAL):
        for ci in range(SPATIAL):
            y0, y1 = y_edges[ri], y_edges[ri + 1]
            x0, x1 = x_edges[ci], x_edges[ci + 1]
            out.append((y0, y1, x0, x1))
    return out


def _dense_keypoints(width: int, height: int, grid: int) -> list[cv2.KeyPoint]:
    kps: list[cv2.KeyPoint] = []
    for j in range(grid):
        for i in range(grid):
            x = (i + 0.5) * (width / grid)
            y = (j + 0.5) * (height / grid)
            kps.append(cv2.KeyPoint(float(x), float(y), SIFT_KEYPOINT_SIZE))
    return kps


_sift_impl = None


def _get_sift():
    global _sift_impl
    if _sift_impl is None:
        _sift_impl = cv2.SIFT_create()
    return _sift_impl


def dense_sift_on_gray(gray: np.ndarray) -> np.ndarray:
    """
    单块灰度图，grid x grid 个关键点。返回 (grid*grid, 128) float32。
    """
    h, w = gray.shape[:2]
    if w < 8 or h < 8:
        raise ValueError("子区域过小，无法提 SIFT")
    kps = _dense_keypoints(w, h, REGION_GRID)
    sift = _get_sift()
    kps, des = sift.compute(gray, kps)
    n_exp = REGION_GRID * REGION_GRID
    if des is None or len(des) != n_exp:
        raise RuntimeError(
            f"子块 SIFT 数量异常: 期望 {n_exp}, 得到 {0 if des is None else len(des)}"
        )
    if des.shape[1] != DESCRIPTOR_DIM:
        raise RuntimeError(f"描述子维度应为 {DESCRIPTOR_DIM}, 得到 {des.shape[1]}")
    return des.astype(np.float32, copy=False)


def collect_sift_for_vocab_training(bgr: np.ndarray) -> np.ndarray:
    """
    训练词典：9 个区域所有子块 SIFT 拼成 (9*R*R, 128)（R=REGION_GRID）。
    """
    bgr = to_fixed_resolution(bgr)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    parts: list[np.ndarray] = []
    for y0, y1, x0, x1 in _region_boundaries_3x3(h, w):
        tile = gray[y0:y1, x0:x1]
        parts.append(dense_sift_on_gray(tile))
    return np.vstack(parts)


def assign_visual_words(
    descriptors: np.ndarray, centers: np.ndarray
) -> np.ndarray:
    diff = descriptors[:, np.newaxis, :] - centers[np.newaxis, :, :]
    d2 = np.einsum("ijk,ijk->ij", diff, diff)
    return np.argmin(d2, axis=1).astype(np.int64)


def bow_histogram(visual_word_ids: np.ndarray, k_words: int = K_VISUAL) -> np.ndarray:
    hist, _ = np.histogram(visual_word_ids, bins=k_words, range=(0, k_words))
    h = hist.astype(np.float64)
    s = h.sum()
    if s == 0:
        return h
    return h / s


def l2_unit_vector(x: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """一维特征向量 L2 归一化为单位范数（float32）；范数过小则原样返回。"""
    t = np.asarray(x, dtype=np.float64)
    n = float(np.linalg.norm(t))
    if n <= eps:
        return t.astype(np.float32, copy=False)
    return (t / n).astype(np.float32, copy=False)


def encode_image_spatial_bow(
    bgr: np.ndarray, centers: np.ndarray, k_words: int = K_VISUAL
) -> np.ndarray:
    """
    9 个区域各 K 维 L1-归一化直方图，按行主序拼接为 9×K 维，再对整段做 L2 单位化，形状 (9×K,)。
    """
    bgr = to_fixed_resolution(bgr)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    blocks: list[np.ndarray] = []
    for y0, y1, x0, x1 in _region_boundaries_3x3(h, w):
        tile = gray[y0:y1, x0:x1]
        d = dense_sift_on_gray(tile)
        v = assign_visual_words(d, centers)
        blocks.append(bow_histogram(v, k_words=k_words).astype(np.float32))
    stacked = np.concatenate(blocks, axis=0)
    return l2_unit_vector(stacked)


def collect_sift_from_image_path(path: Path) -> np.ndarray:
    return collect_sift_for_vocab_training(load_bgr(path))
