#!/usr/bin/env python3
"""A->B 变换、独立 ORB 检测、Ratio+RANSAC 匹配、拼接连线可视化。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

from image_transformer import transform_image
from orb_detector import detect_orb_features, draw_keypoints

_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"})


def normalize_output_path(p: Path) -> Path:
    if p.suffix.lower() in _IMAGE_SUFFIXES:
        return p
    return p / "orb_match_stitch_ransac_out.png"


def load_image(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"cannot read image: {path}")
    return img


def ratio_match_indices(desc_a: np.ndarray, desc_b: np.ndarray, ratio: float) -> list[tuple[int, int]]:
    """ORB 二进制描述子做 KNN + ratio，返回 (idx_a, idx_b)。"""
    if desc_a.shape[0] == 0 or desc_b.shape[0] == 0:
        return []
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    knn = bf.knnMatch(desc_a, desc_b, k=2)
    matches: list[tuple[int, int]] = []
    for pair in knn:
        if len(pair) < 2:
            continue
        m0, m1 = pair
        if m0.distance < ratio * (m1.distance + 1e-8):
            matches.append((m0.queryIdx, m0.trainIdx))
    return matches


def ransac_filter_matches(
    pts_a: np.ndarray,
    pts_b: np.ndarray,
    raw_matches: list[tuple[int, int]],
    reproj_thresh: float = 3.0,
) -> list[tuple[int, int]]:
    """对 ratio 初始匹配执行 RANSAC（homography）并返回内点。"""
    if len(raw_matches) < 4:
        return []

    src = np.array([pts_a[i] for i, _ in raw_matches], dtype=np.float32)
    dst = np.array([pts_b[j] for _, j in raw_matches], dtype=np.float32)
    _, mask = cv2.findHomography(src, dst, cv2.RANSAC, ransacReprojThreshold=reproj_thresh)
    if mask is None:
        return []

    inliers: list[tuple[int, int]] = []
    for keep, pair in zip(mask.ravel().astype(bool), raw_matches):
        if keep:
            inliers.append(pair)
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

    rng = np.random.default_rng(84)
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
    parser = argparse.ArgumentParser(description="ORB pipeline: ratio+RANSAC match and stitch")
    parser.add_argument("input", type=Path, help="input image A path")
    parser.add_argument("--result-dir", type=Path, default=default_result_dir, help="result directory")
    parser.add_argument("-o", "--output", type=Path, default=None, help="final stitched image path")

    parser.add_argument("--angle", type=float, default=12.0, help="rotation angle for A->B")
    parser.add_argument("--tx", type=float, default=20.0, help="x translation for A->B")
    parser.add_argument("--ty", type=float, default=12.0, help="y translation for A->B")
    parser.add_argument("--perspective", type=float, default=0.02, help="perspective strength")
    parser.add_argument("--blur-ksize", type=int, default=5, help="gaussian blur kernel size")
    parser.add_argument("--blur-sigma", type=float, default=0.0, help="gaussian blur sigma")

    parser.add_argument("--nfeatures", type=int, default=1200, help="number of ORB keypoints")
    parser.add_argument("--scale-factor", type=float, default=1.2, help="ORB scale factor")
    parser.add_argument("--nlevels", type=int, default=8, help="ORB pyramid levels")
    parser.add_argument("--fast-threshold", type=int, default=20, help="FAST threshold inside ORB")
    parser.add_argument("--ratio", type=float, default=0.75, help="Lowe ratio threshold")
    parser.add_argument("--ransac-thresh", type=float, default=3.0, help="RANSAC reprojection threshold")
    args = parser.parse_args()

    args.result_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output if args.output is not None else args.result_dir / "orb_match_stitch_ransac_out.png"
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

    pts_a, desc_a = detect_orb_features(
        gray_a,
        nfeatures=args.nfeatures,
        scale_factor=args.scale_factor,
        nlevels=args.nlevels,
        fast_threshold=args.fast_threshold,
    )
    pts_b, desc_b = detect_orb_features(
        gray_b,
        nfeatures=args.nfeatures,
        scale_factor=args.scale_factor,
        nlevels=args.nlevels,
        fast_threshold=args.fast_threshold,
    )

    a1 = draw_keypoints(img_a, pts_a)
    b1 = draw_keypoints(img_b, pts_b)
    a1_path = args.result_dir / "a1_orb_ransac.png"
    b1_path = args.result_dir / "b1_orb_ransac.png"
    cv2.imwrite(str(a1_path), a1)
    cv2.imwrite(str(b1_path), b1)

    raw_matches = ratio_match_indices(desc_a, desc_b, ratio=args.ratio)
    inlier_matches = ransac_filter_matches(
        pts_a,
        pts_b,
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
    print(f"keypoints A={len(pts_a)}, B={len(pts_b)}")
    print(f"ratio matches={len(raw_matches)}, ransac inliers={len(inlier_matches)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
