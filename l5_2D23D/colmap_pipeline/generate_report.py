"""Task 4.0-H: COLMAP Output Validation and Report Generation."""
import sys
import os
import numpy as np

REPORT_DIR = "./results/colmap/report"
SPARSE_PATH = "./results/colmap/sparse/0"
DENSE_PATH = "./results/colmap/dense"
MODEL_DIR = "./results/colmap/model"


def count_ply_points(path):
    """Count points in a PLY file."""
    import open3d as o3d
    pcd = o3d.io.read_point_cloud(path)
    pts = np.asarray(pcd.points)
    return len(pts), pts


def count_mesh(path):
    """Count vertices and faces in a mesh PLY."""
    import open3d as o3d
    mesh = o3d.io.read_triangle_mesh(path)
    return len(mesh.vertices), len(mesh.triangles), mesh


def generate_projection(points, outpath):
    """Generate XY, XZ, YZ projections."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    titles = ["XY (top)", "XZ (front)", "YZ (side)"]
    idx_pairs = [(0, 1), (0, 2), (1, 2)]

    for ax, (xi, yi), title in zip(axes, idx_pairs, titles):
        ax.scatter(points[:, xi], points[:, yi], s=0.1, c="steelblue", alpha=0.5)
        ax.set_aspect("equal")
        ax.set_title(title)
        ax.set_xlabel(["X", "X", "Y"][idx_pairs.index((xi, yi))])
        ax.set_ylabel(["Y", "Z", "Z"][idx_pairs.index((xi, yi))])

    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()
    print(f"  Projection saved: {outpath}")


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)

    report_lines = ["# COLMAP Reconstruction Report — Task 4.0", ""]
    mesh_summary_lines = ["# Mesh Summary", ""]

    # Check sparse model
    report_lines.append("## 1. Sparse Reconstruction")
    for f in ["cameras.bin", "images.bin", "points3D.bin"]:
        fp = os.path.join(SPARSE_PATH, f)
        ok = "PASS" if os.path.exists(fp) else "MISSING"
        report_lines.append(f"- {f}: {ok}")
    report_lines.append("")

    # Check dense point cloud
    report_lines.append("## 2. Dense Point Cloud")
    fused = os.path.join(DENSE_PATH, "fused.ply")
    points = None
    if os.path.exists(fused):
        n_pts, pts = count_ply_points(fused)
        points = pts
        report_lines.append(f"- fused.ply: {n_pts} points ({os.path.getsize(fused)} bytes)")
    else:
        report_lines.append("- fused.ply: MISSING")
    report_lines.append("")

    # Check meshes
    report_lines.append("## 3. Meshes")
    for mesh_name in ["meshed-poisson.ply", "meshed-delaunay.ply"]:
        mp = os.path.join(DENSE_PATH, mesh_name)
        if os.path.exists(mp):
            nv, nf, m = count_mesh(mp)
            report_lines.append(f"- {mesh_name}: {nv} vertices, {nf} faces ({os.path.getsize(mp)} bytes)")
            mesh_summary_lines.append(f"### {mesh_name}")
            mesh_summary_lines.append(f"- Vertices: {nv}")
            mesh_summary_lines.append(f"- Faces: {nf}")
            mesh_summary_lines.append(f"- Size: {os.path.getsize(mp)} bytes")
            mesh_summary_lines.append("")
        else:
            report_lines.append(f"- {mesh_name}: MISSING")
    report_lines.append("")

    # Check GLB
    report_lines.append("## 4. GLB Model")
    glb = os.path.join(MODEL_DIR, "model.glb")
    if os.path.exists(glb):
        report_lines.append(f"- model.glb: {os.path.getsize(glb)} bytes — PASS")
    else:
        report_lines.append("- model.glb: MISSING")
    report_lines.append("")

    # Generate projection
    report_lines.append("## 5. Point Cloud Projection")
    proj_path = os.path.join(REPORT_DIR, "pointcloud_projection.png")
    if points is not None and len(points) > 0:
        generate_projection(points, proj_path)
        report_lines.append(f"- {proj_path}: generated")
    else:
        report_lines.append("- No point cloud data for projection")
    report_lines.append("")

    # Summary
    report_lines.append("## 6. Final Status")
    checks = [
        ("fused.ply exists", os.path.exists(fused)),
        ("At least one mesh exists", any(os.path.exists(os.path.join(DENSE_PATH, m))
            for m in ["meshed-poisson.ply", "meshed-delaunay.ply"])),
        ("model.glb exists", os.path.exists(glb)),
    ]
    all_pass = True
    for desc, ok in checks:
        s = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        report_lines.append(f"- [{s}] {desc}")

    # Write reports
    with open(os.path.join(REPORT_DIR, "reconstruction_report.md"), "w") as f:
        f.write("\n".join(report_lines))
    with open(os.path.join(REPORT_DIR, "mesh_summary.md"), "w") as f:
        f.write("\n".join(mesh_summary_lines))

    print("[4.0-H] Reports generated")
    if all_pass:
        print("[4.0-H] All validation checks PASSED")
    else:
        print("[4.0-H] Some checks FAILED (see report)")


if __name__ == "__main__":
    main()
