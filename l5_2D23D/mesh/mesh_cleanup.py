"""Low-density and floating mesh cleanup."""

import open3d as o3d
import numpy as np


def remove_low_density_vertices(mesh, densities, percentile=10):
    """Remove vertices whose Poisson density is below the given percentile."""
    if densities is None or len(densities) == 0:
        return mesh

    threshold = np.percentile(densities, percentile)
    vertices_to_remove = densities < threshold
    mesh.remove_vertices_by_mask(vertices_to_remove)
    return mesh


def remove_small_components(mesh, min_triangle_ratio=0.01):
    """Remove connected components with few triangles, keeping largest."""
    triangle_clusters, cluster_count, area = mesh.cluster_connected_triangles()
    triangle_clusters = np.asarray(triangle_clusters)
    triangle_counts = np.bincount(triangle_clusters)

    if len(triangle_counts) <= 1:
        return mesh

    largest_count = triangle_counts.max()
    threshold = max(1, int(largest_count * min_triangle_ratio))

    clusters_to_remove = set(np.where(triangle_counts < threshold)[0])
    triangles_to_remove = np.array([c in clusters_to_remove for c in triangle_clusters])
    mesh.remove_triangles_by_mask(triangles_to_remove)
    return mesh


def remove_degenerate_triangles(mesh):
    """Remove degenerate (zero-area) triangles."""
    mesh.remove_degenerate_triangles()
    return mesh


def remove_duplicated_triangles(mesh):
    """Remove duplicated triangles."""
    mesh.remove_duplicated_triangles()
    return mesh


def remove_duplicated_vertices(mesh):
    """Remove duplicated vertices."""
    mesh.remove_duplicated_vertices()
    return mesh


def keep_largest_component(mesh):
    """Keep only the largest connected component."""
    triangle_clusters, cluster_count, area = mesh.cluster_connected_triangles()
    triangle_clusters = np.asarray(triangle_clusters)
    triangle_counts = np.bincount(triangle_clusters)

    if len(triangle_counts) <= 1:
        return mesh

    largest_cluster = triangle_counts.argmax()
    triangles_to_remove = triangle_clusters != largest_cluster
    mesh.remove_triangles_by_mask(triangles_to_remove)
    mesh.remove_unreferenced_vertices()
    return mesh


def clean_mesh(mesh, densities=None, density_percentile=10, keep_largest=True):
    """Full mesh cleanup pipeline."""
    if densities is not None and len(densities) == len(mesh.vertices):
        mesh = remove_low_density_vertices(mesh, densities, density_percentile)

    mesh = remove_unreferenced_vertices_safe(mesh)
    mesh = remove_degenerate_triangles(mesh)
    mesh = remove_duplicated_triangles(mesh)
    mesh = remove_duplicated_vertices(mesh)

    if keep_largest:
        mesh = keep_largest_component(mesh)

    return mesh


def remove_unreferenced_vertices_safe(mesh):
    """Remove unreferenced vertices. Wraps Open3D method."""
    mesh.remove_unreferenced_vertices()
    return mesh
