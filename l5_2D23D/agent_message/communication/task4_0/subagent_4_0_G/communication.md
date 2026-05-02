# Communication — Subagent 4.0-G

## Producer
Subagent 4.0-G — Mesh to GLB Conversion

## Files Produced
- `./results/colmap/model/model.glb` — GLB model for Three.js visualization (404,664 bytes)
- `./results/colmap/model/conversion_report.md` — Conversion report

## Data Format
- GLB (GL Transmission Format, binary)
- Contains mesh geometry with vertex positions, normals, colors, and face indices
- Compatible with Three.js GLTFLoader

## Metrics
| Metric | Value |
|--------|-------|
| Source mesh | meshed-delaunay.ply |
| GLB size | 404,664 bytes (~395 KB) |
| Source vertices | 11,239 |
| Source faces | 22,414 |
| Conversion method | trimesh 4.12.2 |

## How to Use
Load in Three.js:
```javascript
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
const loader = new GLTFLoader();
loader.load('./results/colmap/model/model.glb', (gltf) => {
    scene.add(gltf.scene);
});
```

## Dependencies
- Python: trimesh 4.12.2
- Source: `./results/colmap/dense/meshed-delaunay.ply`

## Known Issues
- Poisson mesh was empty (0 vertices), so Delaunay mesh was used instead.
- Model has no UV texture coordinates (texture mapping not in scope for Task 4.0).
