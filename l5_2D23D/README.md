# 1. 项目简介与技术路线

## 项目目标

本工程的目标是**基于多视角二维图像重建目标物体的三维结构**。

- **输入**：多张从不同视角拍摄的目标物体 RGB 图像（`data/image/`）
- **输出**：稀疏点云、稠密点云、Mesh 网格、GLB 模型、Three.js 前端展示

## 技术路线概览

项目包含两条技术路线：

| 路线 | 说明 | 目的 |
|---|---|---|
| **传统 Pipeline（V1–V3）** | 从零实现 SfM / MVS / Mesh 全流程 | 理解底层原理，掌握重建 pipeline 各环节 |
| **COLMAP 工具链（V4）** | 使用 COLMAP 作为重建后端 | 追求更好的实际重建效果，作为最终展示路线 |

## 传统重建 Pipeline

多视角图像输入 → 图像预处理 → SIFT 特征提取 → 特征匹配 → RANSAC 几何验证 → 增量式 SfM（Incremental Structure-from-Motion）→ 相机位姿恢复 → 三角测量生成稀疏点云 → MVS 深度估计（Multi-View Stereo）→ 深度图融合生成稠密点云 → 点云清理 → Mesh 重建（Poisson / Ball Pivoting）→ GLB 导出 → Three.js 前端展示

## V4 COLMAP Pipeline

图像输入 → COLMAP `feature_extractor` → COLMAP `matcher`（exhaustive_matcher）→ COLMAP `mapper`（稀疏重建 + Bundle Adjustment）→ COLMAP `image_undistorter` → COLMAP `patch_match_stereo`（深度估计）→ COLMAP `stereo_fusion`（深度融合）→ COLMAP `poisson_mesher` / `delaunay_mesher` → GLB 转换（trimesh）→ Three.js 展示

COLMAP（COLMAP Structure-from-Motion and Multi-View Stereo）是本项目 V4 调用的成熟重建工具包，提供完整的 SfM、Bundle Adjustment、PatchMatch MVS、深度融合和 Mesh 重建流程。COLMAP 作为外部命令行工具运行，Python 侧通过脚本编排其调用顺序并处理输出格式转换。

---

# 2. 文件架构

## 目录总览

```
./
├── data/
│   ├── image/                    # 输入图像（原始尺寸）
│   └── images_resized/           # 预处理后的缩放图像
│
├── colmap_pipeline/              # V4 COLMAP 管道脚本
│   ├── check_inputs.py           #   输入检查
│   ├── run_feature_extraction.py #   特征提取
│   ├── run_matching.py           #   特征匹配
│   ├── run_sparse_mapping.py     #   稀疏重建
│   ├── run_dense_reconstruction.py # 稠密重建
│   ├── run_meshing.py            #   Mesh 生成
│   ├── convert_to_glb.py         #   GLB 格式转换
│   └── generate_report.py        #   重建报告生成
│
├── results/
│   └── colmap/                   # V4 COLMAP 输出
│       ├── database.db           #   COLMAP 特征数据库
│       ├── sparse/               #   稀疏重建结果（相机位姿、稀疏点云）
│       ├── dense/                #   稠密重建结果
│       │   ├── fused.ply         #     融合后的稠密点云
│       │   ├── meshed-poisson.ply #    Poisson Mesh
│       │   └── meshed-delaunay.ply #   Delaunay Mesh
│       ├── model/
│       │   └── model.glb         #   用于 Three.js 展示的 GLB 模型
│       ├── report/               #   重建报告与可视化
│       ├── logs/                 #   各步骤运行日志
│       └── check/                #   输入检查报告
│
├── agent_message/                # Agent 任务文件与工作记录
│   ├── agentwork_record/         #   各 Agent 的工作交接记录
│   └── communication/            #   Subagent 间通信文件
│
├── main_colmap.py                # V4 COLMAP 全流程主脚本
├── config.yaml                   # 全局配置文件
└── README.md
```

## 目录说明

