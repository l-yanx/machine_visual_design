#!/usr/bin/env python3
"""ArcFace embedding 可视化：PCA(50) -> t-SNE(2) 散点图 + 两两余弦相似度热力图。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import LabelEncoder


def main() -> int:
    here = Path(__file__).resolve().parent
    project_root = here.parent

    parser = argparse.ArgumentParser(description="PCA->t-SNE scatter + pairwise cosine heatmap")
    parser.add_argument("--gallery", type=Path, default=project_root / "embedding" / "gallery.npz",
                        help="Path to gallery.npz produced by build_gallery.py")
    parser.add_argument("--output", type=Path, default=here / "output",
                        help="Directory to save output PNGs")
    parser.add_argument("--pca-dim", type=int, default=50, help="PCA components (default 50)")
    parser.add_argument("--perplexity", type=float, default=30.0, help="t-SNE perplexity")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not args.gallery.is_file():
        print(f"Gallery not found: {args.gallery}", file=sys.stderr)
        return 1

    args.output.mkdir(parents=True, exist_ok=True)

    data = np.load(args.gallery, allow_pickle=True)
    X = data["embeddings"].astype(np.float32)
    labels = np.asarray(data["labels"]).astype(str)

    # ArcFace embedding 已 L2 归一化；此处再做一次防御性归一
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)

    # 按身份排序，热力图能看出对角块
    order = np.argsort(labels, kind="stable")
    X = X[order]
    labels = labels[order]

    le = LabelEncoder()
    y = le.fit_transform(labels)
    classes = list(le.classes_)
    n_samples = X.shape[0]
    print(f"Loaded {n_samples} samples, {len(classes)} classes: {classes}")

    # PCA: 512 -> 50
    pca_dim = min(args.pca_dim, X.shape[1], n_samples)
    pca = PCA(n_components=pca_dim, random_state=args.seed)
    X_pca = pca.fit_transform(X)
    var_ratio = float(pca.explained_variance_ratio_.sum())
    print(f"PCA: 512 -> {pca_dim}, explained variance ratio: {var_ratio:.4f}")

    # t-SNE: 50 -> 2
    perp = float(min(args.perplexity, max(5.0, (n_samples - 1) / 3.0)))
    print(f"t-SNE: {pca_dim} -> 2, perplexity={perp}")
    tsne = TSNE(
        n_components=2,
        perplexity=perp,
        random_state=args.seed,
        init="pca",
        learning_rate="auto",
    )
    X_2d = tsne.fit_transform(X_pca)

    # 散点图
    fig, ax = plt.subplots(figsize=(8, 7))
    cmap = plt.get_cmap("tab10" if len(classes) <= 10 else "tab20")
    for i, c in enumerate(classes):
        mask = labels == c
        ax.scatter(
            X_2d[mask, 0], X_2d[mask, 1],
            s=22, alpha=0.85, label=c, color=cmap(i % cmap.N),
            edgecolors="none",
        )
    ax.set_title(f"PCA({pca_dim}) → t-SNE(2) of ArcFace embeddings")
    ax.set_xlabel("t-SNE-1")
    ax.set_ylabel("t-SNE-2")
    ax.legend(title="identity", loc="best", fontsize=9)
    fig.tight_layout()
    scatter_path = args.output / "tsne_scatter.png"
    fig.savefig(scatter_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {scatter_path}")

    # 热力图：两两余弦相似度，按身份排序
    sim = X @ X.T  # [-1, 1]
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(sim, cmap="viridis", vmin=-1.0, vmax=1.0, aspect="auto")
    fig.colorbar(im, ax=ax, label="cosine similarity")

    # 在身份分界处画白线，并把类名标到坐标轴中点
    boundaries: list[int] = []
    ticks: list[float] = []
    prev = labels[0]
    start = 0
    for i in range(1, n_samples + 1):
        if i == n_samples or labels[i] != prev:
            boundaries.append(i)
            ticks.append((start + i - 1) / 2.0)
            if i < n_samples:
                prev = labels[i]
                start = i
    for b in boundaries[:-1]:
        ax.axhline(b - 0.5, color="white", linewidth=0.6, alpha=0.7)
        ax.axvline(b - 0.5, color="white", linewidth=0.6, alpha=0.7)
    ax.set_xticks(ticks)
    ax.set_xticklabels(classes, rotation=45, ha="right")
    ax.set_yticks(ticks)
    ax.set_yticklabels(classes)
    ax.set_title("Pairwise cosine similarity (samples sorted by identity)")
    fig.tight_layout()
    heatmap_path = args.output / "pairwise_heatmap.png"
    fig.savefig(heatmap_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {heatmap_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
