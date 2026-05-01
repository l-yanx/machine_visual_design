"""
Geometric verification module.
Uses RANSAC + Essential Matrix to filter outlier matches.
"""

import os
import cv2
import numpy as np
from sfm.utils import ensure_dir, get_keypoint_coords


def verify_matches(features, matches_dict, K, output_dir, logger=None):
    """Perform RANSAC geometric verification for all matched pairs.

    Uses RANSAC + Essential Matrix to filter outliers.

    Args:
        features: dict mapping image_name -> (keypoints, descriptors).
        matches_dict: dict mapping (img1, img2) -> array of [kp_idx1, kp_idx2].
        K: 3x3 intrinsic matrix.
        output_dir: Directory to save verified inlier files.
        logger: Optional logger instance.

    Returns:
        dict mapping (img1, img2) -> array of [kp_idx1, kp_idx2] inliers.
        dict mapping (img1, img2) -> (num_inliers, inlier_ratio).
    """
    ensure_dir(output_dir)
    verified_dict = {}
    stats_dict = {}

    if logger:
        logger.info("Performing RANSAC geometric verification (Essential Matrix)")

    K_inv = np.linalg.inv(K)

    for (img1, img2), matches in matches_dict.items():
        kp1_list = features[img1][0]
        kp2_list = features[img2][0]

        if len(matches) < 8:
            if logger:
                logger.debug(f"  {img1} <-> {img2}: only {len(matches)} matches, "
                             f"need at least 8 for Essential Matrix, skipping")
            continue

        # Extract matching keypoint coordinates (pixel coordinates)
        pts1 = np.array([kp1_list[m[0]].pt for m in matches], dtype=np.float64)
        pts2 = np.array([kp2_list[m[1]].pt for m in matches], dtype=np.float64)

        # RANSAC for Essential Matrix
        # Pass pixel coordinates + K; OpenCV normalizes internally
        # Threshold in pixels (distance to epipolar line)
        E, mask = cv2.findEssentialMat(
            pts1, pts2, K, method=cv2.RANSAC,
            prob=0.999, threshold=3.0
        )

        if mask is None:
            if logger:
                logger.debug(f"  {img1} <-> {img2}: Essential Matrix computation failed")
            continue

        mask = mask.ravel().astype(bool)
        inliers = matches[mask]
        num_inliers = len(inliers)
        inlier_ratio = num_inliers / len(matches) if len(matches) > 0 else 0

        if num_inliers < 8:
            if logger:
                logger.debug(f"  {img1} <-> {img2}: only {num_inliers} inliers, skipping")
            continue

        verified_dict[(img1, img2)] = inliers
        stats_dict[(img1, img2)] = (num_inliers, inlier_ratio)

        # Save inliers
        basename_i = os.path.splitext(img1)[0]
        basename_j = os.path.splitext(img2)[0]
        inlier_path = os.path.join(output_dir, f"inliers_{basename_i}_{basename_j}.npy")
        np.save(inlier_path, inliers)

        if logger:
            logger.debug(f"  {img1} <-> {img2}: {num_inliers}/{len(matches)} inliers "
                         f"({inlier_ratio:.2%})")

    if logger:
        logger.info(f"Verified {len(verified_dict)} pairs after RANSAC filtering")

    return verified_dict, stats_dict
