"""
Feature matching module.
Performs sequential KNN matching with Lowe ratio test between image pairs.
"""

import os
import cv2
import numpy as np
from sfm.utils import ensure_dir


def match_features(features, image_files, output_dir, ratio_threshold=0.75,
                   neighbor_range=3, logger=None):
    """Match SIFT descriptors sequentially using KNN + Lowe ratio test.

    For image i, match with i+1, i+2, ..., i+neighbor_range.

    Args:
        features: dict mapping image_name to (keypoints, descriptors).
        image_files: Ordered list of image filenames.
        output_dir: Directory to save match files.
        ratio_threshold: Lowe ratio test threshold.
        neighbor_range: How many subsequent images to match with.
        logger: Optional logger instance.

    Returns:
        dict mapping (img1, img2) -> array of [kp_idx1, kp_idx2] matches.
    """
    ensure_dir(output_dir)
    matches_dict = {}
    total_pairs = 0

    if logger:
        logger.info(f"Matching features: KNN + Lowe ratio test "
                     f"(ratio={ratio_threshold}, neighbor_range={neighbor_range})")

    # FLANN matcher for SIFT
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)

    n_images = len(image_files)

    for i in range(n_images):
        fname_i = image_files[i]
        if fname_i not in features:
            continue
        _, desc_i = features[fname_i]
        if desc_i is None or len(desc_i) == 0:
            continue

        for j in range(i + 1, min(i + 1 + neighbor_range, n_images)):
            fname_j = image_files[j]
            if fname_j not in features:
                continue
            _, desc_j = features[fname_j]
            if desc_j is None or len(desc_j) == 0:
                continue

            # KNN matching
            matches = flann.knnMatch(desc_i, desc_j, k=2)

            # Lowe ratio test
            good_matches = []
            for m, n in matches:
                if m.distance < ratio_threshold * n.distance:
                    good_matches.append([m.queryIdx, m.trainIdx])

            if len(good_matches) == 0:
                if logger:
                    logger.debug(f"  {fname_i} <-> {fname_j}: 0 matches after ratio test")
                continue

            good_matches = np.array(good_matches, dtype=np.int32)
            matches_dict[(fname_i, fname_j)] = good_matches
            total_pairs += 1

            # Save matches
            basename_i = os.path.splitext(fname_i)[0]
            basename_j = os.path.splitext(fname_j)[0]
            match_path = os.path.join(output_dir, f"match_{basename_i}_{basename_j}.npy")
            np.save(match_path, good_matches)

            if logger:
                logger.debug(f"  {fname_i} <-> {fname_j}: {len(good_matches)} matches")

    if logger:
        logger.info(f"Matched {total_pairs} pairs, "
                     f"avg matches: {np.mean([len(v) for v in matches_dict.values()]):.1f}" if matches_dict else "No matches")

    return matches_dict
