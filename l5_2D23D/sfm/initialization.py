"""
Initialization module for SfM.
Selects the best initial image pair and recovers relative camera pose.
"""

import os
import cv2
import numpy as np
from sfm.utils import ensure_dir, get_keypoint_coords


def select_initial_pair(verified_dict, stats_dict, logger=None):
    """Select the best image pair for initialization.

    Score for pair (i, j) = num_inliers * inlier_ratio.
    Returns the pair with the highest score.

    Args:
        verified_dict: dict mapping (img1, img2) -> inliers array.
        stats_dict: dict mapping (img1, img2) -> (num_inliers, inlier_ratio).
        logger: Optional logger instance.

    Returns:
        (img1, img2, inliers_array, num_inliers, inlier_ratio)
    """
    if not stats_dict:
        raise RuntimeError("No verified pairs available for initialization")

    best_score = -1
    best_pair = None
    best_inliers = None
    best_num = 0
    best_ratio = 0

    for pair, (num_inliers, inlier_ratio) in stats_dict.items():
        # Extract image indices for baseline calculation
        img1_name = os.path.splitext(pair[0])[0]
        img2_name = os.path.splitext(pair[1])[0]
        try:
            idx1 = int(img1_name)
            idx2 = int(img2_name)
            index_gap = abs(idx2 - idx1)
        except ValueError:
            index_gap = 1

        # Score favors: many inliers, good ratio (not too high = wider baseline),
        # and wider index gap for better coverage
        # Penalize very high inlier ratios (close to 1.0 = tiny baseline)
        baseline_factor = min(inlier_ratio, 1.0 - inlier_ratio) * 2.0  # peaks at 0.5 ratio
        score = num_inliers * baseline_factor * index_gap
        if score > best_score:
            best_score = score
            best_pair = pair
            best_inliers = verified_dict[pair]
            best_num = num_inliers
            best_ratio = inlier_ratio

    if logger:
        logger.info(f"Selected initial pair: {best_pair[0]} <-> {best_pair[1]}")
        logger.info(f"  Score: {best_score:.1f} (inliers={best_num}, ratio={best_ratio:.4f})")

    return best_pair[0], best_pair[1], best_inliers, best_num, best_ratio


def recover_initial_pose(features, img1, img2, inliers, K, logger=None):
    """Recover relative camera pose from essential matrix decomposition.

    Uses cv2.recoverPose with cheirality check.
    First camera: R = I, t = 0
    Second camera: R = recovered R, t = recovered t

    Args:
        features: dict mapping image_name -> (keypoints, descriptors).
        img1: First image filename.
        img2: Second image filename.
        inliers: Nx2 array of inlier keypoint index pairs.
        K: 3x3 intrinsic matrix.
        logger: Optional logger instance.

    Returns:
        dict: {'img1': (R1_3x3, t1_3x1), 'img2': (R2_3x3, t2_3x1)}
        float: number of inliers after recoverPose
    """
    kp1_list = features[img1][0]
    kp2_list = features[img2][0]

    pts1 = np.array([kp1_list[m[0]].pt for m in inliers], dtype=np.float64)
    pts2 = np.array([kp2_list[m[1]].pt for m in inliers], dtype=np.float64)

    # Compute Essential Matrix and recover pose
    # Pass pixel coordinates + K; OpenCV normalizes internally
    E, mask = cv2.findEssentialMat(
        pts1, pts2, K, method=cv2.RANSAC,
        prob=0.999, threshold=3.0
    )

    _, R, t, mask_pose = cv2.recoverPose(E, pts1, pts2, K, mask=mask)

    num_inliers_pose = int(mask_pose.sum()) if mask_pose is not None else 0

    cameras = {
        img1: (np.eye(3, dtype=np.float64), np.zeros((3, 1), dtype=np.float64)),
        img2: (R.astype(np.float64), t.astype(np.float64))
    }

    if logger:
        logger.info(f"Recovered initial pose:")
        logger.info(f"  {img1}: R=I, t=[0,0,0]")
        logger.info(f"  {img2}: R={R.ravel()}, t={t.ravel()}")
        logger.info(f"  Pose inliers: {num_inliers_pose}")

    return cameras, num_inliers_pose
