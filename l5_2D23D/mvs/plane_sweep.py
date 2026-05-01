"""
Plane sweep depth estimation module.
Estimates depth maps using ZNCC-based plane sweeping across multiple views.
Uses sparse 3D point projections as seed regions for efficient processing.
"""

import os
import time
import numpy as np
import cv2
from mvs.zncc import zncc_score, extract_patch


def compute_zncc_batch(ref_patches, src_patches, variance_threshold=1e-5):
    """Compute ZNCC for a batch of patch pairs.

    Args:
        ref_patches: (N, P, P) array of reference patches.
        src_patches: (N, P, P) array of source patches.
        variance_threshold: Minimum variance for valid patches.

    Returns:
        np.ndarray: (N,) array of ZNCC scores (NaN for invalid).
    """
    N, P, _ = ref_patches.shape
    flat_ref = ref_patches.reshape(N, -1).astype(np.float64)
    flat_src = src_patches.reshape(N, -1).astype(np.float64)

    # Center
    mean_ref = flat_ref.mean(axis=1, keepdims=True)
    mean_src = flat_src.mean(axis=1, keepdims=True)
    ref_c = flat_ref - mean_ref
    src_c = flat_src - mean_src

    # Variances
    var_ref = np.sum(ref_c ** 2, axis=1)
    var_src = np.sum(src_c ** 2, axis=1)

    # Numerator
    numerator = np.sum(ref_c * src_c, axis=1)

    # Denominator
    denominator = np.sqrt(var_ref * var_src)

    # ZNCC
    scores = np.full(N, np.nan, dtype=np.float64)
    valid = (var_ref >= variance_threshold) & (var_src >= variance_threshold) & (denominator > 1e-15)
    scores[valid] = numerator[valid] / denominator[valid]
    scores = np.clip(scores, -1.0, 1.0)

    return scores


def build_sparse_pixel_mask(points3D, tracks, poses, K, image_name, pixel_radius=30):
    """Build a binary mask of pixels near sparse 3D point projections.

    Args:
        points3D: dict mapping point_id -> {'xyz': np.array(3,), ...}.
        tracks: dict mapping point_id -> [(img_name, kp_idx), ...].
        poses: dict mapping image_name -> {'R': 3x3, 't': (3,)}.
        K: 3x3 intrinsic matrix.
        image_name: Reference image name.
        pixel_radius: Radius in pixels around each projected point (default 30).

    Returns:
        np.ndarray: (H, W) binary mask (True = seed pixel).
        np.ndarray: (N, 2) array of (u, v) coordinates of seed pixels.
    """
    R = poses[image_name]['R']
    t = poses[image_name]['t']

    # Approximate H, W from K
    W = int(K[0, 2] * 2)
    H = int(K[1, 2] * 2)

    mask = np.zeros((H, W), dtype=bool)
    seed_pixels = []

    for pt_id, pt_data in points3D.items():
        xyz = pt_data['xyz']

        # Check if this point is visible in the reference image
        visible = False
        for obs_img, _ in tracks.get(pt_id, []):
            if obs_img == image_name:
                visible = True
                break
        if not visible:
            continue

        # Project to reference image
        X_cam = R @ xyz + t
        if X_cam[2] <= 0:
            continue
        p = K @ X_cam
        u = p[0] / p[2]
        v = p[1] / p[2]

        if 0 <= u < W and 0 <= v < H:
            # Mark a square region around the projected point
            u_min = max(0, int(u - pixel_radius))
            u_max = min(W, int(u + pixel_radius + 1))
            v_min = max(0, int(v - pixel_radius))
            v_max = min(H, int(v + pixel_radius + 1))
            mask[v_min:v_max, u_min:u_max] = True

    # Collect seed pixel coordinates (sampled by stride to reduce density)
    # Already dense from the mask creation, just return the mask
    return mask


def get_seed_pixels(mask, stride=2):
    """Get seed pixel coordinates from a mask, sampled by stride.

    Args:
        mask: (H, W) boolean array.
        stride: Sampling stride.

    Returns:
        np.ndarray: (N, 2) array of (u, v) coordinates.
    """
    H, W = mask.shape
    pixel_list = []
    for v in range(0, H, stride):
        for u in range(0, W, stride):
            if mask[v, u]:
                pixel_list.append((u, v))
    return np.array(pixel_list, dtype=np.float64)


