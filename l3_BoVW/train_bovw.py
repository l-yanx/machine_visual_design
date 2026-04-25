"""
3×3 分块、每块 Dense-SIFT + 共享 KMeans(100) 视觉词典；
单图 9×K 维 L2 单位向量；每人物多图 L2-平均后再 L2 得原型。
输出 label.npy、features.npy(人数×9K)、visual_vocab.npy(K×128)。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans

from bovw import (
    DESCRIPTOR_DIM,
    K_VISUAL,
    N_REGIONS,
    collect_sift_from_image_path,
    encode_image_spatial_bow,
    l2_unit_vector,
    list_image_files,
    load_bgr,
    person_root_dirs,
)

RNG = 42


def main() -> None:
    ap = argparse.ArgumentParser(description="训练空间 BoVW 与人物级特征")
    ap.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).resolve().parent / "dataset",
        help="含若干人名子文件夹的数据根目录（排除 vedio）",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "output",
        help="输出 npy 所在目录",
    )
    ap.add_argument(
        "--k-visual",
        type=int,
        default=K_VISUAL,
        help="每块直方图维度 / 聚类数 K",
    )
    ap.add_argument(
        "--max-train-samples",
        type=int,
        default=0,
        help="KMeans 时最多用多少条 SIFT 描述子，0 为不限制",
    )
    args = ap.parse_args()
    dataset: Path = args.dataset
    out: Path = args.out
    k_vis = int(args.k_visual)
    if k_vis < 1:
        print("k-visual 须为正整数", file=sys.stderr)
        sys.exit(1)

    persons = person_root_dirs(dataset)
    if not persons:
        print(f"未在 {dataset} 下找到人名子文件夹（或仅有 vedio）", file=sys.stderr)
        sys.exit(1)

    all_desc: list[np.ndarray] = []
    for pdir in persons:
        imgs = list_image_files(pdir)
        if not imgs:
            print(f"跳过空文件夹: {pdir}", file=sys.stderr)
            continue
        for ip in imgs:
            all_desc.append(collect_sift_from_image_path(ip))

    if not all_desc:
        print("没有可用的描述子", file=sys.stderr)
        sys.exit(1)

    X = np.vstack(all_desc)
    n_desc = X.shape[0]
    if args.max_train_samples and args.max_train_samples < n_desc:
        r = np.random.default_rng(RNG)
        idx = r.choice(n_desc, size=args.max_train_samples, replace=False)
        X_train = X[idx]
    else:
        X_train = X

    if X_train.shape[0] < k_vis:
        print(
            f"训练样本 {X_train.shape[0]} 小于聚类数 {k_vis}，请增图或降低 k。",
            file=sys.stderr,
        )
        sys.exit(1)

    km = KMeans(
        n_clusters=k_vis,
        random_state=RNG,
        n_init=10,
        max_iter=300,
    )
    km.fit(X_train)
    centers = np.asarray(km.cluster_centers_, dtype=np.float32)

    labels_out: list[str] = []
    features_rows: list[np.ndarray] = []

    for pdir in persons:
        imgs = list_image_files(pdir)
        if not imgs:
            continue
        vecs: list[np.ndarray] = []
        for ip in imgs:
            bgr = load_bgr(ip)
            v = encode_image_spatial_bow(bgr, centers, k_words=k_vis)
            if v.shape[0] != N_REGIONS * k_vis:
                print("单图特征维应为 9*K", file=sys.stderr)
                sys.exit(1)
            vecs.append(v.astype(np.float64))
        proto = l2_unit_vector(np.mean(np.stack(vecs, axis=0), axis=0))
        labels_out.append(pdir.name)
        features_rows.append(proto)

    if not labels_out:
        print("无有效人物文件夹", file=sys.stderr)
        sys.exit(1)

    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "label.npy", np.array(labels_out, dtype=object))
    features_mat = np.stack(features_rows, axis=0)
    if features_mat.shape[1] != N_REGIONS * k_vis:
        print("特征维应为 9*K", file=sys.stderr)
        sys.exit(1)
    np.save(out / "features.npy", features_mat)
    np.save(out / "visual_vocab.npy", centers)

    print("人物数:", len(labels_out))
    print("每图块数×K:", N_REGIONS, "×", k_vis, "=> 特征维", N_REGIONS * k_vis)
    print("SIFT 维:", DESCRIPTOR_DIM, " 子块网格:", 5, "x", 5, "/ 区域")
    print("已写入:", out / "label.npy", out / "features.npy", out / "visual_vocab.npy")


if __name__ == "__main__":
    main()
