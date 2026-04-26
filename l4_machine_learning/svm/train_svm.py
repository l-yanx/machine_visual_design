#!/usr/bin/env python3
"""Train an SVM classifier on the ArcFace embeddings stored in embedding/gallery.npz."""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC


def main() -> int:
    here = Path(__file__).resolve().parent
    project_root = here.parent

    parser = argparse.ArgumentParser(description="Train an SVM on ArcFace embeddings")
    parser.add_argument("--gallery", type=Path, default=project_root / "embedding" / "gallery.npz",
                        help="Path to gallery.npz produced by build_gallery.py")
    parser.add_argument("--out", type=Path, default=here / "svm_model.pkl",
                        help="Output pickle path for the trained classifier")
    parser.add_argument("--kernel", type=str, default="linear", choices=["linear", "rbf"])
    parser.add_argument("--C", type=float, default=1.0)
    parser.add_argument("--gamma", type=str, default="scale", help="Only used for rbf kernel")
    args = parser.parse_args()

    if not args.gallery.is_file():
        print(f"Gallery not found: {args.gallery}", file=sys.stderr)
        return 1

    data = np.load(args.gallery, allow_pickle=True)
    X = data["embeddings"].astype(np.float32)
    y_str = np.asarray(data["labels"]).astype(str)

    # ArcFace embeddings 已 L2 归一化；此处仅作防御性归一化
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)

    le = LabelEncoder()
    y = le.fit_transform(y_str)
    classes = list(le.classes_)
    if len(classes) < 2:
        print(f"SVM 需要至少 2 个身份，但只发现 {len(classes)} 个: {classes}", file=sys.stderr)
        return 1

    print(f"Training SVM (kernel={args.kernel}, C={args.C}) "
          f"on {X.shape[0]} samples, {len(classes)} classes")
    clf = SVC(C=args.C, kernel=args.kernel, gamma=args.gamma, probability=True)
    clf.fit(X, y)

    train_acc = float((clf.predict(X) == y).mean())
    print(f"Train accuracy: {train_acc:.4f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "wb") as f:
        pickle.dump({"clf": clf, "classes": classes, "kernel": args.kernel, "C": args.C}, f)
    print(f"Saved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
