"""
PnP registration module.
Estimates camera pose for new images using PnP + RANSAC.
"""

import cv2
import numpy as np


def estimate_pose_pnp(points_3d, points_2d, K, min_inliers=30,
                      reproj_error=5.0, logger=None):
    """Estimate camera pose using PnP + RANSAC.

    Args:
        points_3d: Nx3 array of 3D world points.
        points_2d: Nx2 array of corresponding 2D image points.
        K: 3x3 intrinsic matrix.
        min_inliers: Minimum number of inliers for successful registration.
        reproj_error: RANSAC reprojection error threshold in pixels.
        logger: Optional logger instance.

    Returns:
        (R, t, num_inliers) if successful, or (None, None, 0) if failed.
    """
    if len(points_3d) < 6:
        if logger:
            logger.debug(f"  PnP: only {len(points_3d)} correspondences, need at least 6")
        return None, None, 0

    points_3d = np.asarray(points_3d, dtype=np.float64)
    points_2d = np.asarray(points_2d, dtype=np.float64)

    # Try multiple PnP methods with fallback
    rvec, tvec, inliers = None, None, None
    best_num_inliers = 0

    for method in [cv2.SOLVEPNP_EPNP, cv2.SOLVEPNP_ITERATIVE, cv2.SOLVEPNP_P3P]:
        if method == cv2.SOLVEPNP_P3P and len(points_3d) < 4:
            continue
        retval, rvec_try, tvec_try, inliers_try = cv2.solvePnPRansac(
            points_3d, points_2d, K, None,
            iterationsCount=2000,
            reprojectionError=reproj_error,
            confidence=0.999,
            flags=method
        )
        if retval and inliers_try is not None:
            n_inl = len(inliers_try)
            if n_inl > best_num_inliers:
                best_num_inliers = n_inl
                inliers = inliers_try
                # Refine with iterative
                inl_3d = points_3d[inliers_try.ravel()]
                inl_2d = points_2d[inliers_try.ravel()]
                _, rvec, tvec = cv2.solvePnP(
                    inl_3d, inl_2d, K, None,
                    rvec_try, tvec_try, useExtrinsicGuess=True,
                    flags=cv2.SOLVEPNP_ITERATIVE
                )
                if best_num_inliers >= min_inliers:
                    break  # Good enough

    if rvec is None or best_num_inliers < min_inliers:
        if logger:
            logger.debug(f"  PnP: best inliers={best_num_inliers}, need {min_inliers}")
        return None, None, 0

    num_inliers = best_num_inliers

    R, _ = cv2.Rodrigues(rvec)
    t = tvec.reshape(3, 1)

    # Sanity check: translation should be reasonable
    # Typical translations are < 10 units; reject clearly bogus values
    t_norm = np.linalg.norm(t)
    if t_norm > 500.0:
        if logger:
            logger.debug(f"  PnP: rejecting bogus pose (t_norm={t_norm:.1f})")
        return None, None, 0

    return R.astype(np.float64), t.astype(np.float64), num_inliers
