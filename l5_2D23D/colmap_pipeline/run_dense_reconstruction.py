"""Task 4.0-E: COLMAP Dense Reconstruction (undistort + stereo + fusion)."""
import subprocess
import sys
import os
from datetime import datetime

LOG_DIR = "./results/colmap/logs"
IMAGE_PATH = "./data/image"
SPARSE_PATH = "./results/colmap/sparse"
DENSE_PATH = "./results/colmap/dense"


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


def step(name, cmd, logname):
    log_path = os.path.join(LOG_DIR, logname)
    print(f"[4.0-E] {name}...")
    ok, elapsed = run(cmd, log_path)
    if ok:
        print(f"  PASS ({elapsed:.1f}s)")
    else:
        print(f"  FAILED — see {log_path}")
        sys.exit(1)
    return ok


def main():
    # Step 1: Image Undistortion
    sparsemodel = os.path.join(SPARSE_PATH, "0")
    step("Image undistortion", [
        "colmap", "image_undistorter",
        "--image_path", IMAGE_PATH,
        "--input_path", sparsemodel,
        "--output_path", DENSE_PATH,
        "--output_type", "COLMAP",
    ], "image_undistorter.log")

    # Step 2: PatchMatch Stereo
    step("PatchMatch stereo", [
        "colmap", "patch_match_stereo",
        "--workspace_path", DENSE_PATH,
        "--workspace_format", "COLMAP",
        "--PatchMatchStereo.geom_consistency", "true",
    ], "patch_match_stereo.log")

    # Step 3: Stereo Fusion
    step("Stereo fusion", [
        "colmap", "stereo_fusion",
        "--workspace_path", DENSE_PATH,
        "--workspace_format", "COLMAP",
        "--input_type", "geometric",
        "--output_path", os.path.join(DENSE_PATH, "fused.ply"),
    ], "stereo_fusion.log")

    # Verify
    fused = os.path.join(DENSE_PATH, "fused.ply")
    if os.path.exists(fused):
        print(f"[4.0-E] fused.ply created ({os.path.getsize(fused)} bytes)")
    else:
        print("[4.0-E] fused.ply MISSING")
        sys.exit(1)


if __name__ == "__main__":
    main()
