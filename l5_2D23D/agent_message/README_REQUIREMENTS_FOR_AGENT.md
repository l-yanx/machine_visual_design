# README Writing Requirements for Agent

## Purpose

Write or update the project `README.md` according to the structure and content requirements below.

The README should explain the overall purpose of the project, the traditional reconstruction pipeline, the iterative development process from V1 to V4, the project file structure, and the environment/package management method.

The README should be written in Chinese. Technical terms may include English names in parentheses when helpful.

---

# README Required Structure

The README must contain the following five main sections:

```text
1. 项目简介与技术路线
2. 文件架构
3. 版本迭代过程
4. 环境与包管理
5. 总结
```

Section 5 should be left mostly empty for the user to fill in later.

---

# Section 1: 项目简介与技术路线

## Required Content

This section should explain:

```text
1. 本工程的目标：基于多视角二维图像重建三维结构。
2. 输入是什么：多张从不同视角拍摄的目标物体图像。
3. 输出是什么：稀疏点云、稠密点云、Mesh、GLB 模型、Three.js 前端展示。
4. 传统方案 pipeline 是什么。
5. V4 中调用的成熟工具包是什么，以及它在工程中的作用。
```

## Traditional Pipeline to Describe

The traditional reconstruction pipeline should be described clearly:

```text
多视角图像输入
→ 图像预处理
→ SIFT 特征提取
→ 特征匹配
→ RANSAC 几何验证
→ 增量式 SfM
→ 相机位姿恢复
→ 三角测量生成稀疏点云
→ MVS 深度估计
→ 深度图融合生成稠密点云
→ 点云清理
→ Mesh 重建
→ GLB 导出
→ Three.js 前端展示
```

## V4 Package-Based Pipeline to Describe

Explain that V4 uses COLMAP as the mature reconstruction backend.

The V4 package-based pipeline should include:

```text
图像输入
→ COLMAP feature_extractor
→ COLMAP matcher
→ COLMAP mapper
→ COLMAP image_undistorter
→ COLMAP patch_match_stereo
→ COLMAP stereo_fusion
→ COLMAP poisson_mesher / delaunay_mesher
→ GLB 转换
→ Three.js 展示
```

## Required Explanation

The README should clearly distinguish:

```text
1. 自研传统 pipeline：用于理解和实现 SfM/MVS 底层流程。
2. V4 COLMAP pipeline：用于追求更好的实际重建效果。
```

---

# Section 2: 文件架构

## Required Content

This section should describe the project directory structure.

The agent should inspect the actual project files first, then write the file structure based on the real project.

If some directories do not exist yet, the README may still include them as planned directories, but should not falsely claim that generated results exist unless they are actually present.

## Recommended Directory Structure to Explain

The README should cover directories similar to:

```text
./
├── data/
│   └── image/                    # 输入图像
│
├── sfm/                          # 自研 SfM 模块
├── mvs/                          # 自研 MVS 模块
├── mesh/                         # 点云清理与 Mesh 重建模块
├── frontend/                     # Three.js 前端展示
├── visualization/                # 可视化与质量评估脚本
│
├── results/
│   ├── sparse/                   # SfM 输出
│   ├── dense/                    # MVS 输出
│   ├── mesh/                     # Mesh 与 GLB 输出
│   ├── colmap/                   # V4 COLMAP 输出
│   ├── visualization/            # 可视化结果
│   └── logs/                     # 运行日志
│
├── agent_message/
│   └── agentwork_record/         # agent 工作记录与交接文件
│
├── main_sfm.py                   # 自研 SfM 主程序
├── main_mvs.py                   # 自研 MVS 主程序
├── config.yaml                   # 全局配置文件
└── README.md
```

## Required Details

For each important folder, briefly explain:

```text
1. 该目录存放什么文件。
2. 它对应哪个任务阶段。
3. 它的输入/输出关系。
```

---

# Section 3: 版本迭代过程

## Required Content

This section must explain the iterative process according to the tasks:

```text
V1: 自研增量式 SfM + ZNCC-MVS，输出 sparse.ply 和 dense.ply
V2: Mesh 重建与 Three.js 展示
V3: 点云质量检查、清理与 Mesh 前置优化
V4: 使用 COLMAP 成熟工具链追求更好重建效果
```

The README must explain V1, V2, and V3 with clear principles.

V4 should explain that the project switches to or adds a mature package-based baseline because the user currently prioritizes reconstruction quality.

---

## V1 Required Explanation

V1 should explain the principle of the self-developed traditional reconstruction pipeline.

Must include:

```text
1. SIFT 特征提取的作用：从图像中提取稳定局部特征。
2. 特征匹配的作用：建立不同图像之间的对应点关系。
3. RANSAC 的作用：剔除错误匹配，估计本质矩阵或基础矩阵。
4. 增量式 SfM 的作用：逐步注册图像，恢复相机位姿。
5. 三角测量的作用：由多视角匹配点恢复三维点。
6. ZNCC-MVS 的作用：根据多视角图像块相似性估计深度。
7. 深度图融合的作用：将多张深度图反投影并融合为稠密点云。
```

V1 outputs should include:

