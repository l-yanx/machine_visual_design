"""
Depth map filtering module.
Filters invalid or unreliable depth values from raw depth maps.
"""

import os
import numpy as np
import cv2


def filter_depth_map(depth_map, confidence_map, depth_range,
                      zncc_threshold=0.5, apply_median_filter=False, logger=None):
    """Apply filters to a single depth map.

    Filters:
    1. Remove depth values with confidence < zncc_threshold.
    2. Remove depth values <= 0.
    3. Remove depth values outside estimated depth range.
    4. Optionally apply median filter.

    Args:
        depth_map: (H, W) array of depth values.
        confidence_map: (H, W) array of ZNCC confidence scores.
        depth_range: dict with 'min_depth' and 'max_depth'.
        zncc_threshold: Minimum ZNCC confidence threshold (default 0.5).
        apply_median_filter: Whether to apply median filtering (default False).
        logger: Optional logger instance.

    Returns:
        np.ndarray: Filtered depth map (invalid pixels set to 0).
    """
    H, W = depth_map.shape
    filtered = depth_map.copy()

    min_depth = depth_range['min_depth']
    max_depth = depth_range['max_depth']

    # 1. Remove low-confidence depths
    low_conf_mask = confidence_map < zncc_threshold
    filtered[low_conf_mask] = 0.0

    # 2. Remove zero or negative depths
    invalid_depth_mask = filtered <= 1e-6
    filtered[invalid_depth_mask] = 0.0

    # 3. Remove depths outside the estimated range
    out_of_range_mask = (filtered < min_depth) | (filtered > max_depth)
    filtered[out_of_range_mask] = 0.0

    # 4. Optional median filter (applied to non-zero values)
    if apply_median_filter:
        # Create a mask of valid pixels
        valid_mask = filtered > 1e-6
        # Apply median filter to the whole image
        median_filtered = cv2.medianBlur(filtered.astype(np.float32), 5)
        # Restore only valid filtered values
        filtered = np.where(valid_mask, median_filtered, 0.0)

    return filtered


def filter_all_depth_maps(depth_maps, confidence_maps, depth_ranges,
                           zncc_threshold=0.5, apply_median_filter=False,
                           image_names=None, logger=None):
    """Filter all depth maps.

    Args:
        depth_maps: dict {img_name: (H, W) depth array}.
        confidence_maps: dict {img_name: (H, W) confidence array}.
        depth_ranges: dict {img_name: {'min_depth': float, 'max_depth': float}}.
        zncc_threshold: Minimum ZNCC confidence threshold.
        apply_median_filter: Whether to apply median filtering.
        image_names: List of image names to process (if None, uses all in depth_maps).
        logger: Optional logger instance.

    Returns:
        dict: {img_name: filtered_depth_map (H, W)}.
    """
    if image_names is None:
        image_names = list(depth_maps.keys())

    filtered = {}
    total_valid_before = 0
    total_valid_after = 0

    for img_name in image_names:
        depth = depth_maps.get(img_name)
        conf = confidence_maps.get(img_name)
        dr = depth_ranges.get(img_name, {'min_depth': 0.5, 'max_depth': 10.0})

        if depth is None or conf is None:
            if logger:
                logger.warning(f"  {img_name}: Missing depth or confidence map, skipping filter")
            continue

        n_before = np.count_nonzero(depth > 1e-6)
        filtered_depth = filter_depth_map(
            depth, conf, dr, zncc_threshold=zncc_threshold,
            apply_median_filter=apply_median_filter, logger=logger
        )
        n_after = np.count_nonzero(filtered_depth > 1e-6)
        filtered[img_name] = filtered_depth
        total_valid_before += n_before
        total_valid_after += n_after

        if logger:
            logger.info(f"  {img_name}: {n_before} -> {n_after} valid pixels "
                       f"({100*n_after/max(n_before,1):.1f}%)")

    if logger:
        logger.info(f"Total: {total_valid_before} -> {total_valid_after} valid pixels "
                   f"({100*total_valid_after/max(total_valid_before,1):.1f}%)")

    return filtered


def save_filtered_depth_maps(filtered_maps, output_dir, logger=None):
    """Save filtered depth maps to disk.

    Args:
        filtered_maps: dict {img_name: filtered_depth_map}.
        output_dir: Directory to save to (results/dense/depth_maps_filtered/).
        logger: Optional logger instance.
    """
    os.makedirs(output_dir, exist_ok=True)

    for img_name, depth_map in filtered_maps.items():
        base_name = os.path.splitext(img_name)[0]
        output_path = os.path.join(output_dir, f"{base_name}_depth_filtered.npy")
        np.save(output_path, depth_map)

        if logger:
            logger.debug(f"    Saved filtered depth map: {output_path}")

    if logger:
        logger.info(f"Saved {len(filtered_maps)} filtered depth maps to {output_dir}")