**`data/image/`** — 存放输入的多视角目标物体图像（.jpg）。当前包含 20 张从不同角度拍摄的雕塑图像。对应任务阶段：图像采集与输入。

**`colmap_pipeline/`** — 存放 V4 COLMAP 重建管道的各步骤脚本。每个脚本对应 COLMAP 的一个子命令，由 `main_colmap.py` 统一编排调用。对应任务阶段：V4 成熟工具链重建全流程。

**`results/colmap/`** — 存放 COLMAP 重建的全部输出，包括数据库、稀疏/稠密点云、Mesh、GLB 模型、报告和日志。是重建结果的集中存储位置。

**`agent_message/`** — 存放项目各版本的任务需求文档（V1–V4 Task）、Agent 工作记录和通信交接文件。用于记录开发过程和 Agent 间信息传递。

**`config.yaml`** — 全局配置文件，包含 SfM、MVS、Mesh、点云清理等模块的参数以及文件路径配置。所有脚本通过读取此文件获取运行参数。

**`main_colmap.py`** — V4 全流程入口脚本，按顺序编排 COLMAP 管道的所有步骤，从输入检查到 GLB 导出。

---

# 3. 版本迭代过程

## V1 — 自研增量式 SfM + ZNCC-MVS

V1 从零实现了传统的多视角三维重建 pipeline 的核心环节，目标是理解 SfM 和 MVS 的底层流程。

**SfM 模块（增量式 Structure-from-Motion）：**

1. **SIFT 特征提取**：从每张图像中提取尺度不变局部特征点（关键点 + 描述子），作为跨图像匹配的基础。
2. **特征匹配**：在相邻图像之间使用 KNN + Lowe Ratio Test 建立特征对应关系。
3. **RANSAC 几何验证**：通过随机采样一致性算法估计本质矩阵（Essential Matrix），剔除错误匹配对。
4. **初始图像对选择**：根据匹配内点数量与比例评分，选择最佳初始图像对。
5. **增量式 SfM**：从初始图像对开始，逐步注册剩余图像 —— 通过 PnP（Perspective-n-Point）估计新图像相机位姿，再通过三角测量（Triangulation）恢复新的三维点，迭代扩展场景。
6. **输出**：稀疏点云、注册相机位姿、2D-3D 特征轨迹。

**MVS 模块（ZNCC 多视角立体重建）：**

1. **深度范围估计**：利用稀疏点云估计每张参考图像的深度搜索范围（取 5%–95% 分位数）。
2. **平面扫描深度估计**：在深度范围内对每个像素（按步长采样）进行平面扫描，通过 ZNCC（Zero-mean Normalized Cross-Correlation）计算参考图像块与源视角图像块的相似度，选取最高分的深度值。
3. **深度图滤波**：去除低置信度、负深度、超出范围的深度值。
4. **反投影与融合**：将各视图深度图反投影为局部点云，合并后经体素下采样和统计离群点去除，生成稠密点云。

**V1 输出：**
- `results/sparse/sparse.ply` — 稀疏点云
- `results/sparse/cameras.json` — 相机内参
- `results/sparse/camera_poses.txt` — 相机位姿
- `results/sparse/points3D.json` — 三维点
- `results/sparse/tracks.json` — 特征轨迹
- `results/dense/dense.ply` — 稠密点云
- `results/dense/depth_maps/` — 深度图
- `results/dense/confidence_maps/` — 置信度图

---

## V2 — Mesh 重建与 Three.js 展示

V2 在 V1 稠密点云的基础上，将其转换为可展示的三维网格模型，并搭建网页端可视化。

**Mesh 重建模块：**

1. **点云不是最终模型**：稠密点云是离散采样点，Mesh 才是连续表面表达，更适合渲染和交互展示。
2. **法向估计（Normal Estimation）**：对清洗后的点云计算局部邻域法向量，为表面重建提供几何方向信息。
3. **泊松表面重建（Poisson Surface Reconstruction）**：根据点云和法向生成连续光滑的三角网格表面。
4. **Ball Pivoting（可选）**：基于局部点云连接三角面的方法，适合快速局部表面实验。
5. **低密度区域清理**：去除泊松重建中低置信度的顶点和面片，保留主体结构。
6. **网格简化**：将面片数控制在 5–20 万以内，适配前端加载。
7. **GLB/GLTF 导出**：将 Mesh 转换为 Three.js 可直接加载的三维模型格式。

