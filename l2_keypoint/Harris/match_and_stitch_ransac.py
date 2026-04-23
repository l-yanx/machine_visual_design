#!/usr/bin/env python3
"""A->B 变换、独立 Harris 角点、Ratio+RANSAC 匹配、拼接连线可视化。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

from harris_detector import detect_harris_corners, draw_corners
from image_transformer import transform_image

_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"})


def normalize_output_path(p: Path) -> Path:
    if p.suffix.lower() in _IMAGE_SUFFIXES:
        return p
    return p / "match_stitch_ransac_out.png"


def load_image(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"cannot read image: {path}")
    return img


def build_patch_descriptors(
    gray: np.ndarray,
    pts: np.ndarray,
    patch_radius: int = 15,
    intensity_bins: int = 16,
    orientation_bins: int = 8,
) -> tuple[np.ndarray, np.ndarray]:
    """角点邻域描述子：灰度直方图 + 梯度方向直方图（L2 归一化）。"""
    if pts.size == 0:
        return np.zeros((0, intensity_bins + orientation_bins), dtype=np.float32), np.zeros(
            (0,), dtype=np.int32
        )

    h, w = gray.shape[:2]
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    r = patch_radius
    desc_list: list[np.ndarray] = []
    valid_idx: list[int] = []

    for i in range(pts.shape[0]):
        x = int(round(float(pts[i, 0])))
        y = int(round(float(pts[i, 1])))
        if x - r < 0 or x + r >= w or y - r < 0 or y + r >= h:
            continue

        patch = gray[y - r : y + r + 1, x - r : x + r + 1]
        px = gx[y - r : y + r + 1, x - r : x + r + 1]
        py = gy[y - r : y + r + 1, x - r : x + r + 1]

        hist_i, _ = np.histogram(patch, bins=intensity_bins, range=(0, 256))
        hist_i = hist_i.astype(np.float64)
        hist_i /= float(hist_i.sum()) + 1e-8

        mag = np.sqrt(px * px + py * py)
        ang = np.mod(np.arctan2(py, px), np.pi)
        bins = np.clip((ang / np.pi * orientation_bins).astype(np.int32), 0, orientation_bins - 1)
        hist_o = np.bincount(
            bins.ravel(),
            weights=mag.ravel(),
            minlength=orientation_bins,
        ).astype(np.float64)
        hist_o /= float(hist_o.sum()) + 1e-8

        v = np.concatenate([hist_i, hist_o]).astype(np.float64)
        n = np.linalg.norm(v)
        if n < 1e-8:
            continue
        v /= n
        desc_list.append(v.astype(np.float32))
        valid_idx.append(i)

    if not desc_list:
        return np.zeros((0, intensity_bins + orientation_bins), dtype=np.float32), np.zeros(
            (0,), dtype=np.int32
        )
    return np.stack(desc_list, axis=0), np.array(valid_idx, dtype=np.int32)


def ratio_match_indices(desc_a: np.ndarray, desc_b: np.ndarray, ratio: float) -> list[tuple[int, int]]:
    """只做 ratio test，返回 (desc_a_idx, desc_b_idx)。"""
    if desc_a.shape[0] == 0 or desc_b.shape[0] == 0:
        return []

    dist = np.sqrt(np.maximum(0.0, 2.0 - 2.0 * (desc_a @ desc_b.T)))
    matches: list[tuple[int, int]] = []
    for i in range(dist.shape[0]):
        row = dist[i]
        order = np.argsort(row)
        if len(order) < 2:
            continue
        j0 = int(order[0])
        j1 = int(order[1])
        d0 = float(row[j0])
        d1 = float(row[j1])
        if d0 < ratio * (d1 + 1e-8):
            matches.append((i, j0))
    return matches


def ransac_filter_matches(
    pts_a: np.ndarray,
    pts_b: np.ndarray,
    idx_a: np.ndarray,
    idx_b: np.ndarray,
    raw_matches: list[tuple[int, int]],
    reproj_thresh: float = 3.0,
) -> list[tuple[int, int]]:
    """对 ratio 初始匹配执行 RANSAC（homography），返回内点匹配。"""
    if len(raw_matches) < 4:
        return []

    src = np.array([pts_a[int(idx_a[i])] for i, _ in raw_matches], dtype=np.float32)
    dst = np.array([pts_b[int(idx_b[j])] for _, j in raw_matches], dtype=np.float32)
    _, mask = cv2.findHomography(src, dst, cv2.RANSAC, ransacReprojThreshold=reproj_thresh)
    if mask is None:
        return []

    inliers: list[tuple[int, int]] = []
    m = mask.ravel().astype(bool)
    for keep, (i, j) in zip(m, raw_matches):
        if keep:
            inliers.append((int(idx_a[i]), int(idx_b[j])))
    return inliers


def stitch_and_draw_matches(
    a1_bgr: np.ndarray,
    b1_bgr: np.ndarray,
    pts_a: np.ndarray,
    pts_b: np.ndarray,
    matches: list[tuple[int, int]],
    radius: int = 4,
) -> np.ndarray:
    h1, w1 = a1_bgr.shape[:2]
    h2, w2 = b1_bgr.shape[:2]
    out_h = max(h1, h2)
    canvas = np.zeros((out_h, w1 + w2, 3), dtype=np.uint8)
    canvas[:h1, :w1] = a1_bgr
    canvas[:h2, w1 : w1 + w2] = b1_bgr

    rng = np.random.default_rng(21)
    for ia, ib in matches:
        color = tuple(int(x) for x in rng.integers(40, 255, size=3))
        pa = (int(round(float(pts_a[ia, 0]))), int(round(float(pts_a[ia, 1]))))
        pb = (int(round(float(pts_b[ib, 0])) + w1), int(round(float(pts_b[ib, 1]))))
        cv2.line(canvas, pa, pb, color, 1, lineType=cv2.LINE_AA)
        cv2.circle(canvas, pa, radius, color, 1, lineType=cv2.LINE_AA)
        cv2.circle(canvas, pb, radius, color, 1, lineType=cv2.LINE_AA)
    return canvas


def main() -> int:
    root = Path(__file__).resolve().parent
    default_result_dir = root / "result"
    parser = argparse.ArgumentParser(description="Harris pipeline: ratio+RANSAC match and stitch")
    parser.add_argument("input", type=Path, help="input image A path")
    parser.add_argument("--result-dir", type=Path, default=default_result_dir, help="result directory")
    parser.add_argument("-o", "--output", type=Path, default=None, help="final stitched image path")

    parser.add_argument("--angle", type=float, default=12.0, help="rotation angle for A->B")
    parser.add_argument("--tx", type=float, default=20.0, help="x translation for A->B")
    parser.add_argument("--ty", type=float, default=12.0, help="y translation for A->B")
    parser.add_argument("--perspective", type=float, default=0.02, help="perspective strength")
    parser.add_argument("--blur-ksize", type=int, default=5, help="gaussian blur kernel size")
    parser.add_argument("--blur-sigma", type=float, default=0.0, help="gaussian blur sigma")

    parser.add_argument("--max-corners", type=int, default=1200, help="max number of Harris corners")
    parser.add_argument("--quality-level", type=float, default=0.005, help="corner quality threshold")
    parser.add_argument("--min-distance", type=float, default=6.0, help="minimum corner distance")
    parser.add_argument("--block-size", type=int, default=3, help="block size for Harris")
    parser.add_argument("--harris-k", type=float, default=0.04, help="Harris response k")

    parser.add_argument("--patch-radius", type=int, default=15, help="descriptor patch radius")
    parser.add_argument("--ratio", type=float, default=0.75, help="Lowe ratio threshold")
    parser.add_argument("--ransac-thresh", type=float, default=3.0, help="RANSAC reprojection threshold")
    args = parser.parse_args()

    args.result_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output if args.output is not None else args.result_dir / "match_stitch_ransac_out.png"
    out_path = normalize_output_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img_a = load_image(args.input)
    img_b = transform_image(
        img_a,
        angle_deg=args.angle,
        tx_px=args.tx,
        ty_px=args.ty,
        perspective=args.perspective,
        blur_ksize=args.blur_ksize,
        blur_sigma=args.blur_sigma,
    )
    gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)

    harris_kwargs = dict(
        max_corners=args.max_corners,
        quality_level=args.quality_level,
        min_distance=args.min_distance,
        block_size=args.block_size,
        k=args.harris_k,
    )
    pts_a = detect_harris_corners(gray_a, **harris_kwargs)
    pts_b = detect_harris_corners(gray_b, **harris_kwargs)
    a1 = draw_corners(img_a, pts_a)
    b1 = draw_corners(img_b, pts_b)

    a1_path = args.result_dir / "a1_corners_ransac.png"
    b1_path = args.result_dir / "b1_corners_ransac.png"
    cv2.imwrite(str(a1_path), a1)
    cv2.imwrite(str(b1_path), b1)

    desc_a, idx_a = build_patch_descriptors(gray_a, pts_a, patch_radius=args.patch_radius)
    desc_b, idx_b = build_patch_descriptors(gray_b, pts_b, patch_radius=args.patch_radius)
    raw_matches = ratio_match_indices(desc_a, desc_b, ratio=args.ratio)
    inlier_matches = ransac_filter_matches(
        pts_a,
        pts_b,
        idx_a,
        idx_b,
        raw_matches,
        reproj_thresh=args.ransac_thresh,
    )

    stitched = stitch_and_draw_matches(a1, b1, pts_a, pts_b, inlier_matches)
    ok = cv2.imwrite(str(out_path), stitched)
    if not ok:
        print(f"failed to write output: {out_path}", file=sys.stderr)
        return 1

    print(f"saved a1: {a1_path}")
    print(f"saved b1: {b1_path}")
    print(f"saved stitched: {out_path}")
    print(f"corners A={len(pts_a)}, B={len(pts_b)}")
    print(f"ratio matches={len(raw_matches)}, ransac inliers={len(inlier_matches)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
