#!/usr/bin/env python3
"""Detect faces, align, save to aligned_dataset/, extract ArcFace embeddings into embedding/gallery.npz."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

from fr_utils import align_face_bgr, create_face_app, ensure_l2, pick_primary_face

IMAGE_SUFFIX = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def list_images(folder: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIX:
            out.append(p)
    return out


def rel_str(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build aligned faces + embedding gallery from dataset/")
    root = Path(__file__).resolve().parent
    parser.add_argument("--dataset", type=Path, default=root / "dataset", help="Root with one subfolder per identity")
    parser.add_argument("--aligned", type=Path, default=root / "aligned_dataset", help="Output aligned crops")
    parser.add_argument("--embedding-dir", type=Path, default=root / "embedding", help="Output directory for .npz")
    parser.add_argument("--gallery-name", type=str, default="gallery.npz", help="Gallery filename under embedding-dir")
    parser.add_argument("--model", type=str, default="buffalo_l", help="InsightFace model pack name")
    parser.add_argument("--model-root", type=Path, default=root / "models", help="Directory to store ONNX models")
    parser.add_argument("--ctx-id", type=int, default=0, help="GPU id, or -1 for CPU")
    parser.add_argument("--det-size", type=int, nargs=2, default=[640, 640], metavar=("W", "H"))
    parser.add_argument("--det-thresh", type=float, default=0.5)
    args = parser.parse_args()

    dataset: Path = args.dataset
    aligned_root: Path = args.aligned
    emb_dir: Path = args.embedding_dir
    emb_dir.mkdir(parents=True, exist_ok=True)
    aligned_root.mkdir(parents=True, exist_ok=True)

    if not dataset.is_dir():
        print(f"Dataset not found: {dataset}", file=sys.stderr)
        return 1

    app = create_face_app(
        ctx_id=args.ctx_id,
        model_name=args.model,
        model_root=args.model_root,
        det_size=(int(args.det_size[0]), int(args.det_size[1])),
        det_thresh=args.det_thresh,
    )

    records: list[dict] = []
    embeddings: list[np.ndarray] = []
    labels: list[str] = []

    id_dirs = [p for p in sorted(dataset.iterdir()) if p.is_dir()]
    if not id_dirs:
        print(f"No identity subfolders under {dataset}", file=sys.stderr)
        return 1

    for id_path in id_dirs:
        identity = id_path.name
        out_id_dir = aligned_root / identity
        out_id_dir.mkdir(parents=True, exist_ok=True)

        images = list_images(id_path)
        counter = 0
        for img_path in tqdm(images, desc=f"{identity}", unit="img"):
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            faces = app.get(img)
            face = pick_primary_face(faces)
            if face is None:
                continue

            aligned = align_face_bgr(img, face, image_size=112)
            counter += 1
            out_name = f"{counter:03d}.jpg"
            out_path = out_id_dir / out_name
            cv2.imwrite(str(out_path), aligned)

            emb = np.asarray(face.embedding, dtype=np.float32).reshape(-1)
            emb = ensure_l2(emb)
            embeddings.append(emb)
            labels.append(identity)
            records.append(
                {
                    "identity": identity,
                    "source_image": rel_str(img_path, root),
                    "aligned_image": rel_str(out_path, root),
                    "det_score": float(getattr(face, "det_score", 0.0) or 0.0),
                }
            )

    if not embeddings:
        print("No faces detected in dataset; nothing saved.", file=sys.stderr)
        return 1

    gallery_path = emb_dir / args.gallery_name
    E = np.stack(embeddings, axis=0)
    L = np.array(labels, dtype=object)
    meta_path = emb_dir / "gallery_meta.json"
    np.savez_compressed(
        gallery_path,
        embeddings=E.astype(np.float32),
        labels=L,
    )
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"records": records, "model": args.model, "embedding_dim": int(E.shape[1])}, f, ensure_ascii=False, indent=2)

    print(f"Saved gallery: {gallery_path} ({E.shape[0]} vectors, dim={E.shape[1]})")
    print(f"Aligned images under: {aligned_root}")
    print(f"Metadata: {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