**Three.js 前端展示：**

- 支持 Mesh 模型、稠密点云、稀疏点云、相机位姿四种显示模式
- 支持轨道控制（旋转、缩放、平移）
- 支持显示模式切换
- 以 `model.glb` 作为主要加载格式

> **注意**：直接从含有噪声的稠密点云生成 Mesh 可能出现尖刺、破面、飞面（flying triangles）等问题。这是 V2 阶段已知的局限，驱动了 V3 点云清理的引入。

---

## V3 — 点云质量检查、清理与 Mesh 前置优化

V3 的核心理念是：**在 Mesh 重建之前对稠密点云进行系统化清理，避免噪声放大**。

**为什么需要清理：**

1. MVS 输出的 `dense.ply` 可能含有飞点、背景残留点、错误深度点和孤立小簇。
2. 如果直接对未清理的点云做 Mesh，噪声会在表面重建过程中被放大，导致尖刺、破面、飞面等缺陷。
3. 因此 V3 引入 `dense_cleaned.ply` 作为 Mesh 重建的前置门控 —— 只有通过清理的点云才能进入 Mesh 阶段。

**点云清理流程：**

- 统计离群点去除（Statistical Outlier Removal）：基于局部邻域距离分布剔除异常点
- 半径离群点去除（Radius Outlier Removal）：剔除局部稀疏区域中的孤立点
- DBSCAN 聚类主体保留：识别并保留最大的主体簇，去除背景小簇
- 体素下采样（Voxel Downsampling）：均匀化点云密度，控制后续计算量
- 法向估计：为 Mesh 重建准备法向信息
- 可视化质量检查：输出清理前后的 XY/XZ/YZ 投影对比图

**V3 输出：**
- `results/mesh/dense_cleaned.ply` — 清理后的点云
- `results/mesh/cleaning_report.txt` — 清理报告（点云数量变化、各步骤统计）
- `results/mesh/pointcloud_before_after.png` — 清理前后对比图

---

## V4 — COLMAP 成熟工具链

**动机：**

1. 自研 SfM/MVS 有助于理解底层原理，但受限于实现复杂度，工程重建效果存在瓶颈。
2. 当前项目目标转为追求重建质量，因此引入 COLMAP 作为成熟的 SfM/MVS 重建后端。
3. COLMAP 提供了经过大量验证的 SfM、Bundle Adjustment、PatchMatch MVS、深度融合和 Mesh 重建流程。
4. V4 的目标是生成更可靠的 `fused.ply`、`mesh.ply` 和 `model.glb`。
5. V4 可以作为最终展示路线，也可以作为自研 pipeline 的 baseline 对照。

**V4 流程（编排自 COLMAP 子命令）：**

```
图像输入 → feature_extractor → exhaustive_matcher → mapper
→ image_undistorter → patch_match_stereo → stereo_fusion
→ poisson_mesher / delaunay_mesher → GLB 转换 → Three.js 展示
```

**V4 输出：**
- `results/colmap/sparse/` — 稀疏重建（`cameras.bin`, `images.bin`, `points3D.bin`）
- `results/colmap/dense/fused.ply` — 融合稠密点云
- `results/colmap/dense/meshed-poisson.ply` — Poisson Mesh
- `results/colmap/dense/meshed-delaunay.ply` — Delaunay Mesh
- `results/colmap/model/model.glb` — GLB 模型
- `results/colmap/report/reconstruction_report.md` — 重建报告

---

# 4. 总结

传统方案效果并不佳，所以最后选用了成熟工具链，详细迭代代码在地址**https://github.com/l-yanx/machine_visual_design.git**
