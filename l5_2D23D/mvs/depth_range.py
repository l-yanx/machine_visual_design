"""
Depth range estimation module.
Estimates depth search range for each reference image using sparse 3D points.
"""

import os
import json
import numpy as np


def estimate_depth_range_for_image(img_name, pose, points3D, tracks,
                                    percentile_min=5, percentile_max=95,
                                    expansion_factor_min=0.9, expansion_factor_max=1.1,
                                    logger=None):
    """Estimate depth range for a single reference image.

    Transforms sparse 3D points into the reference camera coordinate system,
    keeps points with positive depth, and uses percentiles to estimate range.

    Args:
        img_name: Reference image filename.
        pose: dict with 'R' (3x3) and 't' (3,).
        points3D: dict mapping point_id -> {'xyz': np.array(3,), ...}.
        tracks: dict mapping point_id -> [(img_name, kp_idx), ...].
        percentile_min: Lower percentile for depth range (default 5).
        percentile_max: Upper percentile for depth range (default 95).
        expansion_factor_min: Factor to expand min depth (default 0.9).
        expansion_factor_max: Factor to expand max depth (default 1.1).
        logger: Optional logger instance.

    Returns:
        dict: {'min_depth': float, 'max_depth': float} or None if insufficient points.
    """
    R = pose['R']  # 3x3
    t = pose['t']  # (3,)

    depths = []
    for pt_id, pt_data in points3D.items():
        xyz_world = pt_data['xyz']

        # Transform world point to camera coordinate system
        # X_cam = R * X_world + t
        xyz_cam = R @ xyz_world + t

        depth = xyz_cam[2]  # z-coordinate in camera space
        if depth > 0:
            depths.append(depth)

    if len(depths) < 10:
        if logger:
            logger.warning(f"  {img_name}: only {len(depths)} points with positive depth, using default range")
        return {'min_depth': 0.5, 'max_depth': 10.0}

    depths = np.array(depths)

    # Use 5th and 95th percentiles
    base_min = np.percentile(depths, percentile_min)
    base_max = np.percentile(depths, percentile_max)

    # Expand range
    min_depth = expansion_factor_min * base_min
    max_depth = expansion_factor_max * base_max

    # Safety: min_depth should be non-negative
    min_depth = max(min_depth, 1e-6)

    if logger:
        logger.debug(f"  {img_name}: {len(depths)} valid depths, "
                     f"p{percentile_min}={base_min:.3f}, p{percentile_max}={base_max:.3f}, "
                     f"range=[{min_depth:.3f}, {max_depth:.3f}]")

    return {'min_depth': float(min_depth), 'max_depth': float(max_depth)}


def estimate_depth_ranges(poses, points3D, tracks, image_names,
                           percentile_min=5, percentile_max=95,
                           expansion_factor_min=0.9, expansion_factor_max=1.1,
                           logger=None):
    """Estimate depth range for all reference images.

    Args:
        poses: dict mapping image_name -> {'R': 3x3, 't': (3,)}.
        points3D: dict of sparse 3D points.
        tracks: dict of 2D-3D observations.
        image_names: List of registered image names.
        percentile_min: Lower percentile for depth range.
        percentile_max: Upper percentile for depth range.
        expansion_factor_min: Factor to expand min depth.
        expansion_factor_max: Factor to expand max depth.
        logger: Optional logger instance.

    Returns:
        dict: {img_name: {'min_depth': float, 'max_depth': float}}
    """
    depth_ranges = {}

    for img_name in image_names:
        range_info = estimate_depth_range_for_image(
            img_name, poses[img_name], points3D, tracks,
            percentile_min=percentile_min,
            percentile_max=percentile_max,
            expansion_factor_min=expansion_factor_min,
            expansion_factor_max=expansion_factor_max,
            logger=logger
        )
        depth_ranges[img_name] = range_info

    if logger:
        # Log summary statistics
        all_mins = [v['min_depth'] for v in depth_ranges.values()]
        all_maxs = [v['max_depth'] for v in depth_ranges.values()]
        logger.info(f"Depth range summary across {len(depth_ranges)} images:")
        logger.info(f"  min_depth: [{np.min(all_mins):.3f}, {np.max(all_mins):.3f}]")
        logger.info(f"  max_depth: [{np.min(all_maxs):.3f}, {np.max(all_maxs):.3f}]")

    return depth_ranges


def export_depth_ranges(depth_ranges, output_path, logger=None):
    """Export depth ranges to JSON.

    Args:
        depth_ranges: dict {img_name: {'min_depth': float, 'max_depth': float}}.
        output_path: Path to output JSON file.
        logger: Optional logger instance.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(depth_ranges, f, indent=2)

    if logger:
        logger.info(f"Exported depth ranges for {len(depth_ranges)} images to {output_path}")
