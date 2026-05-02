"""DBSCAN clustering for main-cluster extraction."""

import numpy as np
import open3d as o3d


def extract_main_cluster_dbscan(pcd, eps, min_points, keep_largest_k=1):
    """Cluster points with DBSCAN and keep the largest K clusters.

    Returns (filtered_pcd, stats_dict).
    stats_dict includes: n_before, n_after, n_clusters, cluster_sizes, kept_cluster_count.
    """
    n_before = len(pcd.points)
    if n_before < min_points:
        return pcd, {
            "before": n_before, "after": n_before, "removed": 0,
            "n_clusters": 0, "cluster_sizes": [], "kept_cluster_count": 0,
            "eps": eps, "min_points": min_points,
            "note": "too few points for DBSCAN, skipped"
        }

    labels = np.array(pcd.cluster_dbscan(eps=eps, min_points=min_points, print_progress=False))

    # Count clusters (exclude noise labeled -1)
    unique_labels = np.unique(labels)
    cluster_labels = unique_labels[unique_labels >= 0]
    n_clusters = len(cluster_labels)

    if n_clusters == 0:
        return pcd, {
            "before": n_before, "after": n_before, "removed": 0,
            "n_clusters": 0, "cluster_sizes": [], "kept_cluster_count": 0,
            "eps": eps, "min_points": min_points,
            "note": "no clusters found, all points are noise"
        }

    # Count sizes
    cluster_sizes = []
    for c in cluster_labels:
        cluster_sizes.append(int(np.sum(labels == c)))

    # Sort by size descending
    sorted_indices = np.argsort(cluster_sizes)[::-1]
    keep_k = min(keep_largest_k, n_clusters)
    kept_labels = set(cluster_labels[sorted_indices[:keep_k]])

    keep_mask = np.isin(labels, list(kept_labels))
    n_after = int(np.sum(keep_mask))

    if n_after == 0:
        return pcd, {
            "before": n_before, "after": n_before, "removed": 0,
            "n_clusters": n_clusters, "cluster_sizes": cluster_sizes, "kept_cluster_count": 0,
            "eps": eps, "min_points": min_points,
            "note": "kept cluster has no points"
        }

    pcd_filtered = pcd.select_by_index(np.where(keep_mask)[0])
    return pcd_filtered, {
        "before": n_before, "after": n_after, "removed": n_before - n_after,
        "n_clusters": n_clusters, "cluster_sizes": cluster_sizes, "kept_cluster_count": keep_k,
        "eps": eps, "min_points": min_points
    }
