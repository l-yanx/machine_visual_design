"""
把 ../test/test1.jpg, test3.jpg, test4.jpg 与库特征一起做 PCA(50) + t-SNE(2)，
观察 query 在 t-SNE 平面上落在哪里。输出: ./output/tsne_with_queries.png

注意：t-SNE 不支持对新点做 transform，因此 query 必须与库点一起重新做一次 t-SNE，
其库点坐标与 visualize.py 那张图不会完全一致，但簇结构应当稳定。
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
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

# 让脚本在 t-sne/ 子目录下也能 import 仓库根的 bovw 模块
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from bovw import N_REGIONS, encode_image_spatial_bow, load_bgr  # noqa: E402


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


DEFAULT_QUERIES = ["test1.jpg", "test3.jpg", "test4.jpg"]


def main() -> None:
    _ensure_cjk_font()
    ap = argparse.ArgumentParser(
        description="库特征 + test1/3/4 一起 PCA(50)+t-SNE(2) 可视化"
    )
    ap.add_argument("--art_dir", type=Path, default=_HERE.parent / "output")
    ap.add_argument("--test_dir", type=Path, default=_HERE.parent / "test")
    ap.add_argument(
        "--queries",
        nargs="+",
        default=DEFAULT_QUERIES,
        help="test 目录下的查询图文件名",
    )
    ap.add_argument("--out_dir", type=Path, default=_HERE / "output")
    ap.add_argument("--pca_dim", type=int, default=50)
    ap.add_argument("--perplexity", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    feats = np.load(args.art_dir / "features.npy")
    labels = np.array([str(x) for x in np.load(args.art_dir / "label.npy", allow_pickle=True)])
    centers = np.load(args.art_dir / "visual_vocab.npy")
    if feats.ndim != 2 or len(labels) != feats.shape[0]:
        print("features/label 形状不一致", file=sys.stderr)
        sys.exit(1)
    k_words = centers.shape[0]
    if feats.shape[1] != N_REGIONS * k_words:
        print("features 维度与 9*K 不一致", file=sys.stderr)
        sys.exit(1)

    q_vecs: list[np.ndarray] = []
    q_names: list[str] = []
    for fname in args.queries:
        p = args.test_dir / fname
        if not p.exists():
            print(f"跳过不存在的查询图: {p}", file=sys.stderr)
            continue
        bgr = load_bgr(p)
        v = encode_image_spatial_bow(bgr, centers, k_words=k_words)
        q_vecs.append(v.astype(np.float32, copy=False))
        q_names.append(p.stem)
    if not q_vecs:
        print("没有可用的查询图", file=sys.stderr)
        sys.exit(1)
    Q = np.stack(q_vecs, axis=0)

    # 拼接：库在前，query 在后
    X = np.vstack([feats, Q])
    n_total, d = X.shape
    n_lib = feats.shape[0]
    n_q = Q.shape[0]

    pca_dim = max(2, min(args.pca_dim, d, n_total - 1))
    perplexity = max(2.0, min(args.perplexity, max(2.0, (n_total - 1) / 3)))

    Xp = PCA(n_components=pca_dim, random_state=args.seed).fit_transform(X)
    Xt = TSNE(
        n_components=2,
        perplexity=perplexity,
        random_state=args.seed,
        init="pca",
        learning_rate="auto",
        metric="euclidean",
    ).fit_transform(Xp)

    Xt_lib = Xt[:n_lib]
    Xt_q = Xt[n_lib:]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    uniq = sorted(set(labels.tolist()))
    cmap = plt.get_cmap("tab20") if len(uniq) <= 20 else plt.get_cmap("gist_ncar")

    fig, ax = plt.subplots(figsize=(9.5, 7.5))
    for i, name in enumerate(uniq):
        m = labels == name
        color = cmap(i % 20) if len(uniq) <= 20 else cmap(i / max(1, len(uniq) - 1))
        ax.scatter(Xt_lib[m, 0], Xt_lib[m, 1], s=20, color=color, label=name, alpha=0.75)

    ax.scatter(
        Xt_q[:, 0],
        Xt_q[:, 1],
        s=180,
        marker="X",
        color="black",
        edgecolors="white",
        linewidths=1.2,
        zorder=5,
        label="query",
    )
    for (xq, yq), name in zip(Xt_q, q_names):
        ax.annotate(
            name,
            xy=(xq, yq),
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=10,
            color="black",
            fontweight="bold",
        )

    ax.set_title(
        f"库 + queries 共同 t-SNE (PCA={pca_dim} → t-SNE=2)\n"
        f"库 N={n_lib}, identities={len(uniq)}, queries={n_q}, perplexity={perplexity:.1f}"
    )
    ax.set_xlabel("dim 1")
    ax.set_ylabel("dim 2")
    ax.legend(loc="best", fontsize=8, frameon=False, ncol=2 if len(uniq) > 8 else 1)
    fig.tight_layout()
    fp = args.out_dir / "tsne_with_queries.png"
    fig.savefig(fp, dpi=150)
    print("saved:", fp)
    print("queries:", q_names)


if __name__ == "__main__":
    main()
