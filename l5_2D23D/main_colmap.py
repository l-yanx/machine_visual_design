#!/usr/bin/env python3
"""Task 4.0: COLMAP Reconstruction Pipeline — main orchestrator.

Runs the full COLMAP pipeline:
  A: Input check (already done)
  B: Feature extraction
  C: Feature matching
  D: Sparse reconstruction
  E: Dense reconstruction
  F: Meshing
  G: GLB conversion
  H: Report generation
"""
import subprocess
import sys
import os
from datetime import datetime

ENV_ACTIVATE = "source /home/lyx/miniconda3/etc/profile.d/conda.sh && conda activate 3D_Reconstruction"

STEPS = [
    ("4.0-B Feature Extraction",      "colmap_pipeline/run_feature_extraction.py"),
    ("4.0-C Feature Matching",         "colmap_pipeline/run_matching.py"),
    ("4.0-D Sparse Reconstruction",    "colmap_pipeline/run_sparse_mapping.py"),
    ("4.0-E Dense Reconstruction",     "colmap_pipeline/run_dense_reconstruction.py"),
    ("4.0-F Meshing",                  "colmap_pipeline/run_meshing.py"),
    ("4.0-G GLB Conversion",           "colmap_pipeline/convert_to_glb.py"),
    ("4.0-H Validation & Report",      "colmap_pipeline/generate_report.py"),
]


def run_step(name, script):
    start = datetime.now()
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    cmd = f"{ENV_ACTIVATE} && python {script}"
    result = subprocess.run(cmd, shell=True, executable="/bin/bash")
    elapsed = (datetime.now() - start).total_seconds()
    if result.returncode != 0:
        print(f"\n  FAILED: {name} (exit {result.returncode}, {elapsed:.1f}s)")
        return False
    print(f"\n  PASSED: {name} ({elapsed:.1f}s)")
    return True


def main():
    print("=" * 60)
    print("  Task 4.0: COLMAP Reconstruction Pipeline")
    print(f"  Started: {datetime.now().isoformat()}")
    print("=" * 60)

    for name, script in STEPS:
        if not run_step(name, script):
            print(f"\nPipeline stopped at: {name}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("  ALL STEPS PASSED")
    print(f"  Finished: {datetime.now().isoformat()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
