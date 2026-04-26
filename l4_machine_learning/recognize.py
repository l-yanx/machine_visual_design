#!/usr/bin/env python3
"""Run detection + alignment + embedding, match by cosine similarity or SVM."""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

from fr_utils import create_face_app, ensure_l2, pick_primary_face

IMAGE_SUFFIX = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def load_gallery(path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(path, allow_pickle=True)
    emb = data["embeddings"].astype(np.float32)
    labels = data["labels"]
    return emb, labels


def load_svm(path: Path) -> dict:
    with open(path, "rb") as f:
        bundle = pickle.load(f)
    if "clf" not in bundle or "classes" not in bundle:
        raise ValueError(f"Invalid SVM bundle: {path}")
    return bundle


def collect_images(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            for q in sorted(p.rglob("*")):
                if q.is_file() and q.suffix.lower() in IMAGE_SUFFIX:
                    out.append(q)
        elif p.is_file() and p.suffix.lower() in IMAGE_SUFFIX:
            out.append(p)
    return out


def main() -> int:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="1:N face identification (cosine or SVM)")
    parser.add_argument("inputs", nargs="+", type=Path, help="Image file(s) or directories")
    parser.add_argument("--matcher", choices=["cosine", "svm"], default="cosine",
                        help="Choose cosine similarity (default) or SVM classifier")
    parser.add_argument("--gallery", type=Path, default=root / "embedding" / "gallery.npz",
                        help="Used by cosine matcher")
    parser.add_argument("--svm-model", type=Path, default=root / "svm" / "svm_model.pkl",
                        help="Used by svm matcher")
    parser.add_argument("--threshold", type=float, default=0.35,
                        help="cosine: min similarity; svm: min probability")
    parser.add_argument("--model", type=str, default="buffalo_l")
    parser.add_argument("--model-root", type=Path, default=root / "models")
    parser.add_argument("--ctx-id", type=int, default=0)
    parser.add_argument("--det-size", type=int, nargs=2, default=[640, 640])
    parser.add_argument("--det-thresh", type=float, default=0.5)
    parser.add_argument("--topk", type=int, default=3)
    args = parser.parse_args()

    if args.matcher == "cosine":
        if not args.gallery.is_file():
            print(f"Gallery not found: {args.gallery}", file=sys.stderr)
            return 1
        gallery_emb, gallery_labels = load_gallery(args.gallery)
        gallery_emb = gallery_emb / (np.linalg.norm(gallery_emb, axis=1, keepdims=True) + 1e-12)
        svm_bundle = None
    else:
        if not args.svm_model.is_file():
            print(f"SVM model not found: {args.svm_model}\n"
                  f"先运行: python svm/train_svm.py", file=sys.stderr)
            return 1
        svm_bundle = load_svm(args.svm_model)
        gallery_emb, gallery_labels = None, None

    app = create_face_app(
        ctx_id=args.ctx_id,
        model_name=args.model,
        model_root=args.model_root,
        det_size=(int(args.det_size[0]), int(args.det_size[1])),
        det_thresh=args.det_thresh,
    )

    images = collect_images(args.inputs)
    if not images:
        print("No input images.", file=sys.stderr)
        return 1

    for img_path in tqdm(images, unit="img"):
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"[skip unreadable] {img_path}")
            continue
        faces = app.get(img)
        face = pick_primary_face(faces)
        if face is None:
            print(f"[no face] {img_path}")
            continue
        q = ensure_l2(np.asarray(face.embedding, dtype=np.float32))

        if args.matcher == "cosine":
            sims = gallery_emb @ q
            order = np.argsort(-sims)
            topk = min(args.topk, sims.shape[0])
            best_i = int(order[0])
            best_score = float(sims[best_i])
            pred = str(gallery_labels[best_i])
            if best_score < args.threshold:
                pred = "unknown"
            top_matches = [
                {"identity": str(gallery_labels[int(order[j])]),
                 "similarity": float(sims[int(order[j])])}
                for j in range(topk)
            ]
            score_field = "best_similarity"
        else:
            clf = svm_bundle["clf"]
            classes = svm_bundle["classes"]
            proba = clf.predict_proba(q.reshape(1, -1))[0]
            order = np.argsort(-proba)
            topk = min(args.topk, len(classes))
            best_i = int(order[0])
            best_score = float(proba[best_i])
            pred = str(classes[best_i])
            if best_score < args.threshold:
                pred = "unknown"
            top_matches = [
                {"identity": str(classes[int(order[j])]),
                 "probability": float(proba[int(order[j])])}
                for j in range(topk)
            ]
            score_field = "best_probability"

        line = {
            "image": str(img_path),
            "matcher": args.matcher,
            "prediction": pred,
            score_field: best_score,
            "threshold": args.threshold,
        }
        if topk > 1:
            line["top_matches"] = top_matches
        print(json.dumps(line, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
