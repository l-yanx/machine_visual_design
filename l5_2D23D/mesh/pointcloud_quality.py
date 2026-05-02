"""Point cloud statistics computation."""

import numpy as np
from mesh.utils import compute_nn_distance_stats


def compute_point_cloud_stats(pcd):
    """Compute comprehensive statistics for a point cloud.

    Returns a dict with keys:
        num_points, bounds_min, bounds_max, extent, centroid,
        dist_to_centroid_mean/std/min/max,
        color_mean/std/min/max (if colors exist),
        nn_distance_mean/median/std/min/max
    """
    pts = np.asarray(pcd.points)
    n = len(pts)

    bounds_min = np.min(pts, axis=0)
    bounds_max = np.max(pts, axis=0)
    extent = bounds_max - bounds_min
    centroid = np.mean(pts, axis=0)
    dists = np.linalg.norm(pts - centroid, axis=1)

    stats = {
        "num_points": n,
        "bounds_min": bounds_min,
        "bounds_max": bounds_max,
        "extent": extent,
        "centroid": centroid,
        "dist_to_centroid_mean": float(np.mean(dists)),
        "dist_to_centroid_std": float(np.std(dists)),
        "dist_to_centroid_min": float(np.min(dists)),
        "dist_to_centroid_max": float(np.max(dists)),
    }

    if pcd.has_colors():
        colors = np.asarray(pcd.colors)
        stats["color_mean"] = np.mean(colors, axis=0)
        stats["color_std"] = np.std(colors, axis=0)
        stats["color_min"] = np.min(colors, axis=0)
        stats["color_max"] = np.max(colors, axis=0)
    else:
        stats["color_mean"] = None
        stats["color_std"] = None
        stats["color_min"] = None
        stats["color_max"] = None

    nn = compute_nn_distance_stats(pcd)
    stats["nn_distance_mean"] = nn["mean"]
    stats["nn_distance_median"] = nn["median"]
    stats["nn_distance_std"] = nn["std"]
    stats["nn_distance_min"] = nn["min"]
    stats["nn_distance_max"] = nn["max"]

    return stats


def format_stats_for_report(stats, label="Point Cloud Statistics"):
    """Format statistics as a readable text block."""
    lines = [f"--- {label} ---"]
    lines.append(f"  Number of points: {stats['num_points']:,}")
    lines.append(f"  Bounding box min: ({stats['bounds_min'][0]:.4f}, {stats['bounds_min'][1]:.4f}, {stats['bounds_min'][2]:.4f})")
    lines.append(f"  Bounding box max: ({stats['bounds_max'][0]:.4f}, {stats['bounds_max'][1]:.4f}, {stats['bounds_max'][2]:.4f})")
    lines.append(f"  Extent: ({stats['extent'][0]:.4f}, {stats['extent'][1]:.4f}, {stats['extent'][2]:.4f})")
    lines.append(f"  Centroid: ({stats['centroid'][0]:.4f}, {stats['centroid'][1]:.4f}, {stats['centroid'][2]:.4f})")
    lines.append(f"  Distance to centroid: mean={stats['dist_to_centroid_mean']:.4f}, std={stats['dist_to_centroid_std']:.4f}, min={stats['dist_to_centroid_min']:.4f}, max={stats['dist_to_centroid_max']:.4f}")
    if stats["color_mean"] is not None:
        lines.append(f"  Color mean: ({stats['color_mean'][0]:.3f}, {stats['color_mean'][1]:.3f}, {stats['color_mean'][2]:.3f})")
        lines.append(f"  Color std:  ({stats['color_std'][0]:.3f}, {stats['color_std'][1]:.3f}, {stats['color_std'][2]:.3f})")
        lines.append(f"  Color min:  ({stats['color_min'][0]:.3f}, {stats['color_min'][1]:.3f}, {stats['color_min'][2]:.3f})")
        lines.append(f"  Color max:  ({stats['color_max'][0]:.3f}, {stats['color_max'][1]:.3f}, {stats['color_max'][2]:.3f})")
    else:
        lines.append("  Colors: none")
    lines.append(f"  NN distance: mean={stats['nn_distance_mean']:.6f}, median={stats['nn_distance_median']:.6f}, std={stats['nn_distance_std']:.6f}, min={stats['nn_distance_min']:.6f}, max={stats['nn_distance_max']:.6f}")
    return "\n".join(lines)
