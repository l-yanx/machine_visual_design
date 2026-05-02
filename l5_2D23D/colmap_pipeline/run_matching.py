"""Task 4.0-C: COLMAP Feature Matching."""
import subprocess
import sys
import os
from datetime import datetime

LOG_DIR = "./results/colmap/logs"
DB_PATH = "./results/colmap/database.db"


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
    log_path = os.path.join(LOG_DIR, "matching.log")

    # Exhaustive matching for < 100 images
    cmd = [
        "colmap", "exhaustive_matcher",
        "--database_path", DB_PATH,
        "--SiftMatching.use_gpu", "1",
    ]
    print("[4.0-C] Running exhaustive matching (GPU)...")
    ok, elapsed, stderr = run(cmd, log_path)

    mode = "GPU"
    if not ok:
        print("[4.0-C] GPU failed, trying CPU fallback...")
        cmd[-1] = "0"
        ok, elapsed, stderr = run(cmd, log_path)
        mode = "CPU"

    if ok:
        print(f"[4.0-C] Feature matching PASS ({mode}, {elapsed:.1f}s)")
    else:
        print(f"[4.0-C] Feature matching FAILED ({mode})")
        sys.exit(1)


if __name__ == "__main__":
    main()
