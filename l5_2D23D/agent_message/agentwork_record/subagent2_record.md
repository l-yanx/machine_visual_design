# Agent Work Record

## Agent Name

Subagent 2

## Task Name

Task 2: ZNCC-based MVS and Dense PLY Generation

---

## 1. 工作内容记录（中文）

### 实现的模块

#### `mvs/read_sfm.py`
读取 Task 1 导出的 SfM 结果文件（cameras.json、points3D.json、tracks.json），构建 K 矩阵、相机位姿字典、3D 点字典和 track 字典。

#### `mvs/view_selection.py`
基于稀疏点可见性的源视图选择：对于每个参考图像，统计与其他已注册图像的共享稀疏 3D 点数量，按共享点数降序选择前 N 个源视图。导出到 view_pairs.json。

#### `mvs/depth_range.py`
深度范围估计：将稀疏 3D 点变换到每个参考相机坐标系，取正深度点的百分位数作为深度范围，使用 5%/95% 百分位并扩展 0.9/1.1 倍。导出到 depth_ranges.json。

#### `mvs/zncc.py`
ZNCC 相似度计算：实现零均值归一化互相关，支持批量计算（向量化）。低方差区域标记为无效（阈值 1e-5）。支持 5x5 图像块提取。

#### `mvs/plane_sweep.py`
平面扫描深度估计：
- 使用稀疏 3D 点投影构建种子像素掩码（seed mask），限制处理范围
- 对每个种子像素，在深度范围内采样 48 层深度候选
- 反投影 + 投影到源视图，提取图像块并计算 ZNCC
- 聚合多视图 ZNCC 分数，选择最高分数的深度
- 保存深度图和置信度图（ZNCC 阈值 0.5）
- 关键优化：patch_size=5, stride=2, seed_pixel_radius=20

#### `mvs/depth_filter.py`
深度图过滤：移除低置信度、零深度和超出深度范围的像素。支持中值滤波（可选）。

#### `mvs/depth_to_pointcloud.py`
深度图反投影：将深度像素通过 K⁻¹ 反投影到相机坐标系，再通过 R⁻¹ 变换到世界坐标系。从参考图像采样颜色。

#### `mvs/pointcloud_fusion.py`
点云融合：合并所有局部点云，体素降采样（voxel=0.02），统计离群点移除（nb_neighbors=20, std_ratio=2.0），导出 dense.ply。

#### `main_mvs.py`
MVS 主脚本：按顺序执行 8 个步骤，读取 config.yaml，记录运行日志到 mvs_log.txt。

### 使用的输入数据

- Task 1 SfM 输出：`results/sparse/cameras.json`、`results/sparse/points3D.json`、`results/sparse/tracks.json`
- 缩放后图像：`data/images_resized/`（23 个已注册图像）
- 配置文件：`config.yaml`

### 输出的结果文件

- `results/dense/dense.ply`（471,159 点，带颜色）
- `results/dense/view_pairs.json`（23 个视图对）
- `results/dense/depth_ranges.json`（23 个深度范围）
- `results/dense/depth_maps/`（23 个深度图 .npy）
- `results/dense/confidence_maps/`（23 个置信度图 .npy）
- `results/dense/depth_maps_filtered/`（23 个过滤后深度图 .npy）
- `results/dense/partial_pointclouds/`（23 个局部点云 .ply）
- `results/logs/mvs_log.txt`

### 配置参数修改

为优化处理速度，调整了 config.yaml 中的参数：
- `mvs.seed_pixel_radius`: 新增参数（30 → 20）
- `mvs.depth_samples`: 64 → 48

---

## 2. 程序执行结果（中文）

### 执行命令

```bash
source /home/lyx/miniconda3/etc/profile.d/conda.sh && conda activate 3D_Reconstruction
python main_mvs.py --config config.yaml --image_limit 23
```

### 执行结果

**成功**

### 关键指标

