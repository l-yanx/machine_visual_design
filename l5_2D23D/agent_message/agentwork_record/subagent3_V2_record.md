# Agent Work Record

## Agent Name

Subagent 3 V2

## Task Name

Task 3: Mesh Reconstruction

---

## 1. 工作内容记录（中文）

### 实现的模块

#### `mesh/read_dense.py`
读取 V1 密集点云 `results/dense/dense.ply`，返回 Open3D 点云对象和检查信息（点数、颜色、法线、边界框）。

#### `mesh/pointcloud_clean.py`
点云清理流水线：
- 移除 NaN 和无穷点
- 统计离群点移除（nb_neighbors=20, std_ratio=2.0）
- 体素降采样（voxel_size=0.005）
- 471,159 → 445,317 → 445,271 点

#### `mesh/normal_estimation.py`
法线估计与方向校正：
- 使用混合 KD 树搜索估计法线（radius=0.02, max_nn=30）
- 方向校正使法线指向点云中心

#### `mesh/poisson_recon.py`
Poisson 曲面重建：
- 使用 Open3D `create_from_point_cloud_poisson`（depth=8, scale=1.1）
- 按点云边界框裁剪网格
- 原始网格：311,515 顶点, 626,858 三角形

#### `mesh/mesh_cleanup.py`
网格清理流水线：
- 移除低 Poisson 密度的顶点（低于第 5 百分位）
- 移除未引用顶点
- 移除退化/重复三角形和顶点
- 保留最大连通分量

#### `mesh/mesh_simplify.py`
网格简化：
- 使用二次误差度量边折叠
- 目标：100,000 三角形（597,886 → 99,999）

#### `mesh/export_model.py`
模型导出：
- `model.ply`：PLY 格式
- `model.obj`：OBJ 格式
- `model.glb`：glTF 二进制格式（Open3D 直接导出）

#### `main_mesh.py`
主流水线脚本：按顺序执行 7 个步骤，读取 config.yaml，记录日志。

### 使用的输入数据

- V1 密集点云：`results/dense/dense.ply`（471,159 点，带颜色）
- 配置文件：`config.yaml`

### 输出的结果文件

- `results/mesh/cleaned_dense.ply`（445,271 点）
- `results/mesh/cleaned_dense_with_normals.ply`（445,271 点，带法线）
- `results/mesh/mesh_poisson_raw.ply`（311,515 顶点, 626,858 三角形）
- `results/mesh/mesh_cleaned.ply`（295,577 顶点, 597,886 三角形）
- `results/mesh/mesh_simplified.ply`（47,235 顶点, 99,999 三角形）
- `results/mesh/model.ply`
- `results/mesh/model.obj`
- `results/mesh/model.glb`
- `results/logs/mesh_log.txt`

### 参数说明

| 参数 | 值 | 说明 |
|------|-----|------|
| poisson_depth | 8 | Poisson 重建八叉树深度 |
| poisson_scale | 1.1 | Poisson 重建尺度因子 |
| poisson_linear_fit | false | 不使用线性拟合 |
| simplify_target_triangles | 100000 | 简化目标三角形数 |
| outlier_nb_neighbors | 20 | 离群点检测邻域大小 |
| outlier_std_ratio | 2.0 | 离群点检测标准差比例 |
| voxel_downsample | 0.005 | 体素降采样大小 |
| keep_largest_component | true | 仅保留最大连通分量 |

---

## 2. 程序执行结果（中文）

### 执行命令

```bash
source /home/lyx/miniconda3/etc/profile.d/conda.sh && conda activate 3D_Reconstruction
python main_mesh.py --config config.yaml
```

### 执行结果

**成功**

### 关键指标

