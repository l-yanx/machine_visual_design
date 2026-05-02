"""Task 4.0-F: COLMAP Meshing (Poisson + Delaunay)."""
import subprocess
import sys
import os
from datetime import datetime

LOG_DIR = "./results/colmap/logs"
DENSE_PATH = "./results/colmap/dense"
FUSED_PLY = os.path.join(DENSE_PATH, "fused.ply")


def run(cmd, log_path):
    start = datetime.now()
    with open(log_path, "w") as f:
        f.write(f"Command: {' '.join(cmd)}\nStarted: {start.isoformat()}\n\n")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        f.write("STDOUT:\n" + proc.stdout + "\n")
        f.write("STDERR:\n" + proc.stderr + "\n")
        elapsed = (datetime.now() - start).total_seconds()
        f.write(f"\nReturn code: {proc.returncode}\nElapsed: {elapsed:.1f}s\n")
    return proc.returncode == 0, elapsed


def main():
    success = False

    # Poisson meshing
    poisson_out = os.path.join(DENSE_PATH, "meshed-poisson.ply")
    print("[4.0-F] Poisson meshing...")
    ok, elapsed = run([
        "colmap", "poisson_mesher",
        "--input_path", FUSED_PLY,
        "--output_path", poisson_out,
    ], os.path.join(LOG_DIR, "poisson_mesher.log"))
    if ok:
        print(f"  PASS ({elapsed:.1f}s, {os.path.getsize(poisson_out)} bytes)")
        success = True
    else:
        print(f"  FAILED ({elapsed:.1f}s)")

    # Delaunay meshing
    delaunay_out = os.path.join(DENSE_PATH, "meshed-delaunay.ply")
    print("[4.0-F] Delaunay meshing...")
    ok2, elapsed2 = run([
        "colmap", "delaunay_mesher",
        "--input_path", DENSE_PATH,
        "--output_path", delaunay_out,
    ], os.path.join(LOG_DIR, "delaunay_mesher.log"))
    if ok2:
        print(f"  PASS ({elapsed2:.1f}s, {os.path.getsize(delaunay_out)} bytes)")
        success = True
    else:
        print(f"  FAILED ({elapsed2:.1f}s)")

    if not success:
        print("[4.0-F] Both meshing methods failed")
        sys.exit(1)

    print("[4.0-F] Meshing done — at least one mesh exists")


if __name__ == "__main__":
    main()
