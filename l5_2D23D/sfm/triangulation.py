"""
Triangulation module for SfM.
Triangulates 3D points from two-view geometry with filtering.
"""

import numpy as np
import cv2


def triangulate_points(kp1_list, kp2_list, matches, K, R1, t1, R2, t2,
                       reproj_threshold=5.0, min_angle_deg=1.0, logger=None):
    """Triangulate 3D points from two views.

    Args:
        kp1_list: KeyPoint list for image 1.
        kp2_list: KeyPoint list for image 2.
        matches: Nx2 array of [kp_idx1, kp_idx2] matches.
        K: 3x3 intrinsic matrix.
        R1, t1: Camera 1 pose (world-to-camera).
        R2, t2: Camera 2 pose (world-to-camera).
        reproj_threshold: Maximum reprojection error in pixels.
        min_angle_deg: Minimum triangulation angle in degrees.
        logger: Optional logger instance.

    Returns:
        points_3d: Nx3 array of triangulated 3D points.
        valid_mask: Boolean array indicating which points passed filtering.
        reproj_errors: Array of reprojection errors for valid points.
    """
    if len(matches) == 0:
        return np.zeros((0, 3)), np.zeros(0, dtype=bool), np.zeros(0)

    # Build projection matrices: P = K [R | t]
    P1 = K @ np.hstack([R1, t1.reshape(3, 1)])
    P2 = K @ np.hstack([R2, t2.reshape(3, 1)])

    # Get matching keypoint coordinates
    pts1 = np.array([kp1_list[m[0]].pt for m in matches], dtype=np.float64).T  # 2xN
    pts2 = np.array([kp2_list[m[1]].pt for m in matches], dtype=np.float64).T  # 2xN

    # Triangulate
    points_4d = cv2.triangulatePoints(P1, P2, pts1, pts2)  # 4xN
    points_3d = points_4d[:3, :] / points_4d[3, :]  # 3xN
    points_3d = points_3d.T  # Nx3

    # Filtering
    N = len(matches)
    valid = np.ones(N, dtype=bool)
    reproj_errors = np.full(N, np.inf)

    for i in range(N):
        pt_3d = points_3d[i]
        if not np.isfinite(pt_3d).all():
            valid[i] = False
            continue

        # Positive depth check in both cameras
        # Camera 1: transform world point to camera coordinates
        pt_cam1 = R1 @ pt_3d + t1.ravel()
        if pt_cam1[2] <= 0:
            valid[i] = False
            continue

        # Camera 2:
        pt_cam2 = R2 @ pt_3d + t2.ravel()
        if pt_cam2[2] <= 0:
            valid[i] = False
            continue

        # Reprojection error
        proj1 = P1 @ np.append(pt_3d, 1.0)
        proj1 = proj1[:2] / proj1[2]
        err1 = np.linalg.norm(proj1 - pts1[:, i])

        proj2 = P2 @ np.append(pt_3d, 1.0)
        proj2 = proj2[:2] / proj2[2]
        err2 = np.linalg.norm(proj2 - pts2[:, i])

        avg_err = (err1 + err2) / 2.0

        if avg_err > reproj_threshold:
            valid[i] = False
            continue

        reproj_errors[i] = avg_err

    points_3d_valid = points_3d[valid]
    reproj_errors_valid = reproj_errors[valid]

    if logger:
        logger.debug(f"  Triangulation: {len(points_3d_valid)}/{N} points valid "
                     f"(mean reproj err: {np.mean(reproj_errors_valid):.2f}px)" if len(reproj_errors_valid) > 0 else "  Triangulation: 0 valid points")

    return points_3d_valid, valid, reproj_errors_valid


def multi_view_triangulate(features, img_new, img_reg, matches, K, cameras,
                           reproj_threshold=5.0, logger=None):
    """Triangulate new points between a new image and a registered image.

    Args:
        features: dict mapping image_name -> (keypoints, descriptors).
        img_new: New (just registered) image filename.
        img_reg: Already registered image filename.
        matches: Nx2 array of [kp_idx_new, kp_idx_reg] matches.
        K: 3x3 intrinsic matrix.
        cameras: dict mapping image_name -> (R, t).
        reproj_threshold: Maximum reprojection error in pixels.
        logger: Optional logger instance.

    Returns:
        points_3d: Mx3 array of valid triangulated points.
        match_indices: Mx2 array of [kp_idx_new, kp_idx_reg] for valid points.
    """
    kp_new = features[img_new][0]
    kp_reg = features[img_reg][0]
    R_new, t_new = cameras[img_new]
    R_reg, t_reg = cameras[img_reg]

    points_3d, valid_mask, _ = triangulate_points(
        kp_new, kp_reg, matches, K, R_new, t_new, R_reg, t_reg,
        reproj_threshold=reproj_threshold, logger=logger
    )

    valid_matches = matches[valid_mask]
    return points_3d, valid_matches
