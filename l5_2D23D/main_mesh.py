#!/usr/bin/env python3
"""Main Mesh Reconstruction Pipeline for V2 Task 3.

Converts dense.ply → cleaned point cloud → normals → Poisson mesh → cleanup → simplify → export.
"""

import argparse
import os
import sys
import time

import numpy as np
import open3d as o3d
import yaml

from mesh.read_dense import read_dense_ply
from mesh.pointcloud_clean import clean_dense_pcd
from mesh.normal_estimation import estimate_and_orient_normals
from mesh.poisson_recon import poisson_reconstruct, crop_mesh_to_bounds
from mesh.mesh_cleanup import clean_mesh
from mesh.mesh_simplify import simplify_mesh
from mesh.export_model import export_all


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_log(log_path):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    return open(log_path, "w", encoding="utf-8")


def log(msg, log_file=None):
    msg = str(msg)
    print(msg)
    if log_file:
        log_file.write(msg + "\n")
        log_file.flush()


def main():
    parser = argparse.ArgumentParser(description="V2 Mesh Reconstruction Pipeline")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config file")
    parser.add_argument("--dense", default=None, help="Override dense.ply path")
    parser.add_argument("--output_dir", default=None, help="Override output directory")
    args = parser.parse_args()

    cfg = load_config(args.config)
    results_dir = args.output_dir or cfg["paths"]["results_dir"]
    mesh_dir = os.path.join(results_dir, "mesh")
    logs_dir = os.path.join(results_dir, "logs")
    os.makedirs(mesh_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    log_path = os.path.join(logs_dir, "mesh_log.txt")
    logf = setup_log(log_path)

    t_start = time.time()
    log("=" * 60, logf)
    log("V2 Mesh Reconstruction Pipeline", logf)
    log(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}", logf)
    log("=" * 60, logf)

    mesh_cfg = cfg.get("mesh", {})

    # --- Step 1: Read dense point cloud ---
    log("\n[Step 1] Reading dense point cloud...", logf)
    dense_path = args.dense or os.path.join(results_dir, "dense", "dense.ply")
    pcd, pcd_info = read_dense_ply(dense_path)
    log(f"  Path: {pcd_info['path']}", logf)
    log(f"  Points: {pcd_info['num_points']:,}", logf)
    log(f"  Has colors: {pcd_info['has_colors']}", logf)
    log(f"  Has normals: {pcd_info['has_normals']}", logf)
    log(f"  Bounds: {pcd_info['bounds_min']} to {pcd_info['bounds_max']}", logf)

    # --- Step 2: Point cloud cleaning ---
    log("\n[Step 2] Cleaning dense point cloud...", logf)
    pcd_cleaned, clean_stats = clean_dense_pcd(
        pcd,
        nb_neighbors=mesh_cfg.get("outlier_nb_neighbors", 20),
        std_ratio=mesh_cfg.get("outlier_std_ratio", 2.0),
        voxel_size=mesh_cfg.get("voxel_downsample", 0.005),
    )
    log(f"  Before cleaning: {clean_stats['before_clean']:,} points", logf)
    log(f"  After statistical outlier removal: {clean_stats['after_statistical']:,} points", logf)
    log(f"  After voxel downsample: {clean_stats['after_voxel']:,} points", logf)

    cleaned_path = os.path.join(mesh_dir, "cleaned_dense.ply")
    o3d.io.write_point_cloud(cleaned_path, pcd_cleaned)
    log(f"  Saved: {cleaned_path}", logf)

    # --- Step 3: Normal estimation ---
    log("\n[Step 3] Estimating and orienting normals...", logf)
    pcd_with_normals = estimate_and_orient_normals(
        pcd_cleaned, radius=0.02, max_nn=30
    )
    log(f"  Normals estimated: {pcd_with_normals.has_normals()}", logf)
    log(f"  Points: {len(pcd_with_normals.points):,}", logf)

    normals_path = os.path.join(mesh_dir, "cleaned_dense_with_normals.ply")
    o3d.io.write_point_cloud(normals_path, pcd_with_normals)
    log(f"  Saved: {normals_path}", logf)

    # --- Step 4: Poisson surface reconstruction ---
    log("\n[Step 4] Poisson surface reconstruction...", logf)
    poisson_depth = mesh_cfg.get("poisson_depth", 8)
    poisson_scale = mesh_cfg.get("poisson_scale", 1.1)
    poisson_linear_fit = mesh_cfg.get("poisson_linear_fit", False)

    log(f"  Parameters: depth={poisson_depth}, scale={poisson_scale}, linear_fit={poisson_linear_fit}", logf)
    mesh_raw, densities = poisson_reconstruct(
        pcd_with_normals, depth=poisson_depth, scale=poisson_scale, linear_fit=poisson_linear_fit
    )
    log(f"  Raw mesh: {len(mesh_raw.vertices):,} vertices, {len(mesh_raw.triangles):,} triangles", logf)

    # Crop to point cloud bounds
    mesh_raw = crop_mesh_to_bounds(mesh_raw, pcd_with_normals, margin=0.1)
    log(f"  After crop to bounds: {len(mesh_raw.vertices):,} vertices, {len(mesh_raw.triangles):,} triangles", logf)

    raw_path = os.path.join(mesh_dir, "mesh_poisson_raw.ply")
    o3d.io.write_triangle_mesh(raw_path, mesh_raw)
    log(f"  Saved: {raw_path}", logf)

    # --- Step 5: Mesh cleanup ---
    log("\n[Step 5] Mesh cleanup...", logf)
    keep_largest = mesh_cfg.get("keep_largest_component", True)
    density_percentile = 5

    densities_array = np.asarray(densities) if densities is not None else None

    mesh_clean = clean_mesh(
        mesh_raw,
        densities=densities_array,
        density_percentile=density_percentile,
        keep_largest=keep_largest,
    )
    log(f"  Cleaned mesh: {len(mesh_clean.vertices):,} vertices, {len(mesh_clean.triangles):,} triangles", logf)

    cleaned_path = os.path.join(mesh_dir, "mesh_cleaned.ply")
    o3d.io.write_triangle_mesh(cleaned_path, mesh_clean)
    log(f"  Saved: {cleaned_path}", logf)

    # --- Step 6: Mesh simplification ---
    log("\n[Step 6] Mesh simplification...", logf)
    target_triangles = mesh_cfg.get("simplify_target_triangles", 100000)
    mesh_simplified, simplify_stats = simplify_mesh(mesh_clean, target_triangles=target_triangles)

    if simplify_stats.get("simplified", False):
        log(f"  Simplified: {simplify_stats['before']:,} → {simplify_stats['after']:,} triangles", logf)
        log(f"  Reduction ratio: {simplify_stats['reduction_ratio']:.3f}", logf)
    else:
        log(f"  No simplification needed: {simplify_stats['before']:,} triangles ≤ {target_triangles:,} target", logf)

    simpl_path = os.path.join(mesh_dir, "mesh_simplified.ply")
    o3d.io.write_triangle_mesh(simpl_path, mesh_simplified)
    log(f"  Saved: {simpl_path}", logf)

    # --- Step 7: Export model files ---
    log("\n[Step 7] Exporting model files...", logf)
    export_results = export_all(mesh_simplified, results_dir)

    for fmt, status in export_results.items():
        status_str = "OK" if status else "FAILED (see conversion note)"
        log(f"  model.{fmt}: {status_str}", logf)

    # --- Summary ---
    t_total = time.time() - t_start
    log("\n" + "=" * 60, logf)
    log("Mesh Reconstruction Summary", logf)
    log(f"  Input dense points: {pcd_info['num_points']:,}", logf)
    log(f"  Cleaned points: {clean_stats['after_voxel']:,}", logf)
    log(f"  Raw mesh: {len(mesh_raw.vertices):,} vertices, {len(mesh_raw.triangles):,} triangles", logf)
    log(f"  Cleaned mesh: {len(mesh_clean.vertices):,} vertices, {len(mesh_clean.triangles):,} triangles", logf)
    log(f"  Final mesh: {len(mesh_simplified.vertices):,} vertices, {len(mesh_simplified.triangles):,} triangles", logf)
    log(f"  Total time: {t_total:.1f} seconds", logf)
    log(f"  Log file: {log_path}", logf)
    log("=" * 60, logf)

    logf.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
