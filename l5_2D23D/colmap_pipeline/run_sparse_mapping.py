"""Task 4.0-D: COLMAP Sparse Reconstruction."""
import subprocess
import sys
import os
from datetime import datetime

LOG_DIR = "./results/colmap/logs"
DB_PATH = "./results/colmap/database.db"
IMAGE_PATH = "./data/image"
SPARSE_PATH = "./results/colmap/sparse"


def run(cmd, log_path):
    start = datetime.now()
    with open(log_path, "w") as f:
        f.write(f"Command: {' '.join(cmd)}\nStarted: {start.isoformat()}\n\n")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        f.write("STDOUT:\n" + proc.stdout + "\n")
        f.write("STDERR:\n" + proc.stderr + "\n")
        elapsed = (datetime.now() - start).total_seconds()
        f.write(f"\nReturn code: {proc.returncode}\nElapsed: {elapsed:.1f}s\n")
    return proc.returncode == 0, elapsed, proc.stderr


def main():
    log_path = os.path.join(LOG_DIR, "sparse_mapping.log")

    cmd = [
        "colmap", "mapper",
        "--database_path", DB_PATH,
        "--image_path", IMAGE_PATH,
        "--output_path", SPARSE_PATH,
    ]
    print("[4.0-D] Running sparse mapping...")
    ok, elapsed, stderr = run(cmd, log_path)

    if not ok:
        print(f"[4.0-D] Sparse mapping FAILED")
        print(stderr[-500:] if len(stderr) > 500 else stderr)
        sys.exit(1)

    # Verify sparse model
    model_dirs = sorted([d for d in os.listdir(SPARSE_PATH) if os.path.isdir(os.path.join(SPARSE_PATH, d)) and d.isdigit()])
    if not model_dirs:
        print("[4.0-D] No sparse model folder found")
        sys.exit(1)

    model_path = os.path.join(SPARSE_PATH, model_dirs[0])
    required = ["cameras.bin", "images.bin", "points3D.bin"]
    for fname in required:
        fpath = os.path.join(model_path, fname)
        if os.path.exists(fpath):
            print(f"  [OK] {model_dirs[0]}/{fname} ({os.path.getsize(fpath)} bytes)")
        else:
            print(f"  [MISSING] {model_dirs[0]}/{fname}")
            sys.exit(1)

    print(f"[4.0-D] Sparse mapping PASS ({model_dirs[0]}, {elapsed:.1f}s)")


if __name__ == "__main__":
    main()
