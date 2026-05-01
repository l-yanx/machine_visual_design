"""
Depth to point cloud conversion module.
Back-projects valid depth pixels to 3D world coordinates and saves partial point clouds.
"""

import os
import numpy as np
import cv2


def depth_map_to_point_cloud(depth_map, image_color, K, R, t,
                              min_valid_depth=1e-6, logger=None):
    """Convert a single depth map to a partial point cloud.

    For each valid depth pixel:
      X_cam = depth * K^(-1) * [u, v, 1]^T
      X_world = R^(-1) * (X_cam - t)
    Color is assigned from the reference image at that pixel.

    Args:
        depth_map: (H, W) array of depth values (0 = invalid).
        image_color: (H, W, 3) BGR color image.
        K: 3x3 intrinsic matrix.
        R: 3x3 rotation matrix.
        t: (3,) translation vector.
        min_valid_depth: Minimum depth to be considered valid.
        logger: Optional logger instance.

    Returns:
        tuple: (points (N, 3) float64, colors (N, 3) uint8)
    """
    K_inv = np.linalg.inv(K)

    H, W = depth_map.shape

    # Find valid depth pixels
    v_indices, u_indices = np.where(depth_map > min_valid_depth)
    n_valid = len(v_indices)

    if n_valid == 0:
        return np.zeros((0, 3), dtype=np.float64), np.zeros((0, 3), dtype=np.uint8)

    depths = depth_map[v_indices, u_indices]

    # Homogeneous pixel coordinates: [u, v, 1]
    pixels = np.stack([u_indices.astype(np.float64), v_indices.astype(np.float64),
                       np.ones(n_valid)], axis=1)  # (N, 3)

    # X_cam = depth * K^(-1) * p
    rays = pixels @ K_inv.T  # (N, 3)
    X_cam = rays * depths.reshape(-1, 1)  # (N, 3)

    # X_world = R^(-1) * (X_cam - t) = R^T * (X_cam - t)
    # In row-vector convention (N,3) @ (3,3) = (N,3):
    X_world = (X_cam - t.reshape(1, 3)) @ R  # (N, 3)

    # Extract colors (BGR from OpenCV image)
    colors_bgr = image_color[v_indices, u_indices]
    # Convert BGR to RGB for PLY output
    colors_rgb = colors_bgr[:, ::-1]

    return X_world, colors_rgb


def export_partial_ply(points, colors, output_path, logger=None):
    """Export a partial point cloud to PLY format.

    Args:
        points: (N, 3) array of 3D points.
        colors: (N, 3) uint8 array of RGB colors.
        output_path: Path to output PLY file.
        logger: Optional logger instance.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")

        for i in range(len(points)):
            if np.isfinite(points[i]).all():
                x, y, z = points[i]
                r, g, b = colors[i]
                f.write(f"{x:.6f} {y:.6f} {z:.6f} {int(r)} {int(g)} {int(b)}\n")

    if logger:
        logger.debug(f"    Exported {len(points)} points to {output_path}")


def generate_all_partial_clouds(depth_maps, image_dir, K, poses, image_names,
                                 output_dir, logger=None):
    """Generate partial point clouds for all depth maps.

    Args:
        depth_maps: dict {img_name: (H, W) filtered depth array}.
        image_dir: Directory containing color images.
        K: 3x3 intrinsic matrix.
        poses: dict mapping image_name -> {'R': 3x3, 't': (3,)}.
        image_names: List of image names to process.
        output_dir: Directory to save partial PLY files.
        logger: Optional logger instance.

    Returns:
        dict: {img_name: (points_array, colors_array)}
    """
    os.makedirs(output_dir, exist_ok=True)
    partial_clouds = {}

    for img_name in image_names:
        depth = depth_maps.get(img_name)
        if depth is None:
            continue

        n_valid = np.count_nonzero(depth > 1e-6)
        if n_valid == 0:
            if logger:
                logger.warning(f"  {img_name}: No valid depth pixels, skipping")
            continue

        # Load color image
        img_path = os.path.join(image_dir, img_name)
        img_color = cv2.imread(img_path)
        if img_color is None:
            if logger:
                logger.warning(f"  {img_name}: Could not load color image, skipping")
            continue

        R = poses[img_name]['R']
        t = poses[img_name]['t']

        points, colors = depth_map_to_point_cloud(
            depth, img_color, K, R, t, logger=logger
        )

        partial_clouds[img_name] = (points, colors)

        # Save PLY
        base_name = os.path.splitext(img_name)[0]
        ply_path = os.path.join(output_dir, f"{base_name}_partial.ply")
        export_partial_ply(points, colors, ply_path, logger=logger)

        if logger:
            logger.info(f"  {img_name}: {len(points)} points -> {ply_path}")

    if logger:
        total_points = sum(len(pc[0]) for pc in partial_clouds.values())
        logger.info(f"Generated {len(partial_clouds)} partial point clouds with {total_points} total points")

    return partial_clouds
