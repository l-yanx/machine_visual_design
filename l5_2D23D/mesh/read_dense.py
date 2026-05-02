"""Read and inspect the V1 dense point cloud."""

import open3d as o3d
import numpy as np
import os


def read_dense_ply(ply_path):
    """Read dense.ply and return point cloud with inspection info."""
    if not os.path.exists(ply_path):
        raise FileNotFoundError(f"Dense PLY not found: {ply_path}")

    pcd = o3d.io.read_point_cloud(ply_path)
    pts = np.asarray(pcd.points)
    colors = np.asarray(pcd.colors) if pcd.has_colors() else None

    info = {
        "path": ply_path,
        "num_points": len(pts),
        "has_colors": pcd.has_colors(),
        "has_normals": pcd.has_normals(),
        "bounds_min": pts.min(axis=0).tolist(),
        "bounds_max": pts.max(axis=0).tolist(),
        "bounds_center": pts.mean(axis=0).tolist(),
    }
    return pcd, info