| 指标 | 数值 |
|------|------|
| 输入密集点数 | 471,159 |
| 清理后点数 | 445,271（去除了 5,888 离群点） |
| 体素降采样后点数 | 445,271（0.005m 体素几乎无降采样） |
| 原始 Poisson 网格 | 311,515 顶点, 626,858 三角形 |
| 清理后网格 | 295,577 顶点, 597,886 三角形 |
| 简化后网格 | 47,235 顶点, 99,999 三角形 |
| 简化比例 | 16.7%（保留约 1/6 的三角形） |
| 网格带顶点颜色 | 是 |
| model.glb 大小 | 3.0 MB |
| 总运行时间 | 9.9 秒 |

### Poisson 重建警告

生成原始 Poisson 网格时出现了少量 "bad average roots: 3" 警告。这是 Poisson 重建中在少数八叉树节点的已知数值问题，不影响整体网格质量。

### 接受标准验证

| 标准 | 状态 |
|------|------|
| results/dense/dense.ply 成功读取 | PASS |
| cleaned_dense.ply 生成并可打开 | PASS |
| 为清理后点云估算法线 | PASS |
| Poisson 网格已生成 | PASS（626,858 三角形） |
| 低密度/漂浮网格碎片已减少 | PASS（移除低密度顶点 + 保留最大连通分量） |
| model.ply 生成并可打开 | PASS |
| model.obj 已生成 | PASS |
| model.glb 已生成 | PASS（Open3D 直接导出） |
| 网格大致保留雕塑表面结构 | PASS |
| 无大规模飞面占据主导地位 | PASS（裁剪到边界框 + 清理） |
| mesh_log.txt 记录关键参数和指标 | PASS |
| subagent3_V2_record.md 已完成 | PASS |

---

## 3. Handover to Next Agent（English）

### Files Ready for Task 4 (Three.js Frontend)

All mesh outputs are available at:

- **GLB model** (preferred for Three.js): `results/mesh/model.glb` (3.0 MB)
  - 47,235 vertices, 99,999 triangles, with vertex colors
  - Binary glTF format — loadable via `THREE.GLTFLoader`

- **OBJ model** (fallback): `results/mesh/model.obj` (7.9 MB)
  - Same mesh in OBJ format

- **PLY model**: `results/mesh/model.ply` (3.6 MB)
  - PLY format with vertex colors

### Pipeline Summary

1. Read V1 dense.ply (471,159 points) → 2. Clean (445,271 points) → 3. Estimate normals → 4. Poisson reconstruction (626,858 triangles) → 5. Clean mesh (remove low-density vertices, keep largest component) → 6. Simplify to 100K triangles → 7. Export PLY/OBJ/GLB

### Assumptions

1. The Poisson reconstruction quality depends on point cloud density and normal quality.
2. Model exported with vertex colors preserved (no texture mapping — per V2 spec).
3. The coordinate system matches V1 world coordinates (origin at camera 005).
4. Mesh scale matches the arbitrary V1 reconstruction scale.
5. The GLB file was exported directly via Open3D and should be compatible with Three.js GLTFLoader.

### Known Issues

1. **Poisson warning**: Minor "bad average roots: 3" warnings from Poisson reconstruction — these are harmless numerical artifacts.
2. **No texture mapping**: Mesh has vertex colors only (per V2 spec limitation).
3. **Mesh may have some minor bumps**: Poisson reconstruction can produce small surface artifacts in sparsely sampled regions.
4. **Arbitrary scale**: Inherited from V1's uncalibrated SfM.
5. **GLB export**: Exported via Open3D's `write_triangle_mesh`. If the Three.js GLTFLoader cannot parse it, use the OBJ fallback.

### What Subagent 4 Should Pay Attention To

1. Primary model: `results/mesh/model.glb` — copy to `frontend/assets/model.glb`
2. Fallback: `results/mesh/model.obj` — if GLB loading fails
3. Also copy: `results/dense/dense.ply`, `results/sparse/sparse.ply`, `results/sparse/cameras.json` to `frontend/assets/`
4. The vertex colors are stored as RGB 0-1 float values
5. Use `THREE.GLTFLoader` to load the GLB, or `THREE.OBJLoader` for OBJ
6. The mesh has exactly 99,999 triangles — suitable for real-time rendering
7. Coordinate origin is at camera 005 position
