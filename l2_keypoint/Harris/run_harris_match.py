#!/usr/bin/env python3
"""Harris 角点检测 + 仿射得到 B + 独立检测 + 邻域直方图描述子相似度匹配与可视化。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

from corner_descriptors import build_corner_descriptors
from harris_corner import detect_harris_corners
from image_transform import synthesize_b
from match_corners import match_by_descriptor_similarity

# imwrite 依赖扩展名选择编码器；无扩展名或未知后缀时视为「输出目录」
_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"})


def normalize_image_output_path(p: Path) -> Path:
    if p.suffix.lower() in _IMAGE_SUFFIXES:
        return p
    if p.exists() and p.is_dir():
        return p / "harris_match_out.png"
    return p / "harris_match_out.png"


def load_image(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"无法读取图像: {path}")
    return img


def draw_side_by_side_matches(
    img_a_bgr: np.ndarray,
    img_b_bgr: np.ndarray,
    pts_a: np.ndarray,
    pts_b: np.ndarray,
    matches: list[tuple[int, int]],
    radius: int = 4,
) -> np.ndarray:
    ha, wa = img_a_bgr.shape[:2]
    hb, wb = img_b_bgr.shape[:2]
    out_h = max(ha, hb)
    wa2, wb2 = wa, wb
    canvas = np.zeros((out_h, wa2 + wb2, 3), dtype=np.uint8)
    canvas[:ha, :wa2] = img_a_bgr
    canvas[:hb, wa2 : wa2 + wb2] = img_b_bgr

    rng = np.random.default_rng(42)
    for ia, ib in matches:
        color = tuple(int(x) for x in rng.integers(40, 255, size=3))
        pa = (int(round(pts_a[ia, 0])), int(round(pts_a[ia, 1])))
        pb = (int(round(pts_b[ib, 0]) + wa2), int(round(pts_b[ib, 1])))
        cv2.line(canvas, pa, pb, color, 1, lineType=cv2.LINE_AA)
        cv2.circle(canvas, pa, radius, color, 1, lineType=cv2.LINE_AA)
        cv2.circle(canvas, pb, radius, color, 1, lineType=cv2.LINE_AA)

    # 未匹配角点用灰色小圆标出
    matched_a = {m[0] for m in matches}
    matched_b = {m[1] for m in matches}
    gray = (180, 180, 180)
    for i in range(len(pts_a)):
        if i not in matched_a:
            p = (int(round(pts_a[i, 0])), int(round(pts_a[i, 1])))
            cv2.circle(canvas, p, max(1, radius - 1), gray, 1, lineType=cv2.LINE_AA)
    for j in range(len(pts_b)):
        if j not in matched_b:
            p = (int(round(pts_b[j, 0]) + wa2), int(round(pts_b[j, 1])))
            cv2.circle(canvas, p, max(1, radius - 1), gray, 1, lineType=cv2.LINE_AA)

    return canvas


def main() -> int:
    root = Path(__file__).resolve().parent
    default_out = root / "result"

    parser = argparse.ArgumentParser(
        description="Harris 角点 + 仿射得 B + 邻域直方图描述子匹配可视化"
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=None,
        help="输入图像路径（省略则使用内置棋盘测试图）",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出拼接图文件路径，需含扩展名如 .png；若写目录或无扩展名则保存为该目录下 harris_match_out.png",
    )
    parser.add_argument(
        "--result-dir",
        type=Path,
        default=default_out,
        help=f"结果目录（默认 {default_out}）",
    )
    parser.add_argument("--seed", type=int, default=None, help="随机种子（控制旋转/平移/模糊）")
    parser.add_argument(
        "--ratio",
        type=float,
        default=0.75,
        help="Lowe 距离比阈值：最近距离需小于该值×次近距离（越小越严）",
    )
    parser.add_argument(
        "--patch-radius",
        type=int,
        default=15,
        help="角点邻域半边长（像素），邻域为 (2r+1)×(2r+1)",
    )
    parser.add_argument(
        "--no-mutual",
        action="store_true",
        help="关闭互最近邻过滤（仅距离比）",
    )
    harris = parser.add_argument_group("Harris 角点（goodFeaturesToTrack）")
    harris.add_argument(
        "--quality-level",
        type=float,
        default=0.01,
        help="相对最强角点的比例阈值，越小保留越多弱角点（面部平滑区可试 0.002～0.005）",
    )
    harris.add_argument(
        "--min-distance",
        type=float,
        default=8.0,
        help="角点间最小像素距离，越小越密（可试 4～6）",
    )
    harris.add_argument(
        "--max-corners",
        type=int,
        default=800,
        help="最多返回角点个数上限",
    )
    harris.add_argument(
        "--block-size",
        type=int,
        default=3,
        help="求导邻域边长（奇数），略增大可略平滑噪声",
    )
    args = parser.parse_args()

    args.result_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output
    if out_path is None:
        out_path = args.result_dir / "harris_match_out.png"
    else:
        out_path = normalize_image_output_path(out_path.resolve())

    rng = np.random.default_rng(args.seed)

    if args.input is not None:
        img_a = load_image(args.input)
    else:
        # 内置棋盘图，便于无参试跑
        block = 40
        n = 12
        board = np.zeros((block * n, block * n), dtype=np.uint8)
        for i in range(n):
            for j in range(n):
                if (i + j) % 2 == 0:
                    y0, y1 = i * block, (i + 1) * block
                    x0, x1 = j * block, (j + 1) * block
                    board[y0:y1, x0:x1] = 255
        img_a = cv2.cvtColor(board, cv2.COLOR_GRAY2BGR)

    img_b, _ = synthesize_b(img_a, rng=rng)

    gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)

    hk = dict(
        max_corners=args.max_corners,
        quality_level=args.quality_level,
        min_distance=args.min_distance,
        block_size=args.block_size,
    )
    pts_a = detect_harris_corners(gray_a, **hk)
    pts_b = detect_harris_corners(gray_b, **hk)

    desc_a, idx_a = build_corner_descriptors(gray_a, pts_a, patch_radius=args.patch_radius)
    desc_b, idx_b = build_corner_descriptors(gray_b, pts_b, patch_radius=args.patch_radius)

    matches = match_by_descriptor_similarity(
        desc_a,
        desc_b,
        idx_a,
        idx_b,
        ratio=args.ratio,
        mutual=not args.no_mutual,
    )

    vis = draw_side_by_side_matches(img_a, img_b, pts_a, pts_b, matches)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(out_path), vis)
    if not ok:
        print(f"写入失败: {out_path}", file=sys.stderr)
        return 1

    print(f"已保存: {out_path}")
    print(f"角点数 A={len(pts_a)}, B={len(pts_b)}, 匹配数={len(matches)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