```text
results/sparse/sparse.ply
results/sparse/cameras.json
results/sparse/camera_poses.txt
results/sparse/points3D.json
results/sparse/tracks.json
results/dense/dense.ply
results/dense/depth_maps/
results/dense/confidence_maps/
```

---

## V2 Required Explanation

V2 should explain the principle of converting point cloud to displayable 3D model.

Must include:

```text
1. 稠密点云不是最终可展示模型，Mesh 才是连续表面表达。
2. 法向估计的作用：为表面重建提供局部几何方向。
3. Poisson Surface Reconstruction 的作用：根据点云和法向生成连续表面。
4. Ball Pivoting 的作用：根据局部点云连接三角面，适合局部表面实验。
5. GLB/GLTF 的作用：作为 Three.js 可加载的三维模型格式。
6. Three.js 的作用：在网页端加载、旋转、缩放和展示三维模型。
```

V2 should also mention that direct Mesh from noisy dense point clouds may produce spikes, broken surfaces, or flying triangles.

---

## V3 Required Explanation

V3 should explain why point cloud cleaning is necessary before Mesh.

Must include:

```text
1. MVS 输出的 dense.ply 可能含有飞点、背景点、错误深度点和孤立小簇。
2. 如果直接 Mesh，会放大点云噪声，导致尖刺、破面、飞面。
3. 因此 V3 引入 dense_cleaned.ply 作为 Mesh 前置门控。
4. 点云清理包括统计离群点去除、半径离群点去除、DBSCAN 主体簇保留、体素下采样、可视化质量检查等。
5. 清理前后应输出 before/after 投影图和 cleaning_report。
```

V3 outputs should include:

```text
results/mesh/dense_cleaned.ply
results/mesh/cleaning_report.txt
results/mesh/pointcloud_before_after.png
```

---

## V4 Required Explanation

V4 should explain the motivation for using COLMAP.

Must include:

```text
1. 自研 SfM/MVS 有助于理解底层原理，但工程效果受限。
2. 当前目标转为追求重建效果，因此引入 COLMAP 成熟工具链。
3. COLMAP 提供完整的 SfM、Bundle Adjustment、PatchMatch MVS、深度融合和 Mesh 重建流程。
4. V4 的目标是生成更可靠的 fused.ply、mesh.ply 和 model.glb。
5. V4 可以作为最终展示路线，也可以作为自研 pipeline 的 baseline 对照。
```

V4 outputs should include:

```text
results/colmap/sparse/
results/colmap/dense/fused.ply
results/colmap/dense/meshed-poisson.ply
results/colmap/dense/meshed-delaunay.ply
results/colmap/model.glb
results/colmap/reconstruction_report.md
```

---

# Section 4: 环境与包管理

## Required Content

This section should describe the environment management method.

Must include:

```text
1. 本工程使用 Miniconda 管理 Python 环境。
2. 环境名必须为 3D_Reconstruction。
3. 所有 Python 包应安装在该环境下。
4. 运行工程前需要先激活该环境。
5. 不要随意新建其他环境。
6. 如果需要新增依赖，应记录在 README 或 requirements/environment 文件中。
```

## Required Commands

Include these commands:

```bash
conda activate 3D_Reconstruction
```

If the environment needs to be created, include:

```bash
conda create -n 3D_Reconstruction python=3.10 -y
conda activate 3D_Reconstruction
```

For package installation, include a section such as:

```bash
pip install numpy scipy opencv-python open3d pyyaml pillow matplotlib trimesh pygltflib
```

If COLMAP is used, explain that COLMAP may be installed as a system-level command-line tool, and the agent should check availability with:

```bash
colmap -h
```

If COLMAP is not installed, the README should not invent a successful installation. It should state that COLMAP needs to be installed separately according to the operating system.

## Required Notes

Mention:

```text
1. Python package dependencies are managed inside 3D_Reconstruction.
2. COLMAP is an external command-line reconstruction tool and may not be installed by pip.
3. All scripts should be run from the project root.
4. config.yaml stores shared parameters and paths.
```

---

# Section 5: 总结

This section should be included but left empty or only contain a placeholder.

Use:

```markdown
# 5. 总结

TODO: 由用户补充。
```

Do not write a long summary in this section.

---

# Additional Writing Requirements

## Language

The README should be written mainly in Chinese.

Technical terms can include English names, for example:

```text
增量式 SfM（Incremental Structure-from-Motion）
多视角立体重建（Multi-View Stereo, MVS）
泊松表面重建（Poisson Surface Reconstruction）
```

## Style

The README should be:

```text
1. 清晰
2. 工程化
3. 结构化
4. 适合给后来接手项目的人阅读
5. 不要写成论文，不要过度展开数学推导
```

## Must Read Before Writing

Before writing the README, the agent must read:

```text
1. 当前工程文件结构
2. task V1 / V2 / V3 / V4 任务文件
3. agent_message/agentwork_record/ 中已有的 agent record
4. config.yaml
```

If some files do not exist, the agent should mention this in its own work record, but should still write the README based on available project information.

## Output

The final output must be:

```text
README.md
```

The agent should also record its work in the required agent record / communication file according to the project protocol.
