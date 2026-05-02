"""Before/after visualization for point cloud cleaning."""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import open3d as o3d


def _sample_points(pts, colors, sample_size):
    """Subsample points and corresponding colors, keeping indices aligned."""
    n = len(pts)
    if n <= sample_size:
        return pts, colors
    rng = np.random.default_rng(42)
    idx = rng.choice(n, sample_size, replace=False)
    if colors is not None and len(colors) == n:
        return pts[idx], colors[idx]
    return pts[idx], None


def save_before_after_projection(before_path, after_path, output_png, sample_size=50000):
    """Generate a before/after projection comparison image.

    Creates a 3x2 grid: rows = [XY, XZ, YZ], cols = [Before, After].
    """
    pcd_before = o3d.io.read_point_cloud(before_path)
    pcd_after = o3d.io.read_point_cloud(after_path)

    pts_b = np.asarray(pcd_before.points)
    pts_a = np.asarray(pcd_after.points)
    colors_b = np.asarray(pcd_before.colors) if pcd_before.has_colors() else None
    colors_a = np.asarray(pcd_after.colors) if pcd_after.has_colors() else None

    pts_b, colors_b = _sample_points(pts_b, colors_b, sample_size)
    pts_a, colors_a = _sample_points(pts_a, colors_a, sample_size)

    fig, axes = plt.subplots(3, 2, figsize=(14, 18))
    fig.suptitle("Point Cloud Before/After Cleaning", fontsize=14, fontweight="bold")

    projections = [
        ("XY Projection", 0, 1),
        ("XZ Projection", 0, 2),
        ("YZ Projection", 1, 2),
    ]

    for row_idx, (title, ax_x, ax_y) in enumerate(projections):
        ax_left = axes[row_idx, 0]
        ax_right = axes[row_idx, 1]

        # Before
        if colors_b is not None:
            ax_left.scatter(pts_b[:, ax_x], pts_b[:, ax_y], c=colors_b, s=0.5, alpha=0.6)
        else:
            ax_left.scatter(pts_b[:, ax_x], pts_b[:, ax_y], c="steelblue", s=0.5, alpha=0.6)
        ax_left.set_title(f"Before — {title}")
        ax_left.set_xlabel(["X", "Y", "Z"][ax_x])
        ax_left.set_ylabel(["X", "Y", "Z"][ax_y])
        ax_left.set_aspect("equal")
        ax_left.grid(True, alpha=0.3)

        # After
        if colors_a is not None:
            ax_right.scatter(pts_a[:, ax_x], pts_a[:, ax_y], c=colors_a, s=0.5, alpha=0.6)
        else:
            ax_right.scatter(pts_a[:, ax_x], pts_a[:, ax_y], c="darkorange", s=0.5, alpha=0.6)
        ax_right.set_title(f"After — {title}")
        ax_right.set_xlabel(["X", "Y", "Z"][ax_x])
        ax_right.set_ylabel(["X", "Y", "Z"][ax_y])
        ax_right.set_aspect("equal")
        ax_right.grid(True, alpha=0.3)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_png), exist_ok=True)
    fig.savefig(output_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_png
