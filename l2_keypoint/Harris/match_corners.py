"""角点匹配：仿射预测（可选）与描述子相似度匹配。"""

from __future__ import annotations

import numpy as np

from harris_corner import affine_apply_xy


def match_by_descriptor_similarity(
    desc_a: np.ndarray,
    desc_b: np.ndarray,
    idx_a: np.ndarray,
    idx_b: np.ndarray,
    ratio: float = 0.75,
    mutual: bool = True,
) -> list[tuple[int, int]]:
    """
    用 L2 归一化描述子的欧氏距离；Lowe 距离比检验；可选互最近邻。
    返回 (pts_a 原始下标, pts_b 原始下标) 列表。
    """
    if desc_a.shape[0] == 0 or desc_b.shape[0] == 0:
        return []

    # ||a-b||^2 = 2 - 2 a·b（单位向量）
    dist = np.sqrt(np.maximum(0.0, 2.0 - 2.0 * (desc_a @ desc_b.T)))
    na, nb = dist.shape

    candidates: list[tuple[int, int]] = []
    for i in range(na):
        row = dist[i]
        order = np.argsort(row)
        j0 = int(order[0])
        d0 = float(row[j0])
        if nb >= 2:
            d1 = float(row[int(order[1])])
            if d0 >= ratio * (d1 + 1e-8):
                continue
        candidates.append((i, j0))

    if not mutual:
        return [(int(idx_a[i]), int(idx_b[j])) for i, j in candidates]

    # 互最近邻：j 在列上最近的 i 须为当前 i
    nearest_i_for_b = np.argmin(dist, axis=0)
    matches: list[tuple[int, int]] = []
    for i, j in candidates:
        if nearest_i_for_b[j] == i:
            matches.append((int(idx_a[i]), int(idx_b[j])))
    return matches


def match_by_affine_prediction(
    pts_a: np.ndarray,
    pts_b: np.ndarray,
    M_a_to_b: np.ndarray,
    max_dist: float,
) -> list[tuple[int, int]]:
    """
    将 A 中角点经 M 映射到 B 坐标系，与 pts_b 做最近邻匹配；
    按预测误差升序贪心，保证每个 b 下标至多匹配一次。
    """
    if pts_a.size == 0 or pts_b.size == 0:
        return []

    pred_b = affine_apply_xy(M_a_to_b, pts_a)
    candidates: list[tuple[float, int, int]] = []
    for i in range(pred_b.shape[0]):
        d = np.linalg.norm(pts_b - pred_b[i : i + 1], axis=1)
        j = int(np.argmin(d))
        err = float(d[j])
        if err <= max_dist:
            candidates.append((err, i, j))

    candidates.sort(key=lambda t: t[0])
    used_a: set[int] = set()
    used_b: set[int] = set()
    matches: list[tuple[int, int]] = []
    for _, i, j in candidates:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        matches.append((i, j))
    return matches
