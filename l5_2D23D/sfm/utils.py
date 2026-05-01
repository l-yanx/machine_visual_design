"""
Utilities for the SfM pipeline.
"""

import os
import logging
import numpy as np
import yaml


def load_config(config_path):
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def ensure_dir(dir_path):
    """Create directory if it does not exist."""
    os.makedirs(dir_path, exist_ok=True)


def get_image_files(image_dir, extensions=('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')):
    """Get sorted list of image files from directory."""
    files = []
    for f in sorted(os.listdir(image_dir)):
        if f.lower().endswith(extensions):
            files.append(f)
    return files


def compute_K(image_width, image_height, fx_scale=1.2):
    """Compute intrinsic matrix K using approximate intrinsics.

    fx = fy = fx_scale * image_width
    cx = image_width / 2
    cy = image_height / 2
    """
    fx = fy = fx_scale * image_width
    cx = image_width / 2.0
    cy = image_height / 2.0
    K = np.array([
        [fx, 0, cx],
        [0, fy, cy],
        [0, 0, 1]
    ], dtype=np.float64)
    return K


def keypoints_to_array(keypoints):
    """Convert list of cv2.KeyPoint to numpy array.

    Columns: [x, y, size, angle, response, octave, class_id]
    """
    arr = np.zeros((len(keypoints), 7), dtype=np.float64)
    for i, kp in enumerate(keypoints):
        arr[i, 0] = kp.pt[0]      # x
        arr[i, 1] = kp.pt[1]      # y
        arr[i, 2] = kp.size       # size
        arr[i, 3] = kp.angle      # angle
        arr[i, 4] = kp.response   # response
        arr[i, 5] = kp.octave     # octave
        arr[i, 6] = kp.class_id   # class_id
    return arr


def array_to_keypoints(arr):
    """Convert numpy array back to list of cv2.KeyPoint.

    Expects columns: [x, y, size, angle, response, octave, class_id]
    """
    import cv2
    keypoints = []
    for row in arr:
        kp = cv2.KeyPoint(
            x=float(row[0]),
            y=float(row[1]),
            size=float(row[2]),
            angle=float(row[3]),
            response=float(row[4]),
            octave=int(row[5]),
            class_id=int(row[6])
        )
        keypoints.append(kp)
    return keypoints


def save_keypoints(filepath, keypoints):
    """Save keypoints as numpy array."""
    ensure_dir(os.path.dirname(filepath))
    arr = keypoints_to_array(keypoints)
    np.save(filepath, arr)


def load_keypoints(filepath):
    """Load keypoints from numpy array file.

    Returns list of cv2.KeyPoint objects.
    """
    arr = np.load(filepath)
    return array_to_keypoints(arr)


def setup_logging(log_path):
    """Set up logging to file and console."""
    ensure_dir(os.path.dirname(log_path))
    logger = logging.getLogger('sfm')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # File handler
    fh = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s',
                                     datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter('[%(levelname)s] %(message)s')
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    return logger


def get_keypoint_coords(keypoints):
    """Extract (x, y) coordinates from list of KeyPoint objects as Nx2 array."""
    coords = np.zeros((len(keypoints), 2), dtype=np.float64)
    for i, kp in enumerate(keypoints):
        coords[i, 0] = kp.pt[0]
        coords[i, 1] = kp.pt[1]
    return coords
