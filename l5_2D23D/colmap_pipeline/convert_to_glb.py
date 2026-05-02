"""Task 4.0-G: Mesh to GLB Conversion."""
import sys
import os

MODEL_DIR = "./results/colmap/model"
DENSE_PATH = "./results/colmap/dense"
REPORT_PATH = os.path.join(MODEL_DIR, "conversion_report.md")


def main():
    # Choose best available mesh
    candidates = [
        os.path.join(DENSE_PATH, "meshed-poisson.ply"),
        os.path.join(DENSE_PATH, "meshed-delaunay.ply"),
    ]
    # Pick the largest valid mesh file
    best = None
    best_size = 0
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > best_size:
            best = c
            best_size = os.path.getsize(c)
    selected = best

    if not selected:
        print("[4.0-G] No valid mesh found for GLB conversion")
        sys.exit(1)
    if best_size < 10000:
        print(f"[4.0-G] WARNING: selected mesh is very small ({best_size} bytes), may be empty")

    print(f"[4.0-G] Converting {os.path.basename(selected)} to GLB...")
    import trimesh
    mesh = trimesh.load(selected)
    glb_path = os.path.join(MODEL_DIR, "model.glb")
    mesh.export(glb_path)

    glb_size = os.path.getsize(glb_path)
    print(f"[4.0-G] GLB exported: {glb_path} ({glb_size} bytes)")

    # Write conversion report
    with open(REPORT_PATH, "w") as f:
        f.write(f"# Mesh to GLB Conversion Report\n\n")
        f.write(f"Source mesh: {selected}\n")
        f.write(f"Output: {glb_path}\n")
        f.write(f"GLB size: {glb_size} bytes\n")
        f.write(f"Vertices: {len(mesh.vertices)}\n")
        f.write(f"Faces: {len(mesh.faces)}\n")


if __name__ == "__main__":
    main()
