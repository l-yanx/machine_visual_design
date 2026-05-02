#!/usr/bin/env python3
"""
Task 3.0: Dense Point Cloud Quality Check & Cleaning Pipeline.

Usage:
    source /home/lyx/miniconda3/etc/profile.d/conda.sh && conda activate 3D_Reconstruction
    python main_clean_pointcloud.py --config config.yaml
"""

import argparse
import os
import sys
import time

import numpy as np
import open3d as o3d
import yaml

from mesh.pointcloud_io import load_point_cloud
from mesh.pointcloud_quality import compute_point_cloud_stats, format_stats_for_report
from mesh.pointcloud_filter import (
    remove_invalid_points,
    remove_duplicate_points,
    apply_statistical_outlier_removal,
    apply_radius_outlier_removal,
    apply_color_filter,
    apply_voxel_downsample,
    estimate_and_orient_normals,
)
from mesh.pointcloud_cluster import extract_main_cluster_dbscan
from mesh.pointcloud_visualize import save_before_after_projection
from mesh.export_cleaned import export_cleaned_pointcloud, generate_cleaning_report
from mesh.utils import estimate_median_nn_distance


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_log(log_path):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    f = open(log_path, "w", encoding="utf-8")
    return f


def log(msg, log_file=None):
    msg = str(msg)
    print(msg)
    if log_file:
        log_file.write(msg + "\n")
        log_file.flush()


