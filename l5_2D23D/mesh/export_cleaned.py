"""Export cleaned point cloud and generate cleaning report."""

import os
import numpy as np
import open3d as o3d
from mesh.pointcloud_quality import compute_point_cloud_stats, format_stats_for_report


def export_cleaned_pointcloud(pcd, output_path):
    """Export point cloud to PLY file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    o3d.io.write_point_cloud(output_path, pcd)
    return output_path


def generate_cleaning_report(report_data, output_path):
    """Generate a Chinese cleaning report text file.

    report_data should contain:
        input_path, output_path, conda_env, original_stats, steps (list of dicts),
        final_stats, before_after_png, recommendation
    """
    lines = []
    lines.append("=" * 60)
    lines.append("点云清洗报告 — Task 3.0")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"输入文件: {report_data.get('input_path', 'N/A')}")
    lines.append(f"输出文件: {report_data.get('output_path', 'N/A')}")
    lines.append(f"Conda 环境: {report_data.get('conda_env', 'N/A')}")
    lines.append(f"可视化对比图: {report_data.get('before_after_png', 'N/A')}")
    lines.append("")

    # Original statistics
    lines.append("-" * 40)
    lines.append("清洗前统计")
    lines.append("-" * 40)
    orig = report_data.get("original_stats")
    if orig:
        lines.append(f"  点数: {orig.get('num_points', 'N/A'):,}")
        bb = orig.get("bounds_min")
        if bb is not None:
            lines.append(f"  包围盒最小: ({bb[0]:.4f}, {bb[1]:.4f}, {bb[2]:.4f})")
        bb = orig.get("bounds_max")
        if bb is not None:
            lines.append(f"  包围盒最大: ({bb[0]:.4f}, {bb[1]:.4f}, {bb[2]:.4f})")
        lines.append(f"  最近邻距离中位数: {orig.get('nn_distance_median', 'N/A')}")
    lines.append("")

    # Step-by-step results
    lines.append("-" * 40)
    lines.append("清洗步骤")
    lines.append("-" * 40)
    steps = report_data.get("steps", [])
    total_removed = 0
    for step in steps:
        name = step.get("name", "?")
        before = step.get("before", 0)
        after = step.get("after", 0)
        removed = step.get("removed", 0)
        pct = (removed / before * 100) if before > 0 else 0
        total_removed += removed
        lines.append(f"  [{name}]")
        lines.append(f"    清洗前: {before:,} 点")
        lines.append(f"    清洗后: {after:,} 点")
        lines.append(f"    移除: {removed:,} 点 ({pct:.2f}%)")
        extra = {k: v for k, v in step.items() if k not in ("name", "before", "after", "removed")}
        if extra:
            for k, v in extra.items():
                lines.append(f"    参数 {k}: {v}")
    lines.append("")

    # Final statistics
    lines.append("-" * 40)
    lines.append("清洗后统计")
    lines.append("-" * 40)
    final = report_data.get("final_stats")
    if final:
        lines.append(f"  点数: {final.get('num_points', 'N/A'):,}")
        bb = final.get("bounds_min")
        if bb is not None:
            lines.append(f"  包围盒最小: ({bb[0]:.4f}, {bb[1]:.4f}, {bb[2]:.4f})")
        bb = final.get("bounds_max")
        if bb is not None:
            lines.append(f"  包围盒最大: ({bb[0]:.4f}, {bb[1]:.4f}, {bb[2]:.4f})")
        lines.append(f"  最近邻距离中位数: {final.get('nn_distance_median', 'N/A')}")
    lines.append("")

    # Summary
    lines.append("-" * 40)
    lines.append("总体变化")
    lines.append("-" * 40)
    orig_n = orig.get("num_points", 0) if orig else 0
    final_n = final.get("num_points", 0) if final else 0
    if orig_n > 0:
        lines.append(f"  原始点数: {orig_n:,}")
        lines.append(f"  最终点数: {final_n:,}")
        lines.append(f"  保留比例: {final_n / orig_n * 100:.2f}%")
    lines.append("")

    lines.append("-" * 40)
    lines.append("建议")
    lines.append("-" * 40)
    lines.append(f"  {report_data.get('recommendation', 'N/A')}")
    lines.append("")

    lines.append("-" * 40)
    lines.append("已知限制")
    lines.append("-" * 40)
    for lim in report_data.get("limitations", []):
        lines.append(f"  - {lim}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_path
