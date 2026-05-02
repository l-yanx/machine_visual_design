"""Point cloud filtering operations: invalid removal, outlier removal, voxel downsample, normal estimation."""

import numpy as np
import open3d as o3d
from mesh.utils import estimate_median_nn_distance


def remove_invalid_points(pcd):
    """Remove points with NaN or inf coordinates. Preserves colors."""
    pts = np.asarray(pcd.points)
    valid = np.isfinite(pts).all(axis=1)
    n_before = len(pts)
    if np.all(valid):
        return pcd, {"before": n_before, "after": n_before, "removed": 0}
    pcd_clean = pcd.select_by_index(np.where(valid)[0])
    n_after = len(pcd_clean.points)
    return pcd_clean, {"before": n_before, "after": n_after, "removed": n_before - n_after}


def remove_duplicate_points(pcd, tol=1e-10):
    """Remove duplicate points (within tolerance). Preserves colors."""
    pts = np.asarray(pcd.points)
    n_before = len(pts)
    _, unique_idx = np.unique(pts.round(decimals=int(-np.log10(tol))), axis=0, return_index=True)
    if len(unique_idx) == n_before:
        return pcd, {"before": n_before, "after": n_before, "removed": 0}
    pcd_unique = pcd.select_by_index(unique_idx)
    n_after = len(pcd_unique.points)
    return pcd_unique, {"before": n_before, "after": n_after, "removed": n_before - n_after}


def apply_statistical_outlier_removal(pcd, nb_neighbors, std_ratio):
    """Remove statistical outliers using Open3D."""
    n_before = len(pcd.points)
    pcd_clean, ind = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    n_after = len(pcd_clean.points)
    return pcd_clean, {"before": n_before, "after": n_after, "removed": n_before - n_after,
                        "nb_neighbors": nb_neighbors, "std_ratio": std_ratio}


def apply_radius_outlier_removal(pcd, radius, min_neighbors):
    """Remove radius outliers using Open3D."""
    n_before = len(pcd.points)
    pcd_clean, ind = pcd.remove_radius_outlier(nb_points=min_neighbors, radius=radius)
    n_after = len(pcd_clean.points)
    return pcd_clean, {"before": n_before, "after": n_after, "removed": n_before - n_after,
                        "radius": radius, "min_neighbors": min_neighbors}


def apply_color_filter(pcd, mode="yellow_background", brightness_min=0, brightness_max=255):
    """Filter points based on color heuristics.

    mode 'yellow_background': removes points that are yellowish (R+G high, B low).
    Returns filtered pcd and stats dict.
    """
    if not pcd.has_colors():
        return pcd, {"before": len(pcd.points), "after": len(pcd.points), "removed": 0,
                      "mode": mode, "note": "no colors, skipped"}

    colors = np.asarray(pcd.colors)
    n_before = len(colors)

    if mode == "yellow_background":
        # Yellow pixels have high R and G, lower B
        r, g, b = colors[:, 0], colors[:, 1], colors[:, 2]
        yellow_mask = (r > 0.5) & (g > 0.4) & (b < 0.5)
        keep = ~yellow_mask
    else:
        keep = np.ones(n_before, dtype=bool)

    if np.all(keep):
        return pcd, {"before": n_before, "after": n_before, "removed": 0, "mode": mode}

    pcd_filtered = pcd.select_by_index(np.where(keep)[0])
    n_after = len(pcd_filtered.points)
    return pcd_filtered, {"before": n_before, "after": n_after, "removed": n_before - n_after,
                           "mode": mode}


def apply_voxel_downsample(pcd, voxel_size):
    """Voxel downsampling to uniformize point density."""
    n_before = len(pcd.points)
    pcd_down = pcd.voxel_down_sample(voxel_size)
    n_after = len(pcd_down.points)
    return pcd_down, {"before": n_before, "after": n_after, "removed": n_before - n_after,
                       "voxel_size": voxel_size}


def estimate_and_orient_normals(pcd, radius, max_nn, orient_toward=None):
    """Estimate normals and optionally orient them toward a reference point."""
    n_before = len(pcd.points)
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=max_nn)
    )
    if orient_toward is not None:
        pcd.orient_normals_towards_camera_location(orient_toward)
    elif pcd.has_normals():
        # Orient toward centroid by default
        pts = np.asarray(pcd.points)
        center = np.mean(pts, axis=0)
        pcd.orient_normals_towards_camera_location(center + np.array([0, 0, 10]))
    return pcd, {"before": n_before, "after": n_before, "removed": 0,
                  "normals_estimated": pcd.has_normals(),
                  "radius": radius, "max_nn": max_nn}
