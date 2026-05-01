#!/usr/bin/env python3
"""
Main MVS pipeline: ZNCC-based Multi-View Stereo and Dense PLY Generation.
Orchestrates the full MVS pipeline from SfM inputs to dense point cloud.

Usage:
    python main_mvs.py --config config.yaml
"""

import os
import sys
import time
import argparse
import logging
import yaml
import numpy as np
import cv2


def setup_logging(log_path):
    """Set up logging to file and console."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger = logging.getLogger('mvs')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fh = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s',
                                     datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter('[%(levelname)s] %(message)s')
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    return logger


def load_config(config_path):
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def main():
    parser = argparse.ArgumentParser(
        description='ZNCC-based MVS and Dense PLY Generation'
    )
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--image_limit', type=int, default=None,
                       help='Limit number of reference images to process (for testing)')
    args = parser.parse_args()

    config = load_config(args.config)

    # Paths
    results_dir = config['paths']['results_dir']
    image_dir = os.path.join('data', 'images_resized')  # Hard-coded fallback

    # Check for alternate image path
    if 'image' in config and 'resize_width' in config['image']:
        pass  # Using the standard path

    sparse_dir = os.path.join(results_dir, 'sparse')
    dense_dir = os.path.join(results_dir, 'dense')
    log_dir = os.path.join(results_dir, 'logs')

    # Setup logging
    logger = setup_logging(os.path.join(log_dir, 'mvs_log.txt'))
    logger.info("=" * 60)
    logger.info("ZNCC-based Multi-View Stereo Pipeline")
    logger.info("=" * 60)
    logger.info(f"Configuration: {args.config}")
    logger.info(f"Sparse results dir: {sparse_dir}")
    logger.info(f"Dense results dir: {dense_dir}")
    logger.info(f"Image dir: {image_dir}")

    mvs_config = config.get('mvs', {})
    logger.info(f"MVS config: {mvs_config}")

    fusion_config = config.get('fusion', {})
    logger.info(f"Fusion config: {fusion_config}")

    # ============================================================
    # Step 1: Read SfM results
    # ============================================================
    logger.info("-" * 40)
    logger.info("Step 1: Reading SfM results from Task 1")
    from mvs.read_sfm import read_sfm_results

    K, poses, points3D, tracks, image_names = read_sfm_results(sparse_dir, logger=logger)

    # Optionally limit images for testing
    if args.image_limit is not None and args.image_limit < len(image_names):
        image_names = image_names[:args.image_limit]
        new_poses = {k: v for k, v in poses.items() if k in image_names}
        poses = new_poses
        logger.info(f"Limited to {len(image_names)} reference images for testing")
        logger.info(f"Images: {', '.join(image_names)}")

    # ============================================================
    # Step 2: View selection
    # ============================================================
    logger.info("-" * 40)
    logger.info("Step 2: Selecting source views using sparse point visibility")
    from mvs.view_selection import select_source_views_by_visibility, export_view_pairs

    source_view_num = mvs_config.get('source_view_num', 3)
    view_pairs, visibility = select_source_views_by_visibility(
        tracks, image_names, source_view_num=source_view_num, logger=logger
    )
    export_view_pairs(view_pairs, os.path.join(dense_dir, 'view_pairs.json'), logger=logger)

    # ============================================================
    # Step 3: Depth range estimation
    # ============================================================
    logger.info("-" * 40)
    logger.info("Step 3: Estimating depth ranges from sparse points")
    from mvs.depth_range import estimate_depth_ranges, export_depth_ranges

    depth_ranges = estimate_depth_ranges(
        poses, points3D, tracks, image_names,
        percentile_min=mvs_config.get('depth_percentile_min', 5),
        percentile_max=mvs_config.get('depth_percentile_max', 95),
        expansion_factor_min=0.9,
        expansion_factor_max=1.1,
        logger=logger
    )
    export_depth_ranges(depth_ranges, os.path.join(dense_dir, 'depth_ranges.json'), logger=logger)

    # ============================================================
    # Step 4: Build seed masks from sparse point projections
    # ============================================================
    logger.info("-" * 40)
    logger.info("Step 4: Building seed pixel masks from sparse 3D point projections")
    from mvs.plane_sweep import build_sparse_pixel_mask

    seed_pixel_radius = mvs_config.get('seed_pixel_radius', 30)
    seed_masks = {}
    for img_name in image_names:
        mask = build_sparse_pixel_mask(
            points3D, tracks, poses, K, img_name, pixel_radius=seed_pixel_radius
        )
        seed_masks[img_name] = mask
        if logger:
            logger.info(f"  {img_name}: {np.sum(mask)} seed pixels (radius={seed_pixel_radius})")

    # ============================================================
    # Step 5: Plane sweep depth estimation
    # ============================================================
    logger.info("-" * 40)
    logger.info("Step 5: Running plane sweep depth estimation on seed pixels")
    from mvs.plane_sweep import run_plane_sweep_all

    t_mvs_start = time.time()
    depth_maps, confidence_maps = run_plane_sweep_all(
        image_names, view_pairs, K, poses, depth_ranges,
        image_dir, dense_dir, mvs_config, seed_masks=seed_masks, logger=logger
    )
    t_mvs_elapsed = time.time() - t_mvs_start
    logger.info(f"Plane sweep completed in {t_mvs_elapsed:.1f}s "
                f"({t_mvs_elapsed/60:.1f} min)")

    # ============================================================
    # Step 6: Depth map filtering
    # ============================================================
    logger.info("-" * 40)
    logger.info("Step 6: Filtering depth maps")
    from mvs.depth_filter import filter_all_depth_maps, save_filtered_depth_maps

    filtered_maps = filter_all_depth_maps(
        depth_maps, confidence_maps, depth_ranges,
        zncc_threshold=mvs_config.get('zncc_threshold', 0.5),
        apply_median_filter=False,
        image_names=image_names,
        logger=logger
    )

    save_filtered_depth_maps(
        filtered_maps,
        os.path.join(dense_dir, 'depth_maps_filtered'),
        logger=logger
    )

    # ============================================================
    # Step 7: Depth to partial point clouds
    # ============================================================
    logger.info("-" * 40)
    logger.info("Step 7: Generating partial point clouds from depth maps")
    from mvs.depth_to_pointcloud import generate_all_partial_clouds

    partial_clouds = generate_all_partial_clouds(
        filtered_maps, image_dir, K, poses, image_names,
        os.path.join(dense_dir, 'partial_pointclouds'),
        logger=logger
    )

    # ============================================================
    # Step 8: Point cloud fusion
    # ============================================================
    logger.info("-" * 40)
    logger.info("Step 8: Fusing partial point clouds into dense.ply")
    from mvs.pointcloud_fusion import fuse_and_export

    pcd = fuse_and_export(
        partial_clouds,
        os.path.join(dense_dir, 'dense.ply'),
        voxel_size=fusion_config.get('voxel_size', 0.02),
        nb_neighbors=fusion_config.get('outlier_nb_neighbors', 20),
        std_ratio=fusion_config.get('outlier_std_ratio', 2.0),
        logger=logger
    )

    # ============================================================
    # Summary
    # ============================================================
    logger.info("=" * 60)
    logger.info("MVS Pipeline Summary")
    logger.info("=" * 60)
    logger.info(f"Registered images: {len(image_names)}")
    logger.info(f"Depth maps generated: {len(depth_maps)}")
    logger.info(f"Confidence maps generated: {len(confidence_maps)}")
    logger.info(f"Filtered depth maps: {len(filtered_maps)}")
    logger.info(f"Partial point clouds: {len(partial_clouds)}")

    total_depth_pixels = sum(np.count_nonzero(d > 1e-6) for d in depth_maps.values())
    total_conf_pixels = sum(np.count_nonzero(c > mvs_config.get('zncc_threshold', 0.5))
                           for c in confidence_maps.values())
    total_filtered_pixels = sum(np.count_nonzero(d > 1e-6) for d in filtered_maps.values())
    total_partial_points = sum(len(pc[0]) for pc in partial_clouds.values())

    logger.info(f"Total valid depth pixels (raw): {total_depth_pixels}")
    logger.info(f"Total valid depth pixels (filtered): {total_filtered_pixels}")
    logger.info(f"Total partial points: {total_partial_points}")

    if pcd is not None:
        logger.info(f"Final dense.ply points: {len(pcd.points)}")
    else:
        logger.warning("dense.ply was not generated")

    logger.info(f"Total MVS time: {t_mvs_elapsed:.1f}s ({t_mvs_elapsed/60:.1f} min)")

    # Verify output files
    logger.info("-" * 40)
    logger.info("Output file check:")
    output_files = [
        os.path.join(dense_dir, 'view_pairs.json'),
        os.path.join(dense_dir, 'depth_ranges.json'),
        os.path.join(dense_dir, 'dense.ply'),
    ]
    for f in output_files:
        exists = os.path.exists(f)
        logger.info(f"  {f}: {'EXISTS' if exists else 'MISSING'}")

    # Count files in directories
    for subdir in ['depth_maps', 'confidence_maps', 'depth_maps_filtered', 'partial_pointclouds']:
        d = os.path.join(dense_dir, subdir)
        if os.path.isdir(d):
            n_files = len([f for f in os.listdir(d) if f.endswith('.npy') or f.endswith('.ply')])
            logger.info(f"  {d}: {n_files} files")

    logger.info("MVS pipeline completed.")


if __name__ == '__main__':
    main()
