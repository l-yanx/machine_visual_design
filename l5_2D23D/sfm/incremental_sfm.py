"""
Incremental SfM module.
Registers remaining images incrementally, triangulates new points, and updates tracks.
Uses multi-pass strategy to maximize registration coverage.
"""

import numpy as np
from sfm.pnp_registration import estimate_pose_pnp
from sfm.triangulation import multi_view_triangulate


def _try_register_image(img_name, features, verified_dict, registered_set, cameras,
                        K, tracks, kp_to_point, points3D, max_point_id,
                        reproj_threshold, pnp_min_inliers, logger):
    """Attempt to register a single image. Returns (success, max_point_id)."""
    kp_new_list = features[img_name][0]

    # Find registered images that have verified matches with this image
    candidate_pairs = []
    for (img_a, img_b), inliers in verified_dict.items():
        if img_a == img_name and img_b in registered_set:
            candidate_pairs.append((img_b, inliers, False))
        elif img_b == img_name and img_a in registered_set:
            candidate_pairs.append((img_a, inliers, True))

    if not candidate_pairs:
        if logger:
            logger.debug(f"  {img_name}: No registered neighbors with verified matches")
        return False, max_point_id

    # Build 2D-3D correspondences, filtering by point quality
    points_3d_list = []
    points_2d_list = []

    for img_reg, inliers, swapped in candidate_pairs:
        kp_reg_list = features[img_reg][0]

        for match in inliers:
            if swapped:
                kp_idx_reg, kp_idx_new = int(match[0]), int(match[1])
            else:
                kp_idx_new, kp_idx_reg = int(match[0]), int(match[1])

            # Check if registered keypoint maps to a 3D point
            key = (img_reg, kp_idx_reg)
            if key in kp_to_point:
                pt_id = kp_to_point[key]
                # Skip low-quality points for PnP
                if points3D[pt_id].get('error', 0) > 4.0:
                    continue
                pt_3d = points3D[pt_id]['xyz']
                # Skip points with huge coordinates (likely outliers)
                if np.linalg.norm(pt_3d) > 500:
                    continue
                points_3d_list.append(pt_3d)
                kp = kp_new_list[kp_idx_new]
                points_2d_list.append([kp.pt[0], kp.pt[1]])

    if len(points_3d_list) < 6:
        if logger:
            logger.debug(f"  {img_name}: Only {len(points_3d_list)} 2D-3D correspondences")
        return False, max_point_id

    # PnP pose estimation
    R, t, num_pnp_inliers = estimate_pose_pnp(
        np.array(points_3d_list), np.array(points_2d_list), K,
        min_inliers=pnp_min_inliers, reproj_error=reproj_threshold, logger=None
    )

    if R is None:
        if logger:
            logger.debug(f"  {img_name}: PnP failed with {len(points_3d_list)} correspondences")
        return False, max_point_id

    # Register the image
    cameras[img_name] = (R, t)
    registered_set.add(img_name)

    if logger:
        logger.info(f"  Registered {img_name} ({num_pnp_inliers} PnP inliers, "
                     f"from {len(candidate_pairs)} neighbors, {len(points_3d_list)} corrs)")

    # Add corresponding 3D point observations for the new image
    for img_reg, inliers, swapped in candidate_pairs:
        for match in inliers:
            if swapped:
                kp_idx_reg, kp_idx_new = int(match[0]), int(match[1])
            else:
                kp_idx_new, kp_idx_reg = int(match[0]), int(match[1])

            key = (img_reg, kp_idx_reg)
            if key in kp_to_point:
                pt_id = kp_to_point[key]
                tracks[pt_id].append((img_name, kp_idx_new))
                new_key = (img_name, kp_idx_new)
                if new_key not in kp_to_point:
                    kp_to_point[new_key] = pt_id

    # Triangulate new points with registered neighbors
    for img_reg, inliers, swapped in candidate_pairs:
        new_matches = []
        for match in inliers:
            if swapped:
                kp_idx_reg, kp_idx_new = int(match[0]), int(match[1])
            else:
                kp_idx_new, kp_idx_reg = int(match[0]), int(match[1])

            key_new = (img_name, kp_idx_new)
            key_reg = (img_reg, kp_idx_reg)

            if key_new not in kp_to_point and key_reg not in kp_to_point:
                new_matches.append([kp_idx_new, kp_idx_reg])

        if len(new_matches) == 0:
            continue

        new_matches = np.array(new_matches, dtype=np.int32)
        points_3d_new, valid_matches = multi_view_triangulate(
            features, img_name, img_reg, new_matches, K, cameras,
            reproj_threshold=reproj_threshold, logger=None
        )

        for j in range(len(points_3d_new)):
            pt_xyz = points_3d_new[j]
            kp_idx_new_pt = int(valid_matches[j, 0])
            kp_idx_reg_pt = int(valid_matches[j, 1])

            pt_id = max_point_id
            max_point_id += 1

            points3D[pt_id] = {
                'xyz': pt_xyz.tolist(),
                'color': [128, 128, 128],
                'error': 0.0
            }

            tracks[pt_id] = [
                (img_name, kp_idx_new_pt),
                (img_reg, kp_idx_reg_pt)
            ]

            kp_to_point[(img_name, kp_idx_new_pt)] = pt_id
            kp_to_point[(img_reg, kp_idx_reg_pt)] = pt_id

    return True, max_point_id


