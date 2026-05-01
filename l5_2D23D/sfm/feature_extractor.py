"""
SIFT feature extraction module.
Extracts keypoints and descriptors for each image.
"""

import os
import cv2
import numpy as np
from sfm.utils import ensure_dir, save_keypoints


def extract_features(image_dir, image_files, output_dir, max_features=4000, logger=None):
    """Extract SIFT keypoints and descriptors for each image.

    Args:
        image_dir: Path to directory containing images.
        image_files: List of image filenames.
        output_dir: Directory to save keypoints and descriptors.
        max_features: Maximum number of SIFT features to retain.
        logger: Optional logger instance.

    Returns:
        dict mapping image_name to (keypoints_list, descriptors_array)
    """
    ensure_dir(output_dir)
    sift = cv2.SIFT_create(nfeatures=max_features)
    features = {}

    if logger:
        logger.info(f"Extracting SIFT features (max_features={max_features})")

    for fname in image_files:
        img_path = os.path.join(image_dir, fname)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            if logger:
                logger.warning(f"Could not read {img_path}, skipping")
            continue

        keypoints, descriptors = sift.detectAndCompute(img, None)

        if descriptors is None:
            if logger:
                logger.warning(f"No features found in {fname}")
            keypoints = []
            descriptors = np.array([])
        else:
            if logger:
                logger.debug(f"  {fname}: {len(keypoints)} keypoints, "
                             f"descriptors shape={descriptors.shape}")

        features[fname] = (keypoints, descriptors)

        # Save keypoints and descriptors
        basename = os.path.splitext(fname)[0]
        kp_path = os.path.join(output_dir, f"{basename}_keypoints.npy")
        desc_path = os.path.join(output_dir, f"{basename}_descriptors.npy")

        save_keypoints(kp_path, keypoints)
        np.save(desc_path, descriptors)

    if logger:
        logger.info(f"Extracted features for {len(features)} images")
        if features:
            avg_kp = int(np.mean([len(v[0]) for v in features.values()]))
            logger.info(f"Average keypoints per image: {avg_kp}")

    return features