def run_plane_sweep_single_image(ref_img_name, ref_image_gray, ref_image_color,
                                  source_views, K, poses, depth_range,
                                  depth_samples=64, patch_size=5, stride=2,
                                  source_view_num=3, zncc_threshold=0.5,
                                  image_dir=None, seed_mask=None, logger=None):
    """Run plane sweeping depth estimation for a single reference image.

    Uses seed_mask to restrict processing to pixels near sparse point projections.

    Args:
        ref_img_name: Reference image filename.
        ref_image_gray: Grayscale reference image (H, W).
        ref_image_color: Color reference image (H, W, 3) BGR.
        source_views: List of source image filenames.
        K: 3x3 intrinsic matrix.
        poses: dict mapping image_name -> {'R': 3x3, 't': (3,)}.
        depth_range: dict with 'min_depth' and 'max_depth'.
        depth_samples: Number of depth samples (default 64).
        patch_size: Square patch size (default 5).
        stride: Pixel sampling stride (default 2).
        source_view_num: Number of source views to use (default 3).
        zncc_threshold: Minimum ZNCC threshold (default 0.5).
        image_dir: Directory containing source images.
        seed_mask: (H, W) boolean mask of seed pixels.
        logger: Optional logger instance.

    Returns:
        tuple: (depth_map (H, W), confidence_map (H, W))
    """
    H, W = ref_image_gray.shape[:2]
    K_inv = np.linalg.inv(K)

    R_ref = poses[ref_img_name]['R']  # 3x3
    t_ref = poses[ref_img_name]['t']  # (3,)

    # Pre-compute for world transform
    # X_world = R_ref^T @ (X_cam - t_ref) = (X_cam - t_ref) @ R_ref (row vector convention)

    # Load source images
    source_images_gray = []
    source_poses = []
    for src_name in source_views[:source_view_num]:
        src_path = os.path.join(image_dir, src_name)
        src_img = cv2.imread(src_path, cv2.IMREAD_GRAYSCALE)
        if src_img is None:
            if logger:
                logger.warning(f"  Could not load source image {src_path}, skipping")
            continue
        source_images_gray.append(src_img.astype(np.float64))
        source_poses.append(poses[src_name])

    if len(source_images_gray) == 0:
        if logger:
            logger.warning(f"  {ref_img_name}: No valid source images")
        return np.zeros((H, W), dtype=np.float64), np.zeros((H, W), dtype=np.float64)

    # Use seed mask if provided, otherwise use all pixels
    if seed_mask is not None:
        pixel_coords = get_seed_pixels(seed_mask, stride=stride)
    else:
        u_grid, v_grid = np.meshgrid(np.arange(0, W, stride), np.arange(0, H, stride))
        pixel_us = u_grid.ravel().astype(np.float64)
        pixel_vs = v_grid.ravel().astype(np.float64)
        pixel_coords = np.column_stack((pixel_us, pixel_vs))

    if len(pixel_coords) == 0:
        if logger:
            logger.warning(f"  {ref_img_name}: No seed pixels to process")
        return np.zeros((H, W), dtype=np.float64), np.zeros((H, W), dtype=np.float64)

    pixel_us = pixel_coords[:, 0]
    pixel_vs = pixel_coords[:, 1]
    n_pixels = len(pixel_us)

    # Depth samples
    min_depth = depth_range['min_depth']
    max_depth = depth_range['max_depth']
    depths = np.linspace(min_depth, max_depth, depth_samples, dtype=np.float64)

    # Pre-compute ray directions for all sampled pixels
    homogeneous = np.stack([pixel_us, pixel_vs, np.ones(n_pixels)], axis=1)  # (N, 3)
    rays = homogeneous @ K_inv.T  # (N, 3)

    # Pre-extract reference patches
    ref_patches = np.zeros((n_pixels, patch_size, patch_size), dtype=np.float64)
    half = patch_size // 2
    for i in range(n_pixels):
        u, v = int(round(pixel_us[i])), int(round(pixel_vs[i]))
        u_start = max(0, u - half)
        u_end = min(W, u + half + 1)
        v_start = max(0, v - half)
        v_end = min(H, v + half + 1)
        pu_start = u_start - (u - half)
        pu_end = pu_start + (u_end - u_start)
        pv_start = v_start - (v - half)
        pv_end = pv_start + (v_end - v_start)
        if pv_end > pv_start and pu_end > pu_start:
            ref_patches[i, pv_start:pv_end, pu_start:pu_end] = \
                ref_image_gray[v_start:v_end, u_start:u_end]
        if pv_start > 0:
            ref_patches[i, :pv_start, :] = ref_patches[i, pv_start, :]
        if pv_end < patch_size:
            ref_patches[i, pv_end:, :] = ref_patches[i, pv_end - 1, :]
        if pu_start > 0:
            ref_patches[i, :, :pu_start] = ref_patches[i, :, pu_start, np.newaxis]
        if pu_end < patch_size:
            ref_patches[i, :, pu_end:] = ref_patches[i, :, pu_end - 1, np.newaxis]

    # Init best results
    best_scores = np.full(n_pixels, -np.inf, dtype=np.float64)
    best_depths = np.zeros(n_pixels, dtype=np.float64)

    n_sources = len(source_images_gray)

    t_start = time.time()
    for d_idx, depth in enumerate(depths):
        # Back-project: X_cam = depth * ray
        X_cam = depth * rays  # (N, 3)

        # X_world = R^T @ (X_cam - t)
        X_world = (X_cam - t_ref.reshape(1, 3)) @ R_ref  # (N, 3): X_world = R_ref^T @ (X_cam - t_ref)

        agg_scores = np.zeros(n_pixels, dtype=np.float64)
        valid_counts = np.zeros(n_pixels, dtype=np.int32)

        for src_idx in range(n_sources):
            R_src = source_poses[src_idx]['R']
            t_src = source_poses[src_idx]['t'].reshape(3, 1)
            src_gray = source_images_gray[src_idx]
            H_s, W_s = src_gray.shape[:2]

            # Project world points to source camera
            X_src_cam = R_src @ X_world.T + t_src  # (3, N)
            z_src = X_src_cam[2, :]

            valid_depth = z_src > 1e-6
            # Compute pixel coordinates: u_pixel = fx * X_cam[0]/z + cx
            u_pixel = np.full(n_pixels, np.nan, dtype=np.float64)
            v_pixel = np.full(n_pixels, np.nan, dtype=np.float64)

            fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
            valid_d = valid_depth
            if np.sum(valid_d) > 0:
                u_pixel[valid_d] = fx * X_src_cam[0, valid_d] / z_src[valid_d] + cx
                v_pixel[valid_d] = fy * X_src_cam[1, valid_d] / z_src[valid_d] + cy

            valid_bounds = valid_d & (u_pixel >= 0) & (u_pixel < W_s) & (v_pixel >= 0) & (v_pixel < H_s)

            if np.sum(valid_bounds) == 0:
                continue

            # Extract source patches
            valid_indices = np.where(valid_bounds)[0]
            src_patches = np.zeros((len(valid_indices), patch_size, patch_size), dtype=np.float64)

            for j, idx in enumerate(valid_indices):
                u_s = int(round(u_pixel[idx]))
                v_s = int(round(v_pixel[idx]))
                u_start_s = max(0, u_s - half)
                u_end_s = min(W_s, u_s + half + 1)
                v_start_s = max(0, v_s - half)
                v_end_s = min(H_s, v_s + half + 1)
                pu_start_s = u_start_s - (u_s - half)
                pu_end_s = pu_start_s + (u_end_s - u_start_s)
                pv_start_s = v_start_s - (v_s - half)
                pv_end_s = pv_start_s + (v_end_s - v_start_s)
                if pv_end_s > pv_start_s and pu_end_s > pu_start_s:
                    src_patches[j, pv_start_s:pv_end_s, pu_start_s:pu_end_s] = \
                        src_gray[v_start_s:v_end_s, u_start_s:u_end_s]
                if pv_start_s > 0:
                    src_patches[j, :pv_start_s, :] = src_patches[j, pv_start_s, :]
                if pv_end_s < patch_size:
                    src_patches[j, pv_end_s:, :] = src_patches[j, pv_end_s - 1, :]
                if pu_start_s > 0:
                    src_patches[j, :, :pu_start_s] = src_patches[j, :, pu_start_s, np.newaxis]
                if pu_end_s < patch_size:
                    src_patches[j, :, pu_end_s:] = src_patches[j, :, pu_end_s - 1, np.newaxis]

            # Compute ZNCC
            scores = compute_zncc_batch(ref_patches[valid_indices], src_patches)

            # Aggregate
            for j, idx in enumerate(valid_indices):
                if not np.isnan(scores[j]):
                    agg_scores[idx] += scores[j]
                    valid_counts[idx] += 1

        # Average across source views and update best
        for i in range(n_pixels):
            if valid_counts[i] > 0:
                avg_score = agg_scores[i] / valid_counts[i]
                if avg_score > best_scores[i]:
                    best_scores[i] = avg_score
                    best_depths[i] = depth

        if logger and (d_idx + 1) % 16 == 0:
            n_best = np.sum(best_scores > zncc_threshold)
            elapsed = time.time() - t_start
            logger.debug(f"    depth {d_idx+1}/{depth_samples}: d={depth:.3f}, "
                        f"{n_best} pixels above threshold, {elapsed:.1f}s")

    elapsed = time.time() - t_start

    # Build full-size output maps
    depth_map = np.zeros((H, W), dtype=np.float64)
    confidence_map = np.zeros((H, W), dtype=np.float64)

    for i in range(n_pixels):
        u = int(round(pixel_us[i]))
        v = int(round(pixel_vs[i]))
        if best_scores[i] > zncc_threshold:
            depth_map[v, u] = best_depths[i]
            confidence_map[v, u] = best_scores[i]

    n_valid = np.count_nonzero(depth_map > 1e-6)
    if logger:
        logger.info(f"  {ref_img_name}: {n_valid}/{n_pixels} seed pixels "
                    f"({100*n_valid/max(n_pixels,1):.1f}%) above threshold, "
                    f"range=[{min_depth:.2f}, {max_depth:.2f}], {elapsed:.1f}s")

    return depth_map, confidence_map


