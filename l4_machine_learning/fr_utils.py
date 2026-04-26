"""Shared InsightFace helpers: app creation, face selection, alignment paths."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List, Sequence, Tuple

import cv2
import numpy as np

# InsightFace imports are deferred in create_face_app to give clearer errors if missing.


def create_face_app(
    *,
    ctx_id: int = 0,
    model_name: str = "buffalo_l",
    model_root: str | Path | None = None,
    det_size: Tuple[int, int] = (640, 640),
    det_thresh: float = 0.5,
) -> Any:
    """Build FaceAnalysis with GPU (ctx_id>=0) or CPU (ctx_id=-1)."""
    from insightface.app import FaceAnalysis

    root = str(model_root) if model_root is not None else str(Path(__file__).resolve().parent / "models")
    os.makedirs(root, exist_ok=True)

    if ctx_id >= 0:
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    else:
        providers = ["CPUExecutionProvider"]

    # providers 经 **kwargs 传入底层 ONNX Runtime；仅加载检测+识别以节省显存与时间
    app = FaceAnalysis(
        name=model_name,
        root=root,
        providers=providers,
        allowed_modules=["detection", "recognition"],
    )
    app.prepare(ctx_id=ctx_id, det_size=det_size, det_thresh=det_thresh)
    return app


def bbox_area(face: Any) -> float:
    x1, y1, x2, y2 = face.bbox.astype(float)
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def pick_primary_face(faces: Sequence[Any]) -> Any | None:
    """Choose the most confident face; tie-break by largest box area."""
    if not faces:
        return None
    scored: List[Tuple[float, float, Any]] = []
    for f in faces:
        area = bbox_area(f)
        det_score = float(getattr(f, "det_score", 0.0) or 0.0)
        scored.append((det_score, area, f))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return scored[0][2]


def align_face_bgr(img_bgr: np.ndarray, face: Any, image_size: int = 112) -> np.ndarray:
    from insightface.utils import face_align

    return face_align.norm_crop(img_bgr, landmark=face.kps, image_size=image_size, mode="arcface")


def cosine_top1(
    query: np.ndarray, gallery: np.ndarray
) -> Tuple[int, float]:
    """Assume L2-normalized rows; returns (index, cosine similarity)."""
    q = query.reshape(-1).astype(np.float32)
    g = gallery.astype(np.float32)
    sims = g @ q
    idx = int(np.argmax(sims))
    return idx, float(sims[idx])


def ensure_l2(vec: np.ndarray) -> np.ndarray:
    v = vec.reshape(-1).astype(np.float32)
    n = float(np.linalg.norm(v))
    if n > 1e-12:
        v /= n
    return v
