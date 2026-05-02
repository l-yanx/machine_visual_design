"""Normal estimation and orientation for point cloud."""

import open3d as o3d
import numpy as np


def estimate_normals(pcd, radius=0.02, max_nn=30):
    """Estimate normals using local neighborhood search."""
    if not pcd.has_normals():
        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=max_nn)
        )
    return pcd


def orient_normals_towards_center(pcd):
    """Orient normals consistently towards the bounding box center."""
    if not pcd.has_normals():
        raise ValueError("Point cloud must have normals before orientation.")
    center = pcd.get_center()
    normals = np.asarray(pcd.normals)
    points = np.asarray(pcd.points)
    vectors_to_center = center - points
    dots = np.sum(normals * vectors_to_center, axis=1)
    normals[dots < 0] *= -1.0
    pcd.normals = o3d.utility.Vector3dVector(normals)
    return pcd


def estimate_and_orient_normals(pcd, radius=0.02, max_nn=30):
    """Full normal estimation pipeline."""
    pcd = estimate_normals(pcd, radius=radius, max_nn=max_nn)
    pcd = orient_normals_towards_center(pcd)
    return pcd
