#!/usr/bin/env python3
"""
Main script for Incremental Structure-from-Motion (SfM) pipeline.

Usage:
    python main_sfm.py --config config.yaml
"""

import os
import sys
import argparse
import time
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sfm.utils import (
    load_config, ensure_dir, get_image_files, compute_K, setup_logging
)
from sfm.image_preprocess import preprocess_images
from sfm.feature_extractor import extract_features
from sfm.feature_matcher import match_features
from sfm.geometric_verification import verify_matches
from sfm.initialization import select_initial_pair, recover_initial_pose
from sfm.triangulation import triangulate_points
from sfm.incremental_sfm import incremental_registration
from sfm.export_sparse import (
    export_sparse_ply, compute_point_colors,
    export_camera_poses, export_cameras_json,
    export_points3D_json, export_tracks_json
)


def main():
    parser = argparse.ArgumentParser(description='Incremental SfM Pipeline')
    parser.add_argument('--config', type=str, default='config.yaml',
                        help='Path to config YAML file')
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)
    project_root = os.path.dirname(os.path.abspath(__file__))

    # Setup logging
    log_path = os.path.join(project_root, config['paths']['results_dir'], 'logs', 'sfm_log.txt')
    logger = setup_logging(log_path)
    logger.info("=" * 60)
    logger.info("Incremental SfM Pipeline Started")
    logger.info("=" * 60)
    logger.info(f"Config: {args.config}")

    start_time = time.time()

    # Paths
    image_dir = os.path.join(project_root, config['paths']['image_dir'])
    results_dir = os.path.join(project_root, config['paths']['results_dir'])
    resized_dir = os.path.join(project_root, 'data', 'images_resized')

    features_dir = os.path.join(results_dir, 'features')
    matches_dir = os.path.join(results_dir, 'matches')
    verified_dir = os.path.join(results_dir, 'matches_verified')
    sparse_dir = os.path.join(results_dir, 'sparse')

    # Ensure directories exist
    for d in [features_dir, matches_dir, verified_dir, sparse_dir, resized_dir]:
        ensure_dir(d)

    # Parameters from config
    resize_width = config['image']['resize_width']
    max_features = config['sift']['max_features']
    ratio_threshold = config['matching']['ratio_threshold']
    neighbor_range = config['matching']['neighbor_range']
    reproj_threshold = config['sfm']['reprojection_error_threshold']
    pnp_min_inliers = config['sfm']['pnp_min_inliers']
    fx_scale = config['camera']['fx_scale']

    logger.info(f"Parameters: resize_width={resize_width}, max_features={max_features}, "
                f"ratio_threshold={ratio_threshold}, neighbor_range={neighbor_range}, "
                f"reproj_threshold={reproj_threshold}, pnp_min_inliers={pnp_min_inliers}, "
                f"fx_scale={fx_scale}")

    # =============================================
    # Step 1: Image Preprocessing
    # =============================================
    logger.info("-" * 60)
    logger.info("Step 1: Image Preprocessing")
    logger.info("-" * 60)
    try:
        image_files = preprocess_images(image_dir, resized_dir, resize_width, logger=logger)
        logger.info(f"Preprocessed {len(image_files)} images")
    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        raise

    # Compute resized image dimensions
    sample_img_path = os.path.join(resized_dir, image_files[0])
    import cv2
    sample_img = cv2.imread(sample_img_path)
    img_h, img_w = sample_img.shape[:2]
    logger.info(f"Resized image dimensions: {img_w}x{img_h}")

    # Compute intrinsic matrix K
    K = compute_K(img_w, img_h, fx_scale=fx_scale)
    logger.info(f"Intrinsic matrix K:\n{K}")
    logger.info(f"  fx={K[0,0]:.1f}, fy={K[1,1]:.1f}, cx={K[0,2]:.1f}, cy={K[1,2]:.1f}")

    # =============================================
    # Step 2: SIFT Feature Extraction
    # =============================================
    logger.info("-" * 60)
    logger.info("Step 2: SIFT Feature Extraction")
    logger.info("-" * 60)
    try:
        features = extract_features(resized_dir, image_files, features_dir,
                                    max_features=max_features, logger=logger)
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        raise

    # =============================================
    # Step 3: Feature Matching
    # =============================================
    logger.info("-" * 60)
    logger.info("Step 3: Feature Matching")
    logger.info("-" * 60)
    try:
        matches_dict = match_features(features, image_files, matches_dir,
                                      ratio_threshold=ratio_threshold,
                                      neighbor_range=neighbor_range,
                                      logger=logger)
    except Exception as e:
        logger.error(f"Feature matching failed: {e}")
        raise

    if len(matches_dict) == 0:
        logger.error("No matches found between any image pairs. Aborting.")
        sys.exit(1)

    # =============================================
    # Step 4: RANSAC Geometric Verification
    # =============================================
    logger.info("-" * 60)
    logger.info("Step 4: RANSAC Geometric Verification")
    logger.info("-" * 60)
    try:
        verified_dict, stats_dict = verify_matches(features, matches_dict, K,
                                                   verified_dir, logger=logger)
    except Exception as e:
        logger.error(f"Geometric verification failed: {e}")
        raise

    if len(verified_dict) == 0:
        logger.error("No verified pairs after RANSAC filtering. Aborting.")
        sys.exit(1)

    # =============================================
    # Step 5: Initial Pair Selection
    # =============================================
    logger.info("-" * 60)
    logger.info("Step 5: Initial Pair Selection")
    logger.info("-" * 60)
    img1, img2, init_inliers, num_inliers, inlier_ratio = select_initial_pair(
        verified_dict, stats_dict, logger=logger
    )

    # Save initial pair
    init_pair_path = os.path.join(sparse_dir, 'initial_pair.txt')
    ensure_dir(sparse_dir)
    with open(init_pair_path, 'w') as f:
        f.write(f"{img1} {img2}\n")
    logger.info(f"Saved initial pair to {init_pair_path}")

    # =============================================
    # Step 6: Initial Pose Recovery
    # =============================================
    logger.info("-" * 60)
    logger.info("Step 6: Initial Pose Recovery")
    logger.info("-" * 60)
    try:
        cameras, num_pose_inliers = recover_initial_pose(
            features, img1, img2, init_inliers, K, logger=logger
        )
    except Exception as e:
        logger.error(f"Initial pose recovery failed: {e}")
        raise

    # =============================================
    # Step 7: Initial Triangulation
    # =============================================
    logger.info("-" * 60)
    logger.info("Step 7: Initial Triangulation")
    logger.info("-" * 60)

    kp1 = features[img1][0]
    kp2 = features[img2][0]
    R1, t1 = cameras[img1]
    R2, t2 = cameras[img2]

    # Use RANSAC-verified inliers for triangulation
    # The cameras were already recovered in recover_initial_pose with
    # proper cheirality check. Depth check in triangulation filters bad points.
    points_3d_init, valid_mask_init, init_errors = triangulate_points(
        kp1, kp2, init_inliers, K, R1, t1, R2, t2,
        reproj_threshold=reproj_threshold, logger=logger
    )

    pose_inliers = init_inliers[valid_mask_init]

    if len(points_3d_init) == 0:
        logger.error("Initial triangulation produced 0 valid points. Aborting.")
        sys.exit(1)

    logger.info(f"Initial triangulation: {len(points_3d_init)} valid points "
                f"(mean reproj error: {np.mean(init_errors):.3f}px)")

    # Initialize tracks
    tracks = {}
    kp_to_point = {}
    points3D = {}

    for i in range(len(points_3d_init)):
        pt_id = i
        points3D[pt_id] = {
            'xyz': points_3d_init[i].tolist(),
            'color': [128, 128, 128],
            'error': float(init_errors[i]) if i < len(init_errors) else 0.0
        }
        tracks[pt_id] = [
            (img1, int(pose_inliers[i, 0])),
            (img2, int(pose_inliers[i, 1]))
        ]
        kp_to_point[(img1, int(pose_inliers[i, 0]))] = pt_id
        kp_to_point[(img2, int(pose_inliers[i, 1]))] = pt_id

    logger.info(f"Initialized {len(points3D)} points and {len(tracks)} tracks")

    # Export initial sparse point cloud
    export_sparse_ply(points3D, os.path.join(sparse_dir, 'initial_sparse.ply'), logger=logger)

    # =============================================
    # Step 8: Incremental SfM Registration
    # =============================================
    logger.info("-" * 60)
    logger.info("Step 8: Incremental SfM Registration")
    logger.info("-" * 60)
    try:
        newly_registered = incremental_registration(
            features, verified_dict, image_files, K, cameras,
            tracks, kp_to_point, points3D,
            reproj_threshold=reproj_threshold,
            pnp_min_inliers=pnp_min_inliers,
            logger=logger
        )
    except Exception as e:
        logger.error(f"Incremental registration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

    # =============================================
    # Step 9: Compute Point Colors
    # =============================================
    logger.info("-" * 60)
    logger.info("Step 9: Computing Point Colors")
    logger.info("-" * 60)
    compute_point_colors(features, image_files, tracks, points3D, logger=logger)

    # =============================================
    # Step 10: Export Results
    # =============================================
    logger.info("-" * 60)
    logger.info("Step 10: Exporting Results")
    logger.info("-" * 60)

    # Export sparse.ply (final)
    sparse_ply_path = os.path.join(sparse_dir, 'sparse.ply')
    export_sparse_ply(points3D, sparse_ply_path, logger=logger)

    # Export camera_poses.txt
    camera_poses_path = os.path.join(sparse_dir, 'camera_poses.txt')
    export_camera_poses(cameras, camera_poses_path, logger=logger)

    # Export cameras.json
    cameras_json_path = os.path.join(sparse_dir, 'cameras.json')
    export_cameras_json(cameras, K, cameras_json_path, logger=logger)

    # Export points3D.json
    points3d_json_path = os.path.join(sparse_dir, 'points3D.json')
    export_points3D_json(points3D, points3d_json_path, logger=logger)

    # Export tracks.json
    tracks_json_path = os.path.join(sparse_dir, 'tracks.json')
    export_tracks_json(tracks, tracks_json_path, logger=logger)

    # =============================================
    # Summary
    # =============================================
    elapsed = time.time() - start_time
    num_registered = len(cameras)
    num_images = len(image_files)
    reg_pct = 100.0 * num_registered / num_images

    # Compute approximate mean reprojection error
    all_errors = [pt['error'] for pt in points3D.values() if pt.get('error', 0) > 0]
    mean_error = np.mean(all_errors) if all_errors else 0.0

    logger.info("=" * 60)
    logger.info("SfM Pipeline Summary")
    logger.info("=" * 60)
    logger.info(f"Total images: {num_images}")
    logger.info(f"Registered images: {num_registered} ({reg_pct:.1f}%)")
    logger.info(f"Total 3D points: {len(points3D)}")
    logger.info(f"Total tracks: {len(tracks)}")
    logger.info(f"Mean reprojection error: {mean_error:.3f} px")
    logger.info(f"Elapsed time: {elapsed:.1f}s")
    logger.info(f"Acceptance: {'PASS' if reg_pct >= 60.0 else 'FAIL'} "
                f"(need >= 60%, got {reg_pct:.1f}%)")

    # Print to console as well
    print(f"\n{'='*60}")
    print(f"SfM Pipeline Complete")
    print(f"{'='*60}")
    print(f"Registered: {num_registered}/{num_images} images ({reg_pct:.1f}%)")
    print(f"3D Points: {len(points3D)}")
    print(f"Mean reproj error: {mean_error:.3f} px")
    print(f"Time: {elapsed:.1f}s")
    print(f"Output: {sparse_ply_path}")
    print(f"{'='*60}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
