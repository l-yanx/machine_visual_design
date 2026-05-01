"""
Point cloud fusion module.
Merges all partial point clouds into a single dense point cloud with filtering.
"""

import os
import numpy as np
import open3d as o3d


def fuse_point_clouds(partial_clouds, voxel_size=0.02,
                       nb_neighbors=20, std_ratio=2.0, logger=None):
    """Fuse multiple partial point clouds into one dense point cloud.

    Operations:
    1. Merge all partial point clouds.
    2. Remove NaN and infinite values.
    3. Apply voxel downsampling.
    4. Apply statistical outlier removal.

    Args:
        partial_clouds: dict {img_name: (points (N,3), colors (N,3))}.
        voxel_size: Voxel size for downsampling (default 0.02).
        nb_neighbors: Number of neighbors for outlier removal (default 20).
        std_ratio: Standard deviation ratio for outlier removal (default 2.0).
        logger: Optional logger instance.

    Returns:
        open3d.geometry.PointCloud: Fused point cloud.
    """
    all_points = []
    all_colors = []

    for img_name, (points, colors) in partial_clouds.items():
        if len(points) == 0:
            continue
        all_points.append(points)
        all_colors.append(colors)

    if len(all_points) == 0:
        if logger:
            logger.warning("No points to fuse")
        return o3d.geometry.PointCloud()

    # Merge
    merged_points = np.vstack(all_points)
    merged_colors = np.vstack(all_colors)

    if logger:
        logger.info(f"Merged {len(merged_points)} points from {len(all_points)} partial clouds")

    # Remove NaN and infinite values
    valid = np.all(np.isfinite(merged_points), axis=1)
    if np.sum(~valid) > 0:
        merged_points = merged_points[valid]
        merged_colors = merged_colors[valid]
        if logger:
            logger.info(f"  Removed {np.sum(~valid)} NaN/inf points, "
                       f"{len(merged_points)} remaining")

    if len(merged_points) == 0:
        if logger:
            logger.warning("No valid points after NaN/inf removal")
        return o3d.geometry.PointCloud()

    # Create Open3D point cloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(merged_points)
    pcd.colors = o3d.utility.Vector3dVector(merged_colors.astype(np.float64) / 255.0)

    if logger:
        logger.info(f"  Before voxel downsampling: {len(pcd.points)} points")

    # Voxel downsampling
    if voxel_size > 0:
        pcd = pcd.voxel_down_sample(voxel_size)
        if logger:
            logger.info(f"  After voxel downsampling (voxel={voxel_size}): {len(pcd.points)} points")

    # Statistical outlier removal
    if nb_neighbors > 0 and std_ratio > 0 and len(pcd.points) > nb_neighbors:
        pcd, _ = pcd.remove_statistical_outlier(
            nb_neighbors=nb_neighbors, std_ratio=std_ratio
        )
        if logger:
            logger.info(f"  After outlier removal (nb={nb_neighbors}, std={std_ratio}): "
                       f"{len(pcd.points)} points")

    return pcd


def fuse_and_export(partial_clouds, output_path, voxel_size=0.02,
                     nb_neighbors=20, std_ratio=2.0, logger=None):
    """Fuse partial point clouds and export to PLY.

    Args:
        partial_clouds: dict {img_name: (points, colors)}.
        output_path: Path to output dense.ply.
        voxel_size: Voxel size for downsampling.
        nb_neighbors: Number of neighbors for outlier removal.
        std_ratio: Standard deviation ratio.
        logger: Optional logger instance.

    Returns:
        open3d.geometry.PointCloud: The fused point cloud, or None on failure.
    """
    pcd = fuse_point_clouds(
        partial_clouds,
        voxel_size=voxel_size,
        nb_neighbors=nb_neighbors,
        std_ratio=std_ratio,
        logger=logger
    )

    if len(pcd.points) == 0:
        if logger:
            logger.warning("Fused point cloud is empty")
        return None

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    o3d.io.write_point_cloud(output_path, pcd)

    if logger:
        logger.info(f"Fused dense point cloud saved to {output_path}")
        logger.info(f"Final point count: {len(pcd.points)}")

    return pcd
