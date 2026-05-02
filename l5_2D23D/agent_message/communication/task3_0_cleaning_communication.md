# Communication

## Producer
Subagent 5 V2-Task3.0 — Dense Point Cloud Quality Check & Cleaning

## Files Produced

| File | Description |
|------|-------------|
| `results/mesh/dense_cleaned.ply` | Final cleaned point cloud with normals (73,810 points) — primary handover to Task 3.1 |
| `results/mesh/dense_statistical_cleaned.ply` | After statistical outlier removal (81,930 points) |
| `results/mesh/dense_radius_cleaned.ply` | After radius outlier removal (81,773 points) |
| `results/mesh/dense_dbscan_cleaned.ply` | After DBSCAN main-cluster extraction (79,618 points) |
| `results/mesh/dense_voxel_downsampled.ply` | After voxel downsampling (73,810 points) |
| `results/mesh/dense_with_normals.ply` | Point cloud with estimated normals (73,810 points) |
| `results/mesh/cleaning_report.txt` | Chinese cleaning report with per-step statistics |
| `results/mesh/pointcloud_before_after.png` | Before/after XY/XZ/YZ projection comparison |
| `results/logs/task3_0_cleaning_log.txt` | Full pipeline execution log |

## Data Format

All PLY files use Open3D's standard PLY format:
- Binary little-endian PLY
- Vertex properties: x, y, z (float64), nx, ny, nz (float64, normals), red, green, blue (uint8, colors)
- Coordinate system: right-handed, arbitrary scale (inherited from V1 SfM)

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Point count | 88,561 | 73,810 |
| NaN points | 0 | 0 |
| Inf points | 0 | 0 |
| Bounding box X | [-5.91, 6.07] | [-4.08, 4.88] |
| Bounding box Y | [-6.20, 4.72] | [-4.72, 4.42] |
| Bounding box Z | [0.83, 12.03] | [0.83, 11.77] |
| Median NN distance | 0.1173 | 0.1120 |
| Has normals | No | Yes |
| Cleaning steps applied | — | NaN/Inf removal, duplicate removal, statistical outlier (30nn, 1.5std), radius outlier (2.5x scale, 8 min), DBSCAN (2.5x eps, 20 min, keep largest 1), voxel downsample (0.02), normal estimation (3.0x radius scale, 30 max_nn) |
| DBSCAN clusters found | — | 27, kept largest (79,618 points) |
| Total retention | — | 83.34% |

## How to Use

The primary output for downstream mesh reconstruction is:

```
results/mesh/dense_cleaned.ply
```

This file has normals and is ready for Poisson surface reconstruction or Ball Pivoting.

To load in Python:
```python
import open3d as o3d
pcd = o3d.io.read_point_cloud("results/mesh/dense_cleaned.ply")
```

Task 3.1 should NOT use `results/dense/dense.ply` directly. Use `dense_cleaned.ply` instead.

## Dependencies

- Conda environment: `3D_Reconstruction`
- Python 3.10, open3d 0.19.0, numpy 2.2.6, matplotlib 3.10.9, pyyaml
- Config file: `config.yaml` (cleaning section)

## Known Issues

1. DBSCAN eps is auto-computed from median NN distance; may need manual tuning if point density varies significantly.
2. Color filtering is disabled by default (no yellow background detected in test data).
3. Normals are oriented toward centroid+Z heuristic — may need refinement for concave objects.
4. Voxel downsample at 0.02 may lose fine detail; reduce voxel_size for higher-quality mesh input.
5. Intermediate valid_only.ply not saved because no NaN/Inf/duplicate points were found in the input.