def main():
    parser = argparse.ArgumentParser(description="Task 3.0 Point Cloud Cleaning")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config")
    args = parser.parse_args()

    cfg = load_config(args.config)
    results_dir = cfg["paths"]["results_dir"]
    cleaning_cfg = cfg.get("cleaning", {})

    input_ply = cleaning_cfg.get("input_dense_ply", os.path.join(results_dir, "dense", "dense.ply"))
    output_dir = cleaning_cfg.get("output_dir", os.path.join(results_dir, "mesh"))
    output_cleaned = cleaning_cfg.get("output_cleaned_ply", os.path.join(output_dir, "dense_cleaned.ply"))
    log_dir = os.path.join(results_dir, "logs")

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, "task3_0_cleaning_log.txt")
    logf = setup_log(log_path)

    t_start = time.time()
    log("=" * 60, logf)
    log("Task 3.0: Dense Point Cloud Quality Check & Cleaning", logf)
    log(f"Start: {time.strftime('%Y-%m-%d %H:%M:%S')}", logf)
    log("=" * 60, logf)
    log(f"Conda env: 3D_Reconstruction", logf)
    log(f"Input: {input_ply}", logf)
    log(f"Output dir: {output_dir}", logf)

    # ── Step 1: Load and validate ──────────────────────────────────
    log("\n[Step 1] Loading dense point cloud...", logf)
    pcd, pcd_info = load_point_cloud(input_ply)
    log(f"  Path: {pcd_info['path']}", logf)
    log(f"  Points: {pcd_info['num_points']:,}", logf)
    log(f"  Has colors: {pcd_info['has_colors']}", logf)
    log(f"  Has normals: {pcd_info['has_normals']}", logf)
    log(f"  NaN count: {pcd_info['nan_count']}", logf)
    log(f"  Inf count: {pcd_info['inf_count']}", logf)
    log(f"  Bounds: {pcd_info['bounds_min']} → {pcd_info['bounds_max']}", logf)

    # ── Step 2: Original statistics ────────────────────────────────
    log("\n[Step 2] Computing original point cloud statistics...", logf)
    original_stats = compute_point_cloud_stats(pcd)
    log(format_stats_for_report(original_stats, "Original Point Cloud"), logf)

    # ── Build step records ─────────────────────────────────────────
    steps = []
    current_pcd = pcd
    current_label = "dense"

    # ── Step 3: Remove invalid points ──────────────────────────────
    if cleaning_cfg.get("remove_nan_inf", True):
        log("\n[Step 3] Removing NaN/Inf points...", logf)
        current_pcd, stats = remove_invalid_points(current_pcd)
        stats["name"] = "NaN/Inf 移除"
        steps.append(stats)
        log(f"  Before: {stats['before']:,}  After: {stats['after']:,}  Removed: {stats['removed']:,}", logf)
        out_path = os.path.join(output_dir, "dense_valid_only.ply")
        export_cleaned_pointcloud(current_pcd, out_path)
        log(f"  Saved: {out_path}", logf)

    # ── Step 4: Remove duplicate points ────────────────────────────
    if cleaning_cfg.get("remove_duplicate_points", True):
        log("\n[Step 4] Removing duplicate points...", logf)
        current_pcd, stats = remove_duplicate_points(current_pcd)
        stats["name"] = "重复点移除"
        steps.append(stats)
        log(f"  Before: {stats['before']:,}  After: {stats['after']:,}  Removed: {stats['removed']:,}", logf)

    # ── Step 5: Color filtering (optional) ─────────────────────────
    color_cfg = cleaning_cfg.get("use_color_filter", False)
    if color_cfg:
        log("\n[Step 5] Color-based background filtering...", logf)
        mode = cleaning_cfg.get("color_filter_mode", "yellow_background")
        b_min = cleaning_cfg.get("brightness_min", 0)
        b_max = cleaning_cfg.get("brightness_max", 255)
        current_pcd, stats = apply_color_filter(current_pcd, mode=mode, brightness_min=b_min, brightness_max=b_max)
        stats["name"] = "颜色背景过滤"
        steps.append(stats)
        log(f"  Mode: {mode}  Before: {stats['before']:,}  After: {stats['after']:,}  Removed: {stats['removed']:,}", logf)
        out_path = os.path.join(output_dir, "dense_color_filtered.ply")
        export_cleaned_pointcloud(current_pcd, out_path)
        log(f"  Saved: {out_path}", logf)
    else:
        log("\n[Step 5] Color filtering: disabled in config", logf)

    # ── Step 6: Statistical outlier removal ────────────────────────
    stat_cfg = cleaning_cfg.get("statistical_outlier", {})
    if stat_cfg.get("enabled", True):
        log("\n[Step 6] Statistical outlier removal...", logf)
        nb = stat_cfg.get("nb_neighbors", 30)
        std = stat_cfg.get("std_ratio", 1.5)
        current_pcd, stats = apply_statistical_outlier_removal(current_pcd, nb_neighbors=nb, std_ratio=std)
        stats["name"] = "统计离群点移除"
        steps.append(stats)
        log(f"  nb_neighbors={nb}  std_ratio={std}", logf)
        log(f"  Before: {stats['before']:,}  After: {stats['after']:,}  Removed: {stats['removed']:,}", logf)
        out_path = os.path.join(output_dir, "dense_statistical_cleaned.ply")
        export_cleaned_pointcloud(current_pcd, out_path)
        log(f"  Saved: {out_path}", logf)

    # ── Step 7: Radius outlier removal ─────────────────────────────
    radius_cfg = cleaning_cfg.get("radius_outlier", {})
    if radius_cfg.get("enabled", True):
        log("\n[Step 7] Radius outlier removal...", logf)
        radius_scale = radius_cfg.get("radius_scale", 2.5)
        min_neighbors = radius_cfg.get("min_neighbors", 8)
        med = estimate_median_nn_distance(current_pcd)
        radius = med * radius_scale
        log(f"  Estimated median NN distance: {med:.6f}", logf)
        log(f"  Computed radius: {radius:.6f} (scale={radius_scale})", logf)
        current_pcd, stats = apply_radius_outlier_removal(current_pcd, radius=radius, min_neighbors=min_neighbors)
        stats["name"] = "半径离群点移除"
        stats["median_nn_distance"] = float(med)
        stats["computed_radius"] = float(radius)
        steps.append(stats)
        log(f"  Before: {stats['before']:,}  After: {stats['after']:,}  Removed: {stats['removed']:,}", logf)
        out_path = os.path.join(output_dir, "dense_radius_cleaned.ply")
        export_cleaned_pointcloud(current_pcd, out_path)
        log(f"  Saved: {out_path}", logf)

    # ── Step 8: DBSCAN clustering ──────────────────────────────────
    dbscan_cfg = cleaning_cfg.get("dbscan", {})
    if dbscan_cfg.get("enabled", True):
        log("\n[Step 8] DBSCAN main cluster extraction...", logf)
        eps_scale = dbscan_cfg.get("eps_scale", 2.5)
        min_points = dbscan_cfg.get("min_points", 20)
        keep_k = dbscan_cfg.get("keep_largest_k", 1)
        med = estimate_median_nn_distance(current_pcd)
        eps = med * eps_scale
        log(f"  Estimated median NN distance: {med:.6f}", logf)
        log(f"  Computed eps: {eps:.6f} (scale={eps_scale})", logf)
        current_pcd, stats = extract_main_cluster_dbscan(
            current_pcd, eps=eps, min_points=min_points, keep_largest_k=keep_k
        )
        stats["name"] = "DBSCAN 主簇提取"
        stats["median_nn_distance"] = float(med)
        steps.append(stats)
        log(f"  Clusters found: {stats.get('n_clusters', 'N/A')}", logf)
        log(f"  Cluster sizes: {stats.get('cluster_sizes', [])}", logf)
        log(f"  Before: {stats['before']:,}  After: {stats['after']:,}  Removed: {stats['removed']:,}", logf)
        out_path = os.path.join(output_dir, "dense_dbscan_cleaned.ply")
        export_cleaned_pointcloud(current_pcd, out_path)
        log(f"  Saved: {out_path}", logf)

    # ── Step 9: Voxel downsampling ─────────────────────────────────
    voxel_cfg = cleaning_cfg.get("voxel_downsample", {})
    if voxel_cfg.get("enabled", True):
        log("\n[Step 9] Voxel downsampling...", logf)
        voxel_size = voxel_cfg.get("voxel_size", 0.02)
        current_pcd, stats = apply_voxel_downsample(current_pcd, voxel_size=voxel_size)
        stats["name"] = "体素降采样"
        steps.append(stats)
        log(f"  Voxel size: {voxel_size}", logf)
        log(f"  Before: {stats['before']:,}  After: {stats['after']:,}  Removed: {stats['removed']:,}", logf)
        out_path = os.path.join(output_dir, "dense_voxel_downsampled.ply")
        export_cleaned_pointcloud(current_pcd, out_path)
        log(f"  Saved: {out_path}", logf)

    # ── Step 10: Normal estimation ─────────────────────────────────
    normal_cfg = cleaning_cfg.get("normal_estimation", {})
    if normal_cfg.get("enabled", True):
        log("\n[Step 10] Normal estimation...", logf)
        radius_scale = normal_cfg.get("radius_scale", 3.0)
        max_nn = normal_cfg.get("max_nn", 30)
        orient = normal_cfg.get("orient_normals", True)
        med = estimate_median_nn_distance(current_pcd)
        radius = med * radius_scale
        log(f"  Estimated median NN distance: {med:.6f}", logf)
        log(f"  Computed radius: {radius:.6f} (scale={radius_scale})", logf)
        orient_ref = None
        if orient:
            pts = np.asarray(current_pcd.points)
            orient_ref = np.mean(pts, axis=0) + np.array([0, 0, 10])
        current_pcd, stats = estimate_and_orient_normals(
            current_pcd, radius=radius, max_nn=max_nn, orient_toward=orient_ref
        )
        stats["name"] = "法线估计"
        steps.append(stats)
        log(f"  Normals estimated: {stats['normals_estimated']}", logf)
        out_path = os.path.join(output_dir, "dense_with_normals.ply")
        export_cleaned_pointcloud(current_pcd, out_path)
        log(f"  Saved: {out_path}", logf)

    # ── Step 11: Export final cleaned point cloud ──────────────────
    log("\n[Step 11] Exporting final cleaned point cloud...", logf)
    export_cleaned_pointcloud(current_pcd, output_cleaned)
    log(f"  Saved: {output_cleaned}", logf)
    log(f"  Final point count: {len(current_pcd.points):,}", logf)

    # ── Step 12: Final statistics ──────────────────────────────────
    log("\n[Step 12] Computing final point cloud statistics...", logf)
    final_stats = compute_point_cloud_stats(current_pcd)
    log(format_stats_for_report(final_stats, "Cleaned Point Cloud"), logf)

    # ── Step 13: Before/after visualization ────────────────────────
    log("\n[Step 13] Generating before/after visualization...", logf)
    vis_output = cleaning_cfg.get("visualization", {}).get(
        "output_projection_png", os.path.join(output_dir, "pointcloud_before_after.png")
    )
    save_before_after_projection(input_ply, output_cleaned, vis_output)
    log(f"  Saved: {vis_output}", logf)

    # ── Step 14: Generate cleaning report ──────────────────────────
    log("\n[Step 14] Generating cleaning report...", logf)
    report_path = os.path.join(output_dir, "cleaning_report.txt")

    # Recommendation
    n_final = len(current_pcd.points)
    if n_final > 1000 and current_pcd.has_normals():
        recommendation = "清洗后的点云质量良好，建议用于网格重建（Task 3.1 Mesh Reconstruction）。"
    elif n_final > 0:
        recommendation = "清洗后的点云基本可用，但可能需要进一步清理或参数调整后再进行网格重建。"
    else:
        recommendation = "清洗后点云点数过少，不建议直接进行网格重建。请检查清洗参数或输入数据。"

    report_data = {
        "input_path": input_ply,
        "output_path": output_cleaned,
        "conda_env": "3D_Reconstruction",
        "before_after_png": vis_output,
        "original_stats": original_stats,
        "steps": steps,
        "final_stats": final_stats,
        "recommendation": recommendation,
        "limitations": [
            "DBSCAN 对 eps 参数敏感，如果点云密度变化较大，可能需要手动调整",
            "颜色过滤仅支持黄色背景模式，其他背景颜色需要修改代码",
            "法线估计使用混合 KD 树搜索，可能在高曲率区域产生噪声",
            "体素降采样会丢失细节，对于精细结构的重建可能需要降低体素大小",
            "半径滤波的 radius 基于中位数最近邻距离估算，极端情况下可能不够准确",
        ],
    }
    generate_cleaning_report(report_data, report_path)
    log(f"  Saved: {report_path}", logf)

    # ── Summary ────────────────────────────────────────────────────
    t_total = time.time() - t_start
    log("\n" + "=" * 60, logf)
    log("Task 3.0 Cleaning Pipeline Summary", logf)
    log(f"  Original points: {pcd_info['num_points']:,}", logf)
    log(f"  Final points: {len(current_pcd.points):,}", logf)
    log(f"  Total removed: {pcd_info['num_points'] - len(current_pcd.points):,}", logf)
    log(f"  Retention: {len(current_pcd.points) / max(pcd_info['num_points'], 1) * 100:.2f}%", logf)
    log(f"  Total time: {t_total:.1f}s", logf)
    log(f"  Log file: {log_path}", logf)
    log(f"  Report file: {report_path}", logf)
    log("=" * 60, logf)

    # Verify final outputs
    log("\nOutput verification:", logf)
    required_outputs = [output_cleaned, report_path, vis_output, log_path]
    all_ok = True
    for p in required_outputs:
        exists = os.path.exists(p)
        log(f"  {p}: {'EXISTS' if exists else 'MISSING'}", logf)
        if not exists:
            all_ok = False

    if all_ok:
        log("\nAll required outputs generated successfully.", logf)
    else:
        log("\nWARNING: Some required outputs are missing.", logf)

    logf.close()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
