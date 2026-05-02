"""Poisson surface reconstruction."""

import open3d as o3d
import numpy as np


def poisson_reconstruct(pcd, depth=8, scale=1.1, linear_fit=False):
    """Run Poisson surface reconstruction.

    Returns (mesh, densities) tuple. densities are per-vertex density values.
    """
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=depth, scale=scale, linear_fit=linear_fit
    )
    return mesh, densities


def crop_mesh_to_bounds(mesh, pcd, margin=0.05):
    """Crop mesh to point cloud bounding box plus margin."""
    pts = np.asarray(pcd.points)
    bmin = pts.min(axis=0) - margin
    bmax = pts.max(axis=0) + margin
    bbox = o3d.geometry.AxisAlignedBoundingBox(bmin, bmax)
    return mesh.crop(bbox)