| 指标 | 数值 |
|------|------|
| 已注册图像数 | 23 |
| 源视图选择 | 全部 23 个图像成功分配 3 个源视图 |
| 深度范围估计 | 全部 23 个图像成功估计深度范围 |
| 深度图生成 | 23/23（100%）|
| 置信度图生成 | 23/23（100%）|
| 过滤后深度图 | 23/23（100%）|
| 局部点云生成 | 23/23（100%）|
| 总部分点云点数 | 548,028 |
| 融合后 dense.ply 点数 | 471,159 |
| 稀疏点云点数 | 2,699 |
| 密集/稀疏比例 | 174.6x |
| 飞行点比例（>5 sigma）| 0.08% |
| 平面扫描耗时 | 578.6 秒（9.6 分钟）|
| 总运行时间 | ~9.6 分钟 |

### 深度图质量

每张图像的种子像素中约有 36-69% 通过了 ZNCC 阈值，生成有效深度值。每张图像的有效深度像素数范围为 16,183 到 31,530 个。

### 接受标准验证

| 标准 | 状态 |
|------|------|
| 成功读取 Task 1 SfM 输出 | PASS |
| 每个参考图像有有效源视图 | PASS（23/23）|
| 每个参考图像有有效深度范围 | PASS（23/23）|
| >=3 个参考图像产生有效深度图 | PASS（23/23）|
| 深度图包含有效深度值 | PASS（548,028 像素）|
| 置信度图与深度图一同生成 | PASS |
| 过滤后深度图移除无效值 | PASS |
| 可从深度图生成局部点云 | PASS（23 个 PLY）|
| dense.ply 可在 Open3D 打开 | PASS |
| dense.ply 点数 >> sparse.ply | PASS（174.6x）|
| 密集点云大致显示雕塑表面 | PASS |
| 无明显大量飞行点 | PASS（0.08% >5 sigma）|

---

## 3. Handover to Next Agent（English）

### Files Ready for Core Agent

All MVS outputs are available at:

- **Dense point cloud**: `results/dense/dense.ply` — 471,159 colored points, 174.6x the sparse count
  - Format: ASCII PLY with vertex colors
  - Bounding box: X[-60.7, 102.8], Y[-68.8, 57.7], Z[-3.4, 132.8]
  - 0.08% points beyond 5 sigma from centroid

- **Depth maps**: `results/dense/depth_maps/` — 23 .npy files (1334x1000 float64)
- **Confidence maps**: `results/dense/confidence_maps/` — 23 .npy files
- **Filtered depth maps**: `results/dense/depth_maps_filtered/` — 23 .npy files
- **Partial point clouds**: `results/dense/partial_pointclouds/` — 23 .ply files (548K total points)
- **View pairs**: `results/dense/view_pairs.json` — 23 entries
- **Depth ranges**: `results/dense/depth_ranges.json` — 23 entries
- **MVS log**: `results/logs/mvs_log.txt`

### Assumptions

1. Task 2 reads only exported Task 1 files (cameras.json, points3D.json, tracks.json). No internal variables from Task 1 are used.
2. The same K matrix (fx=fy=1200, cx=500, cy=667) applies to all cameras.
3. All 23 registered images were processed for MVS.
4. Seed pixel masks are built from sparse 3D point projections with radius=20 to restrict computation.
5. Plane sweep uses stride=2, so depth maps are at half the input resolution.

### Known Issues

1. ZNCC plane sweeping is computationally expensive (~30s per image with 200K seed pixels).
2. The dense point cloud may have some noise near the edges of the sculpture where ZNCC matching is less reliable.
3. No mesh reconstruction or texture mapping (per V1 spec).
4. The reconstruction scale is arbitrary (inherited from Task 1's uncalibrated SfM).

### What Core Agent Should Pay Attention To

1. The dense.ply is ready for visualization in Open3D, MeshLab, or CloudCompare.
2. The depth range for some images is very wide (up to 137m max), which reduces depth precision (48 samples over a wide range).
3. The seed-pixel-based approach means depth is only estimated near sparse point projections — gaps in the sparse reconstruction result in gaps in depth estimation.
4. For V2, consider implementing bundle adjustment in Task 1 and using GPU-accelerated plane sweeping in Task 2.
