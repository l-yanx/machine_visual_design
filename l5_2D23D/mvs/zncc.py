"""
ZNCC (Zero-Mean Normalized Cross-Correlation) similarity module.
Implements patch-based similarity between two image patches.
"""

import numpy as np


def zncc_score(patch1, patch2, variance_threshold=1e-5):
    """Compute ZNCC score between two image patches.

    Formula: ZNCC = sum((A - mean_A) * (B - mean_B)) / sqrt(sum((A-mean_A)^2) * sum((B-mean_B)^2))

    Args:
        patch1: First image patch as numpy array (grayscale, float64).
        patch2: Second image patch as numpy array (grayscale, float64).
        variance_threshold: Minimum variance for valid patches (default 1e-5).

    Returns:
        float: ZNCC score in [-1, 1], or NaN if patches are invalid (weak texture).
        1 = perfect correlation, 0 = no correlation, -1 = perfect anti-correlation.
    """
    # Ensure patches are the same shape
    if patch1.shape != patch2.shape:
        return np.nan

    # Flatten patches
    a = patch1.ravel().astype(np.float64)
    b = patch2.ravel().astype(np.float64)

    # Compute means
    mean_a = np.mean(a)
    mean_b = np.mean(b)

    # Center
    a_centered = a - mean_a
    b_centered = b - mean_b

    # Compute variances
    var_a = np.sum(a_centered ** 2)
    var_b = np.sum(b_centered ** 2)

    # Check for weak texture (low variance)
    if var_a < variance_threshold or var_b < variance_threshold:
        return np.nan

    # Compute ZNCC
    numerator = np.sum(a_centered * b_centered)
    denominator = np.sqrt(var_a * var_b)

    if denominator < 1e-15:
        return np.nan

    zncc = numerator / denominator

    # Clip to [-1, 1] for numerical stability
    zncc = np.clip(zncc, -1.0, 1.0)

    return zncc


def extract_patch(image, u, v, patch_size):
    """Extract a square patch from an image centered at (u, v).
    Pads with edge values if the patch extends beyond image boundaries.

    Args:
        image: Input image (H, W) grayscale or (H, W, C) color.
        patch_size: Size of square patch (must be odd).

    Returns:
        np.ndarray: Extracted patch of shape (patch_size, patch_size) or
                   (patch_size, patch_size, C).
    """
    half = patch_size // 2

    # Calculate patch boundaries
    u_start = u - half
    u_end = u + half + 1
    v_start = v - half
    v_end = v + half + 1

    # Image dimensions
    H, W = image.shape[:2]

    # Create output patch
    if image.ndim == 2:
        patch = np.zeros((patch_size, patch_size), dtype=image.dtype)
    else:
        patch = np.zeros((patch_size, patch_size, image.shape[2]), dtype=image.dtype)

    # Determine valid region in the image
    img_u_start = max(0, u_start)
    img_u_end = min(W, u_end)
    img_v_start = max(0, v_start)
    img_v_end = min(H, v_end)

    # Determine valid region in the patch
    patch_u_start = img_u_start - u_start
    patch_u_end = patch_u_start + (img_u_end - img_u_start)
    patch_v_start = img_v_start - v_start
    patch_v_end = patch_v_start + (img_v_end - img_v_start)

    # Copy valid region
    patch[patch_v_start:patch_v_end, patch_u_start:patch_u_end] = \
        image[img_v_start:img_v_end, img_u_start:img_u_end]

    # Pad with edge values (copy border pixels outward)
    # Top pad
    if patch_v_start > 0:
        for py in range(patch_v_start):
            patch[py, :] = patch[patch_v_start, :]
    # Bottom pad
    if patch_v_end < patch_size:
        for py in range(patch_v_end, patch_size):
            patch[py, :] = patch[patch_v_end - 1, :]
    # Left pad
    if patch_u_start > 0:
        for px in range(patch_u_start):
            patch[:, px] = patch[:, patch_u_start]
    # Right pad
    if patch_u_end < patch_size:
        for px in range(patch_u_end, patch_size):
            patch[:, px] = patch[:, patch_u_end - 1]

    return patch


def extract_patch_vectorized(image, coords, patch_size):
    """Extract multiple patches from an image at given pixel coordinates.

    Vectorized version that extracts all patches at once using broadcasting.
    Pads with edge values.

    Args:
        image: Input image (H, W) grayscale.
        coords: Nx2 array of (u, v) coordinates.
        patch_size: Size of square patch (must be odd).

    Returns:
        np.ndarray: Patches of shape (N, patch_size, patch_size).
    """
    N = len(coords)
    half = patch_size // 2
    H, W = image.shape[:2]

    patches = np.zeros((N, patch_size, patch_size), dtype=np.float64)

    for i, (u, v) in enumerate(coords):
        u_i, v_i = int(u), int(v)
        patch = extract_patch(image, u_i, v_i, patch_size)
        patches[i] = patch.astype(np.float64)

    return patches
