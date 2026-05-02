"""Utility functions for point cloud cleaning pipeline."""

import numpy as np
import open3d as o3d


def estimate_median_nn_distance(pcd, sample_size=5000):
    """Estimate median nearest-neighbor distance from a random sample of points."""
    pts = np.asarray(pcd.points)
    n = len(pts)
    if n < 2:
        return 0.0
    if n > sample_size:
        rng = np.random.default_rng(42)
        idx = rng.choice(n, sample_size, replace=False)
        pts = pts[idx]
    pcd_sample = o3d.geometry.PointCloud()
    pcd_sample.points = o3d.utility.Vector3dVector(pts)
    kdtree = o3d.geometry.KDTreeFlann(pcd_sample)
    distances = []
    for i in range(len(pts)):
        _, _, dist = kdtree.search_knn_vector_3d(pcd_sample.points[i], 2)
        if len(dist) > 1:
            distances.append(np.sqrt(dist[1]))
    if not distances:
        return 0.0
    return float(np.median(distances))


def compute_nn_distance_stats(pcd, sample_size=5000):
    """Compute nearest-neighbor distance statistics (mean, median, std, min, max)."""
    pts = np.asarray(pcd.points)
    n = len(pts)
    if n < 2:
        return {"mean": 0.0, "median": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    if n > sample_size:
        rng = np.random.default_rng(42)
        idx = rng.choice(n, sample_size, replace=False)
        pts = pts[idx]
    pcd_sample = o3d.geometry.PointCloud()
    pcd_sample.points = o3d.utility.Vector3dVector(pts)
    kdtree = o3d.geometry.KDTreeFlann(pcd_sample)
    distances = []
    for i in range(len(pts)):
        _, _, dist = kdtree.search_knn_vector_3d(pcd_sample.points[i], 2)
        if len(dist) > 1:
            distances.append(np.sqrt(dist[1]))
    if not distances:
        return {"mean": 0.0, "median": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    d = np.array(distances)
    return {
        "mean": float(np.mean(d)),
        "median": float(np.median(d)),
        "std": float(np.std(d)),
        "min": float(np.min(d)),
        "max": float(np.max(d)),
    }
