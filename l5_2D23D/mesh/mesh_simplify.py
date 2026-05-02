"""Mesh simplification for frontend display."""

import open3d as o3d
import numpy as np


def simplify_mesh(mesh, target_triangles=100000):
    """Simplify mesh to target triangle count using quadric edge collapse."""
    n_triangles = len(mesh.triangles)

    if n_triangles <= target_triangles:
        return mesh, {"simplified": False, "before": n_triangles, "after": n_triangles}

    reduction = n_triangles - target_triangles
    mesh_simplified = mesh.simplify_quadric_decimation(target_number_of_triangles=target_triangles)
    n_after = len(mesh_simplified.triangles)

    stats = {
        "simplified": True,
        "before": n_triangles,
        "after": n_after,
        "reduction_ratio": n_after / n_triangles if n_triangles > 0 else 1.0,
    }
    return mesh_simplified, stats
