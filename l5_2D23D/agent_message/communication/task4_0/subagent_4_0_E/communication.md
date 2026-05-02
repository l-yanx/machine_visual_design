# Communication — Subagent 4.0-E

## Producer
Subagent 4.0-E — COLMAP Dense Reconstruction

## Files Produced
- `./results/colmap/dense/fused.ply` — Fused dense point cloud (1,039,517 bytes, 38,492 points)
- `./results/colmap/dense/` — Dense workspace (undistorted images, stereo depth maps, normal maps)
- `./results/colmap/logs/image_undistorter.log` — Undistortion log
- `./results/colmap/logs/patch_match_stereo.log` — PatchMatch stereo log
- `./results/colmap/logs/stereo_fusion.log` — Stereo fusion log

## Data Format
- fused.ply: PLY point cloud with XYZ, RGB (0-255), and normals (nx, ny, nz)
- Coordinate system: COLMAP world coordinates (arbitrary scale)

## Metrics
| Metric | Value |
|--------|-------|
| fused.ply points | 38,492 |
| fused.ply size | 1,039,517 bytes (~1 MB) |
| Image undistortion runtime | 0.3 s |
| PatchMatch stereo runtime | 81.1 s |
| Stereo fusion runtime | 2.3 s |
| Geometric consistency | enabled |
| Total runtime | ~84 s |

## How to Use
fused.ply is the input for meshing (Subagent 4.0-F):
```
colmap poisson_mesher --input_path ./results/colmap/dense/fused.ply --output_path ./results/colmap/dense/meshed-poisson.ply
colmap delaunay_mesher --input_path ./results/colmap/dense --output_path ./results/colmap/dense/meshed-delaunay.ply
```

## Dependencies
- COLMAP 3.8 (CUDA)
- `./results/colmap/sparse/0/` (sparse model)
- `./data/image/` (original images)

## Known Issues
None. All three dense reconstruction steps completed successfully.
