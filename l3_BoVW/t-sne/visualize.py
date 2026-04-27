"""
读取 BoVW 的 (features.npy, label.npy)，先 PCA 到 50 维，再 t-SNE 到 2 维，
按身份着色画散点图，保存到本目录的 output/。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无显示器/远端环境也能跑
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE


def _ensure_cjk_font() -> None:
    """让 matplotlib 使用系统里第一个可用的中文字体（找不到就保持默认）。"""
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


def main() -> None:
    _ensure_cjk_font()
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="900 维 BoVW: PCA(50) → t-SNE(2) 散点图")
    ap.add_argument(
        "--art_dir",
        type=Path,
        default=here.parent / "output",
        help="包含 label.npy / features.npy 的目录",
    )
    ap.add_argument(
        "--out_dir",
        type=Path,
        default=here / "output",
        help="散点图输出目录",
    )
    ap.add_argument("--pca_dim", type=int, default=50, help="PCA 中间维度")
    ap.add_argument(
        "--perplexity",
        type=float,
        default=30.0,
        help="t-SNE perplexity；样本太少会自动收缩到 (n-1)/3",
    )
    ap.add_argument("--seed", type=int, default=42, help="随机种子，可复现")
    args = ap.parse_args()

    feats = np.load(args.art_dir / "features.npy")
    labels = np.load(args.art_dir / "label.npy", allow_pickle=True)
    if feats.ndim != 2 or len(labels) != feats.shape[0]:
        print("features/label 形状不一致", file=sys.stderr)
        sys.exit(1)

    n, d = feats.shape
    pca_dim = max(2, min(args.pca_dim, d, n - 1))
    perplexity = max(2.0, min(args.perplexity, max(2.0, (n - 1) / 3)))

    Xp = PCA(n_components=pca_dim, random_state=args.seed).fit_transform(feats)
    Xt = TSNE(
        n_components=2,
        perplexity=perplexity,
        random_state=args.seed,
        init="pca",
        learning_rate="auto",
        metric="euclidean",
    ).fit_transform(Xp)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    uniq = sorted({str(x) for x in labels.tolist()})
    cmap = plt.get_cmap("tab20") if len(uniq) <= 20 else plt.get_cmap("gist_ncar")

    fig, ax = plt.subplots(figsize=(9, 7))
    for i, name in enumerate(uniq):
        mask = np.array([str(x) == name for x in labels])
        color = cmap(i % 20) if len(uniq) <= 20 else cmap(i / max(1, len(uniq) - 1))
        ax.scatter(Xt[mask, 0], Xt[mask, 1], s=22, color=color, label=name, alpha=0.85)

    ax.set_title(
        f"BoVW t-SNE (PCA={pca_dim} → t-SNE=2)\n"
        f"N={n} 张图, identities={len(uniq)}, perplexity={perplexity:.1f}"
    )
    ax.set_xlabel("dim 1")
    ax.set_ylabel("dim 2")
    if len(uniq) <= 30:
        ax.legend(loc="best", fontsize=7, frameon=False, ncol=2 if len(uniq) > 8 else 1)
    fig.tight_layout()
    fp = args.out_dir / "tsne_scatter.png"
    fig.savefig(fp, dpi=150)
    print("saved:", fp)


if __name__ == "__main__":
    main()
