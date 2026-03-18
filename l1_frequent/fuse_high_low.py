#!/usr/bin/env python3
import argparse
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class ResizeSpec:
    width: int
    height: int


def _imread_color(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Failed to read image: {path}")
    return img


def _to_float01(img_bgr_u8: np.ndarray) -> np.ndarray:
    if img_bgr_u8.dtype != np.uint8:
        raise ValueError(f"Expected uint8 image, got {img_bgr_u8.dtype}")
    return img_bgr_u8.astype(np.float32) / 255.0


def _to_u8(img_float01: np.ndarray) -> np.ndarray:
    img = np.clip(img_float01, 0.0, 1.0)
    return (img * 255.0 + 0.5).astype(np.uint8)


def _fmt_float_for_name(x: float) -> str:
    # short, human-readable, no trailing zeros like 10.0 -> 10
    return format(float(x), "g")


def _parse_resize_spec(s: str | None, a_shape_hw: tuple[int, int], b_shape_hw: tuple[int, int]) -> ResizeSpec:
    if s is None or s.lower() == "auto":
        # pick the larger area image as target, preserves more detail by default
        ah, aw = a_shape_hw
        bh, bw = b_shape_hw
        if aw * ah >= bw * bh:
            return ResizeSpec(width=aw, height=ah)
        return ResizeSpec(width=bw, height=bh)

    if "x" not in s:
        raise ValueError("resize must be like 1280x720 or 'auto'")
    w_s, h_s = s.lower().split("x", 1)
    w = int(w_s)
    h = int(h_s)
    if w <= 0 or h <= 0:
        raise ValueError("resize width/height must be positive")
    return ResizeSpec(width=w, height=h)


def _resize(img: np.ndarray, spec: ResizeSpec, interpolation: str) -> np.ndarray:
    interp = {
        "linear": cv2.INTER_LINEAR,
        "area": cv2.INTER_AREA,
        "cubic": cv2.INTER_CUBIC,
        "lanczos": cv2.INTER_LANCZOS4,
    }.get(interpolation)
    if interp is None:
        raise ValueError("interpolation must be one of: linear, area, cubic, lanczos")
    return cv2.resize(img, (spec.width, spec.height), interpolation=interp)


def gaussian_lowpass(img_float01: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    return cv2.GaussianBlur(img_float01, ksize=(0, 0), sigmaX=sigma, sigmaY=sigma, borderType=cv2.BORDER_REFLECT)


def highpass_from(img_float01: np.ndarray, sigma: float) -> np.ndarray:
    low = gaussian_lowpass(img_float01, sigma=sigma)
    return img_float01 - low


def fuse_high_low(
    a_float01: np.ndarray,
    b_float01: np.ndarray,
    sigma_low: float,
    sigma_high: float,
    high_gain: float,
    b_gain: float,
) -> np.ndarray:
    # low frequency from b
    b_low = gaussian_lowpass(b_float01, sigma=sigma_low)
    # high frequency from a
    a_high = highpass_from(a_float01, sigma=sigma_high)
    return b_low * float(b_gain) + a_high * float(high_gain)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Fuse: keep high frequency from image A, low frequency from image B, then add."
    )
    p.add_argument("--a", required=True, help="Path to image A (keeps high frequency).")
    p.add_argument("--b", required=True, help="Path to image B (keeps low frequency).")
    p.add_argument("--out", required=True, help="Output image path.")
    p.add_argument(
        "--resize",
        default="auto",
        help="Target resolution as WxH like 1280x720, or 'auto' (default: larger-area image).",
    )
    p.add_argument(
        "--interp",
        default="area",
        choices=["linear", "area", "cubic", "lanczos"],
        help="Resize interpolation (default: area).",
    )
    p.add_argument(
        "--sigma-low",
        type=float,
        default=5.0,
        help="Gaussian sigma for low-pass on B (default: 5.0). Bigger -> smoother/low-frequency.",
    )
    p.add_argument(
        "--sigma-high",
        type=float,
        default=2.0,
        help="Gaussian sigma to define high-pass on A via A - blur(A) (default: 2.0).",
    )
    p.add_argument(
        "--high-gain",
        type=float,
        default=1.0,
        help="Gain applied to A's high-frequency (default: 1.0).",
    )
    p.add_argument(
        "--b-gain",
        type=float,
        default=1.0,
        help="Gain applied to B's low-frequency base (default: 1.0). Use <1 to suppress B.",
    )
    p.add_argument(
        "--save-f32",
        action="store_true",
        help="Also save a .npy float32 output next to --out (useful for debugging).",
    )

    args = p.parse_args()

    img_a_u8 = _imread_color(args.a)
    img_b_u8 = _imread_color(args.b)

    spec = _parse_resize_spec(
        args.resize,
        a_shape_hw=(img_a_u8.shape[0], img_a_u8.shape[1]),
        b_shape_hw=(img_b_u8.shape[0], img_b_u8.shape[1]),
    )

    img_a_u8 = _resize(img_a_u8, spec, interpolation=args.interp)
    img_b_u8 = _resize(img_b_u8, spec, interpolation=args.interp)

    a = _to_float01(img_a_u8)
    b = _to_float01(img_b_u8)

    fused = fuse_high_low(
        a,
        b,
        sigma_low=args.sigma_low,
        sigma_high=args.sigma_high,
        high_gain=args.high_gain,
        b_gain=args.b_gain,
    )

    out_path = Path(args.out)
    if out_path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"):
        # 若 --out 是目录或没有扩展名，则在该路径下按参数写入 out_*.jpg
        out_name = (
            f"out_{_fmt_float_for_name(args.sigma_low)}_"
            f"{_fmt_float_for_name(args.sigma_high)}_"
            f"{_fmt_float_for_name(args.high_gain)}_"
            f"{_fmt_float_for_name(args.b_gain)}.jpg"
        )
        out_path = out_path / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(out_path), _to_u8(fused))
    if not ok:
        raise RuntimeError(f"Failed to write output image: {out_path}")

    if args.save_f32:
        np.save(str(out_path.with_suffix(out_path.suffix + ".npy")), fused.astype(np.float32))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
