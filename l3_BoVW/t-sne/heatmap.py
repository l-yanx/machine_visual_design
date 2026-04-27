"""
读取 BoVW 的 (features.npy, label.npy)，按身份排序后绘制 N×N 欧氏距离热图，
保存到本目录的 output/。深色 = 距离小（同身份理应在对角块上更深）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np


def _ensure_cjk_font() -> None:
    candidates = [
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "Source Han Sans CN",
        "WenQuanYi Zen Hei",
        "WenQuanYi Micro Hei",
        "PingFang SC",
        "Microsoft YaHei",
        "SimHei",
        "AR PL UMing CN",
        "AR PL UKai CN",
    ]
    have = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in have:
            plt.rcParams["font.family"] = [name]
            plt.rcParams["font.sans-serif"] = [name] + plt.rcParams.get("font.sans-serif", [])
            plt.rcParams["axes.unicode_minus"] = False
            return


def pairwise_euclidean(F: np.ndarray) -> np.ndarray:
    """N×N 欧氏距离矩阵；用 ||a-b||^2 = ||a||^2+||b||^2-2 a·b 矢量化算。"""
    sq = (F * F).sum(axis=1)
    d2 = sq[:, None] + sq[None, :] - 2.0 * (F @ F.T)
    np.maximum(d2, 0.0, out=d2)
    return np.sqrt(d2)


def main() -> None:
    _ensure_cjk_font()
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="BoVW 特征 N×N 欧氏距离热图（按身份排序）")
    ap.add_argument("--art_dir", type=Path, default=here.parent / "output")
    ap.add_argument("--out_dir", type=Path, default=here / "output")
    args = ap.parse_args()

    feats = np.load(args.art_dir / "features.npy")
    labels = np.load(args.art_dir / "label.npy", allow_pickle=True)
    labels = np.array([str(x) for x in labels])
    if feats.ndim != 2 or len(labels) != feats.shape[0]:
        print("features/label 形状不一致", file=sys.stderr)
        sys.exit(1)

    order = np.argsort(labels, kind="stable")
    F = feats[order].astype(np.float64, copy=False)
    L = labels[order]

    D = pairwise_euclidean(F)
    Dvis = D.copy()
    np.fill_diagonal(Dvis, np.nan)

    uniq, counts = np.unique(L, return_counts=True)
    bounds = np.cumsum(counts)
    centers = bounds - counts / 2.0

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(Dvis, cmap="magma_r", aspect="equal", interpolation="nearest")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("euclidean distance (越浅越相似)")

    for b in bounds[:-1]:
        ax.axhline(b - 0.5, color="white", linewidth=0.8, alpha=0.8)
        ax.axvline(b - 0.5, color="white", linewidth=0.8, alpha=0.8)

    ax.set_xticks(centers)
    ax.set_xticklabels(uniq, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(centers)
    ax.set_yticklabels(uniq, fontsize=9)
    ax.set_title(
        f"BoVW 特征 N×N 欧氏距离矩阵 (按身份分块)\n"
        f"N={len(L)} 张图, identities={len(uniq)}"
    )

    fig.tight_layout()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    fp = args.out_dir / "distance_heatmap.png"
    fig.savefig(fp, dpi=150)
    print("saved:", fp)


if __name__ == "__main__":
    main()
