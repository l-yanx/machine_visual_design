"""
Read SfM results module.
Reads camera intrinsics, camera poses, sparse 3D points, and tracks from Task 1 outputs.
"""

import os
import json
import numpy as np


def read_cameras(cameras_path):
    """Read cameras.json and return:
    - K: 3x3 intrinsic matrix (all cameras share the same K)
    - poses: dict mapping image_name -> {'R': 3x3, 't': (3,)}
    - image_names: sorted list of registered image names

    Args:
        cameras_path: Path to cameras.json.

    Returns:
        K (np.ndarray 3x3), poses (dict), image_names (list of str)
    """
    with open(cameras_path, 'r') as f:
        data = json.load(f)

    K = None
    poses = {}
    image_names = sorted(data.keys())

    for img_name in sorted(data.keys()):
        cam = data[img_name]
        if K is None:
            K = np.array(cam['K'], dtype=np.float64)
        R = np.array(cam['R'], dtype=np.float64)
        t = np.array(cam['t'], dtype=np.float64).reshape(3)
        poses[img_name] = {'R': R, 't': t}

    return K, poses, image_names


def read_points3D(points_path):
    """Read points3D.json and return dict:
    {point_id (str): {'xyz': np.array(3,), 'color': np.array(3,), 'error': float}}

    Args:
        points_path: Path to points3D.json.

    Returns:
        dict mapping point_id -> point data.
    """
    with open(points_path, 'r') as f:
        data = json.load(f)

    points = {}
    for pt_id, pt in data.items():
        points[pt_id] = {
            'xyz': np.array(pt['xyz'], dtype=np.float64),
            'color': np.array(pt['color'], dtype=np.uint8),
            'error': float(pt['error'])
        }
    return points


def read_tracks(tracks_path):
    """Read tracks.json and return dict:
    {point_id (str): [(image_name, kp_idx), ...]}

    Args:
        tracks_path: Path to tracks.json.

    Returns:
        dict mapping point_id -> list of (img_name, kp_idx) tuples.
    """
    with open(tracks_path, 'r') as f:
        tracks = json.load(f)
    return tracks


def read_sfm_results(results_dir, logger=None):
    """Read all SfM results from Task 1 output directory.

    Args:
        results_dir: Path to the results/sparse/ directory.
        logger: Optional logger instance.

    Returns:
        K (np.ndarray 3x3), poses (dict), points3D (dict),
        tracks (dict), image_names (list of str)
    """
    cameras_path = os.path.join(results_dir, 'cameras.json')
    points_path = os.path.join(results_dir, 'points3D.json')
    tracks_path = os.path.join(results_dir, 'tracks.json')

    if logger:
        logger.info(f"Reading SfM results from {results_dir}")

    K, poses, image_names = read_cameras(cameras_path)
    points3D = read_points3D(points_path)
    tracks = read_tracks(tracks_path)

    if logger:
        logger.info(f"  Read {len(image_names)} registered cameras")
        logger.info(f"  K = [[{K[0,0]:.1f}, 0, {K[0,2]:.1f}], [0, {K[1,1]:.1f}, {K[1,2]:.1f}], [0, 0, 1]]")
        logger.info(f"  Read {len(points3D)} sparse 3D points")
        logger.info(f"  Read {len(tracks)} tracks")

    return K, poses, points3D, tracks, image_names