def run_plane_sweep_all(ref_images, view_pairs, K, poses, depth_ranges,
                         image_dir, output_dir, config, seed_masks=None, logger=None):
    """Run plane sweep on all reference images.

    Args:
        ref_images: List of reference image filenames.
        view_pairs: dict {ref_img: [src_img1, ...]}.
        K: 3x3 intrinsic matrix.
        poses: dict mapping image_name -> {'R': 3x3, 't': (3,)}.
        depth_ranges: dict {img_name: {'min_depth': float, 'max_depth': float}}.
        image_dir: Directory containing images.
        output_dir: Base output directory (results/dense/).
        config: Configuration dict (MVS section).
        seed_masks: dict {img_name: (H,W) bool mask} of seed pixels (optional).
        logger: Optional logger instance.

    Returns:
        tuple: (depth_maps dict, confidence_maps dict)
    """
    depth_samples = config.get('depth_samples', 64)
    patch_size = config.get('patch_size', 5)
    stride = config.get('stride', 2)
    source_view_num = config.get('source_view_num', 3)
    zncc_threshold = config.get('zncc_threshold', 0.5)

    depth_dir = os.path.join(output_dir, 'depth_maps')
    conf_dir = os.path.join(output_dir, 'confidence_maps')
    os.makedirs(depth_dir, exist_ok=True)
    os.makedirs(conf_dir, exist_ok=True)

    depth_maps = {}
    confidence_maps = {}

    for idx, ref_name in enumerate(ref_images):
        if logger:
            logger.info(f"Processing [{idx+1}/{len(ref_images)}] {ref_name}")
            logger.info(f"  Source views: {view_pairs.get(ref_name, [])[:source_view_num]}")
            dr = depth_ranges.get(ref_name, {})
            logger.info(f"  Depth range: [{dr.get('min_depth', 0):.2f}, {dr.get('max_depth', 0):.2f}]")
            if seed_masks and ref_name in seed_masks:
                n_seeds = np.sum(seed_masks[ref_name])
                logger.info(f"  Seed pixels in mask: {n_seeds}")

        # Load reference image
        ref_path = os.path.join(image_dir, ref_name)
        ref_color = cv2.imread(ref_path)
        if ref_color is None:
            if logger:
                logger.warning(f"  Could not load {ref_path}, skipping")
            continue
        ref_gray = cv2.cvtColor(ref_color, cv2.COLOR_BGR2GRAY).astype(np.float64)

        seed_mask = seed_masks.get(ref_name) if seed_masks else None

        # Run plane sweep
        depth_map, conf_map = run_plane_sweep_single_image(
            ref_name, ref_gray, ref_color,
            view_pairs.get(ref_name, []), K, poses,
            depth_ranges.get(ref_name, {'min_depth': 0.5, 'max_depth': 10.0}),
            depth_samples=depth_samples,
            patch_size=patch_size,
            stride=stride,
            source_view_num=source_view_num,
            zncc_threshold=zncc_threshold,
            image_dir=image_dir,
            seed_mask=seed_mask,
            logger=logger
        )

        # Save
        base_name = os.path.splitext(ref_name)[0]
        depth_path = os.path.join(depth_dir, f"{base_name}_depth.npy")
        conf_path = os.path.join(conf_dir, f"{base_name}_confidence.npy")
        np.save(depth_path, depth_map)
        np.save(conf_path, conf_map)

        depth_maps[ref_name] = depth_map
        confidence_maps[ref_name] = conf_map

        if logger:
            logger.info(f"    Saved depth map to {depth_path}")
            logger.info(f"    Saved confidence map to {conf_path}")

    return depth_maps, confidence_maps
