# Communication — Subagent 4.0-F

## Producer
Subagent 4.0-F — COLMAP Meshing

## Files Produced
- `./results/colmap/dense/meshed-poisson.ply` — Poisson surface reconstruction (1,044 bytes, **empty: 0 vertices, 0 faces**)
- `./results/colmap/dense/meshed-delaunay.ply` — Delaunay triangulation (426,425 bytes, 11,239 vertices, 22,414 faces)
- `./results/colmap/logs/poisson_mesher.log` — Poisson meshing log
- `./results/colmap/logs/delaunay_mesher.log` — Delaunay meshing log

## Data Format
- PLY mesh format with vertices (x, y, z), faces (vertex indices), and optionally vertex colors
- Both meshes in COLMAP world coordinates

## Metrics
| Metric | Poisson | Delaunay |
|--------|---------|----------|
| Vertices | 0 | 11,239 |
| Faces | 0 | 22,414 |
| File size | 1,044 B | 426,425 B |
| Runtime | 26.1 s | 0.9 s |
| Status | FAIL (empty) | PASS |

## Recommended Mesh
**meshed-delaunay.ply** — The Poisson reconstruction produced an empty mesh (likely due to sparse/irregular point distribution). The Delaunay mesh is valid and should be used for GLB conversion.

## How to Use
Use meshed-delaunay.ply for GLB conversion:
```python
import trimesh
mesh = trimesh.load("./results/colmap/dense/meshed-delaunay.ply")
mesh.export("./results/colmap/model/model.glb")
```

## Dependencies
- `./results/colmap/dense/fused.ply`
- `./results/colmap/dense/` (dense workspace for Delaunay mesher)
- COLMAP 3.8

## Known Issues
- Poisson mesher produced an empty mesh — this is expected when the point cloud has irregular sampling or gaps.
- Delaunay mesh may contain artifacts for non-watertight surfaces.
