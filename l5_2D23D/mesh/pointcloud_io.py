"""Point cloud loading and basic validation."""

import os
import numpy as np
import open3d as o3d


def load_point_cloud(path):
    """Load a point cloud file and return (pcd, info_dict).

    Raises FileNotFoundError if the path does not exist.
    Raises ValueError if the file cannot be read or has zero points.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Point cloud file not found: {path}")

    pcd = o3d.io.read_point_cloud(path)
    pts = np.asarray(pcd.points)

    if len(pts) == 0:
        raise ValueError(f"Point cloud at {path} has zero points")

    has_colors = pcd.has_colors()
    has_normals = pcd.has_normals()

    nan_count = int(np.sum(np.isnan(pts)))
    inf_count = int(np.sum(np.isinf(pts)))

    bounds_min = np.min(pts, axis=0) if len(pts) > 0 else np.zeros(3)
    bounds_max = np.max(pts, axis=0) if len(pts) > 0 else np.zeros(3)

    info = {
        "path": os.path.abspath(path),
        "num_points": len(pts),
        "has_colors": has_colors,
        "has_normals": has_normals,
        "nan_count": nan_count,
        "inf_count": inf_count,
        "bounds_min": bounds_min,
        "bounds_max": bounds_max,
    }
    return pcd, info
