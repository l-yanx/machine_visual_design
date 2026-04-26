#!/usr/bin/env python3
"""Run detection + alignment + embedding, match gallery via cosine similarity."""

from __future__ import annotations

import argparse
import json
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


def main() -> int:
    parser = argparse.ArgumentParser(description="1:N face identification against embedding/gallery.npz")
    root = Path(__file__).resolve().parent
    parser.add_argument("inputs", nargs="+", type=Path, help="Image file(s) or directories")
    parser.add_argument("--gallery", type=Path, default=root / "embedding" / "gallery.npz")
    parser.add_argument("--threshold", type=float, default=0.35, help="Min cosine similarity for a hit")
    parser.add_argument("--model", type=str, default="buffalo_l")
    parser.add_argument("--model-root", type=Path, default=root / "models")
    parser.add_argument("--ctx-id", type=int, default=0)
    parser.add_argument("--det-size", type=int, nargs=2, default=[640, 640])
    parser.add_argument("--det-thresh", type=float, default=0.5)
    parser.add_argument("--topk", type=int, default=3, help="Show top-K matches")
    args = parser.parse_args()

    if not args.gallery.is_file():
        print(f"Gallery not found: {args.gallery}", file=sys.stderr)
        return 1

    gallery_emb, gallery_labels = load_gallery(args.gallery)
    # Normalize defensively
    gallery_emb = gallery_emb / (np.linalg.norm(gallery_emb, axis=1, keepdims=True) + 1e-12)

    app = create_face_app(
        ctx_id=args.ctx_id,
        model_name=args.model,
        model_root=args.model_root,
        det_size=(int(args.det_size[0]), int(args.det_size[1])),
        det_thresh=args.det_thresh,
    )

    def collect_images(paths: list[Path]) -> list[Path]:
        out: list[Path] = []
        for p in paths:
            if p.is_dir():
                for q in sorted(p.rglob("*")):
                    if q.is_file() and q.suffix.lower() in IMAGE_SUFFIX:
                        out.append(q)
            elif p.is_file():
                if p.suffix.lower() in IMAGE_SUFFIX:
                    out.append(p)
        return out

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
        sims = gallery_emb @ q
        order = np.argsort(-sims)
        topk = min(args.topk, sims.shape[0])
        best_i = int(order[0])
        best_sim = float(sims[best_i])
        pred = str(gallery_labels[best_i])
        if best_sim < args.threshold:
            pred = "unknown"

        line = {
            "image": str(img_path),
            "prediction": pred,
            "best_similarity": best_sim,
            "threshold": args.threshold,
        }
        if topk > 1:
            line["top_matches"] = [
                {"identity": str(gallery_labels[int(order[j])]), "similarity": float(sims[int(order[j])])}
                for j in range(topk)
            ]
        print(json.dumps(line, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
