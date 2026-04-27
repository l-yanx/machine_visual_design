"""
查询图 9×K 维空间 BoVW（L2-单位）与库中**每张图**特征逐行比欧氏距离，距离越小越相似。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from bovw import N_REGIONS, encode_image_spatial_bow, load_bgr


def euclidean(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def main() -> None:
    ap = argparse.ArgumentParser(description="对单张图做 9×K 维 BoVW，按欧氏距离近邻人名")
    ap.add_argument("image", type=Path, help="查询图像路径")
    ap.add_argument(
        "--art_dir",
        type=Path,
        default=Path(__file__).resolve().parent / "output",
        help="含 label.npy, features.npy, visual_vocab.npy",
    )
    ap.add_argument(
        "--top_k",
        type=int,
        default=3,
        help="输出欧氏距离最小的前 K 行（同一人可能因多张图出现多次）",
    )
    ap.add_argument(
        "--print-stats",
        action="store_true",
        help="打印与库内所有图的欧氏距离 min/max/mean/std/极差，用于判断区分度",
    )
    args = ap.parse_args()
    ad = args.art_dir
    lab = np.load(ad / "label.npy", allow_pickle=True)
    feats = np.load(ad / "features.npy")
    centers = np.load(ad / "visual_vocab.npy")

    if feats.ndim != 2 or feats.shape[0] < 1:
        print("features.npy 形状异常", file=sys.stderr)
        sys.exit(1)
    k_words = centers.shape[0]
    expected = N_REGIONS * k_words
    if centers.shape[1] != 128 or feats.shape[1] != expected:
        print("features 第二维应等于 9*K 且与 visual_vocab 的 K 一致", file=sys.stderr)
        sys.exit(1)
    n = min(len(lab), feats.shape[0])
    if n == 0:
        print("空库", file=sys.stderr)
        sys.exit(1)

    bgr = load_bgr(args.image)
    q = encode_image_spatial_bow(bgr, centers, k_words=k_words)
    if q.shape[0] != expected:
        print("查询特征维与 9*K 不一致", file=sys.stderr)
        sys.exit(1)

    diffs = feats[:n].astype(np.float64) - q.astype(np.float64)
    dists = np.linalg.norm(diffs, axis=1)

    if args.print_stats:
        order_full = np.argsort(dists)
        j0 = int(order_full[0])
        if n > 1:
            j1 = int(order_full[1])
            gap12 = float(dists[j1] - dists[j0])
        else:
            gap12 = 0.0
        dmin = float(dists.min())
        dmax = float(dists.max())
        dmean = float(dists.mean())
        dstd = float(dists.std())
        span = dmax - dmin
        print(
            "stats: n=%d  min=%.6f  max=%.6f  mean=%.6f  std=%.6f  span(max-min)=%.6f"
            % (n, dmin, dmax, dmean, dstd, span)
        )
        print(
            "       top1-top2 gap=%.6f  (span 或 gap 很小时，说明与多数图距离都差不多，特征区分度弱)"
            % gap12
        )

    show = min(args.top_k, n)
    order = np.argsort(dists)[:show]
    print("query:", args.image)
    print("metric: 欧氏距离 (越小越相似)")
    for rank, j in enumerate(order, start=1):
        print(f"  {rank}. {lab[j]!r}  distance={dists[j]:.6f}")


if __name__ == "__main__":
    main()