def incremental_registration(features, verified_dict, image_files, K, cameras,
                             tracks, kp_to_point, points3D,
                             reproj_threshold=5.0, pnp_min_inliers=30,
                             logger=None):
    """Register remaining images incrementally with multi-pass strategy.

    Args:
        features: dict mapping image_name -> (keypoints, descriptors).
        verified_dict: dict mapping (img1, img2) -> inliers array.
        image_files: Ordered list of all image filenames.
        K: 3x3 intrinsic matrix.
        cameras: dict mapping image_name -> (R, t). Initially has two entries.
                 Modified in-place with newly registered cameras.
        tracks: dict mapping point_id -> list of (img_name, kp_idx).
                Modified in-place with new tracks.
        kp_to_point: dict mapping (img_name, kp_idx) -> point_id.
                     Modified in-place with new mappings.
        points3D: dict mapping point_id -> dict with xyz, color, error.
                  Modified in-place with new 3D points.
        reproj_threshold: Reprojection error threshold for PnP and triangulation.
        pnp_min_inliers: Minimum PnP inliers for registration.
        logger: Optional logger instance.

    Returns:
        int: number of newly registered images.
    """
    registered_set = set(cameras.keys())
    total_newly_registered = 0
    max_point_id = max(points3D.keys()) + 1 if points3D else 0

    if logger:
        logger.info(f"Starting incremental registration ({len(registered_set)} images registered)")
        logger.info(f"  PnP min inliers: {pnp_min_inliers}")
        logger.info(f"  Reprojection error threshold: {reproj_threshold}px")

    # Multi-pass: keep processing until no new images are registered in a full pass
    max_passes = 10
    for pass_num in range(1, max_passes + 1):
        pass_new = 0
        if logger:
            logger.info(f"--- Pass {pass_num} ({len(registered_set)} registered so far) ---")

        for img_name in image_files:
            if img_name in registered_set:
                continue

            success, max_point_id = _try_register_image(
                img_name, features, verified_dict, registered_set, cameras,
                K, tracks, kp_to_point, points3D, max_point_id,
                reproj_threshold, pnp_min_inliers, logger
            )

            if success:
                pass_new += 1
                total_newly_registered += 1

        if pass_new == 0:
            if logger:
                logger.info(f"No new registrations in pass {pass_num}, stopping")
            break

        if logger:
            logger.info(f"Pass {pass_num} done: {pass_new} new, "
                         f"total={len(registered_set)}/{len(image_files)}, "
                         f"points={len(points3D)}, tracks={len(tracks)}")

    if logger:
        logger.info(f"Incremental registration complete: {total_newly_registered} new images")
        logger.info(f"Total registered: {len(registered_set)}/{len(image_files)}")

    return total_newly_registered
