# Communication — Subagent 4.0-D

## Producer
Subagent 4.0-D — COLMAP Sparse Reconstruction

## Files Produced
- `./results/colmap/sparse/0/cameras.bin` — Camera parameters (64 bytes, single shared camera)
- `./results/colmap/sparse/0/images.bin` — Registered image poses (158,848 bytes, 20 images)
- `./results/colmap/sparse/0/points3D.bin` — Sparse 3D points (20,382 bytes)
- `./results/colmap/logs/sparse_mapping.log` — Sparse mapping log

## Data Format
COLMAP binary model format (sparse/0/):
- cameras.bin: camera intrinsics (SIMPLE_PINHOLE or similar)
- images.bin: world-to-camera poses (quaternion + translation)
- points3D.bin: sparse 3D points with tracks and colors

## Metrics
| Metric | Value |
|--------|-------|
| Sparse model folder | sparse/0 |
| Images registered | 20 |
| Model 0/0/cameras.bin | 64 bytes |
| Model 0/0/images.bin | 158,848 bytes |
| Model 0/0/points3D.bin | 20,382 bytes |
| Runtime | 0.3 seconds |
| Exit code | 0 |

## How to Use
Sparse model path for dense reconstruction:
```
--input_path ./results/colmap/sparse/0
```

## Dependencies
- `./results/colmap/database.db` (with features and matches)
- `./data/image/` (input images)
- COLMAP 3.8 (CUDA)

## Known Issues
None. All 20 images registered successfully.
