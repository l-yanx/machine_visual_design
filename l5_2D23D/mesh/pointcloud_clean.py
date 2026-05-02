"""Point cloud cleaning: remove NaN/inf, outliers, and downsample."""

import open3d as o3d
import numpy as np


def remove_nan_inf(pcd):
    """Remove points with NaN or infinite coordinates."""
    pts = np.asarray(pcd.points)
    colors = np.asarray(pcd.colors) if pcd.has_colors() else None
    valid = np.isfinite(pts).all(axis=1)
    if not valid.all():
        pcd = pcd.select_by_index(np.where(valid)[0])
    return pcd


def remove_statistical_outliers(pcd, nb_neighbors=20, std_ratio=2.0):
    """Remove statistical outliers."""
    cl, ind = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    return cl


def remove_radius_outliers(pcd, nb_points=16, radius=0.05):
    """Remove radius outliers."""
    cl, ind = pcd.remove_radius_outlier(nb_points=nb_points, radius=radius)
    return cl


def voxel_downsample(pcd, voxel_size=0.005):
    """Downsample point cloud using voxel grid."""
    return pcd.voxel_down_sample(voxel_size)


def clean_dense_pcd(pcd, nb_neighbors=20, std_ratio=2.0, voxel_size=0.005):
    """Full cleaning pipeline."""
    pcd = remove_nan_inf(pcd)
    n_before = len(pcd.points)

    pcd = remove_statistical_outliers(pcd, nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    n_after_stat = len(pcd.points)

    pcd = voxel_downsample(pcd, voxel_size=voxel_size)
    n_after_voxel = len(pcd.points)

    stats = {
        "before_clean": n_before,
        "after_statistical": n_after_stat,
        "after_voxel": n_after_voxel,
    }
    return pcd, stats
