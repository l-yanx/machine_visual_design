# AGENT_WORK_PROTOCOL.md

# Multi-Agent Work Protocol for V1 Traditional 3D Reconstruction

## 1. Purpose

This protocol defines how agents collaborate on the V1 traditional multi-view 3D reconstruction project.

The V1 project contains two main technical tasks:

```text
Task 1: Incremental SfM
Task 2: ZNCC-based MVS and dense PLY generation
```

The agent workflow contains:

```text
Core Agent: project organization, task dispatching, code review, integration, and acceptance
Subagent 1: implementation of Task 1, Incremental SfM
Subagent 2: implementation of Task 2, ZNCC-based MVS
```

All agents must follow this protocol when writing code, running tests, recording results, and handing work over to the next agent.

---

# 2. Global Project Directory Convention

The project root is assumed to be:

```text
./
```

Input image data must be stored in:

```text
./data/image/
```

The recommended full project structure is:

```text
./
├── data/
│   └── image/
│       ├── 0001.jpg
│       ├── 0002.jpg
│       ├── 0003.jpg
│       └── ...
│
├── sfm/
│   ├── image_preprocess.py
│   ├── feature_extractor.py
│   ├── feature_matcher.py
│   ├── geometric_verification.py
│   ├── initialization.py
│   ├── triangulation.py
│   ├── pnp_registration.py
│   ├── incremental_sfm.py
│   ├── export_sparse.py
│   └── utils.py
│
├── mvs/
│   ├── read_sfm.py
│   ├── view_selection.py
│   ├── depth_range.py
│   ├── zncc.py
│   ├── plane_sweep.py
│   ├── depth_filter.py
│   ├── depth_to_pointcloud.py
│   ├── pointcloud_fusion.py
│   └── export_dense.py
│
├── visualization/
│   ├── visualize_matches.py
│   ├── visualize_cameras.py
│   ├── visualize_sparse.py
│   └── visualize_depth.py
│
├── results/
│   ├── features/
│   ├── matches/
│   ├── matches_verified/
│   ├── sparse/
│   ├── dense/
│   ├── visualization/
│   └── logs/
│
├── agent_message/
│   └── agentwork_record/
│       ├── core_agent_record.md
│       ├── subagent1_record.md
│       ├── subagent2_record.md
│       └── handover_summary.md
│
├── main_sfm.py
├── main_mvs.py
├── config.yaml
├── V1_TASK.md
├── AGENT_WORK_PROTOCOL.md
└── README.md
```

If any directory does not exist, the responsible agent must create it before writing files.

---

# 3. Agent Roles

## 3.1 Core Agent

The Core Agent is responsible for project-level coordination.

Main responsibilities:

```text
1. Read V1_TASK.md and AGENT_WORK_PROTOCOL.md.
2. Understand the complete V1 pipeline.
3. Organize the project directory structure.
4. Create or update config.yaml.
5. Dispatch Task 1 to Subagent 1.
6. Dispatch Task 2 to Subagent 2 after Task 1 outputs are available.
7. Review code written by each subagent.
8. Run or request execution of tests.
9. Verify whether outputs satisfy acceptance criteria.
10. Check whether each agent has written its work record.
11. Integrate final outputs.
12. Write final handover_summary.md.
```

The Core Agent should not directly implement large task-specific modules unless necessary for integration or bug fixing.

The Core Agent may write:

```text
1. Project-level scripts
2. Configuration files
3. Integration scripts
4. Test scripts
5. Bug-fix patches
6. Documentation
```

---

## 3.2 Subagent 1

Subagent 1 is responsible for Task 1: Incremental SfM.

Main responsibilities:

```text
1. Read V1_TASK.md.
2. Read AGENT_WORK_PROTOCOL.md.
3. Implement the Incremental SfM pipeline.
4. Use images from ./data/image/.
5. Write Task 1 outputs to ./results/sparse/ and related folders.
6. Generate feature, matching, RANSAC, pose, track, and sparse point cloud results.
7. Run available tests or scripts.
8. Record work content and execution results in Chinese.
9. Record handover information for Subagent 2 in English.
```

Subagent 1 must produce at least:

```text
./results/sparse/sparse.ply
./results/sparse/camera_poses.txt
./results/sparse/cameras.json
./results/sparse/points3D.json
./results/sparse/tracks.json
./results/logs/sfm_log.txt
```

Subagent 1 must write its work record to:

```text
./agent_message/agentwork_record/subagent1_record.md
```

---

## 3.3 Subagent 2

Subagent 2 is responsible for Task 2: ZNCC-based MVS and dense PLY generation.

Main responsibilities:

```text
1. Read V1_TASK.md.
2. Read AGENT_WORK_PROTOCOL.md.
3. Read Subagent 1 handover information.
4. Use Task 1 exported files only, not Subagent 1 internal variables.
5. Implement ZNCC-based MVS.
6. Generate depth maps, confidence maps, partial point clouds, and dense.ply.
7. Run available tests or scripts.
8. Record work content and execution results in Chinese.
9. Record handover information for Core Agent in English.
```

Subagent 2 must produce at least:

```text
./results/dense/dense.ply
./results/dense/depth_maps/
./results/dense/confidence_maps/
./results/dense/depth_maps_filtered/
./results/dense/partial_pointclouds/
./results/logs/mvs_log.txt
```

Subagent 2 must write its work record to:

```text
./agent_message/agentwork_record/subagent2_record.md
```

---

# 4. Execution Order

The required execution order is:

```text
Step 1: Core Agent initializes project structure.
Step 2: Core Agent checks whether ./data/image/ contains valid images.
Step 3: Core Agent dispatches Task 1 to Subagent 1.
Step 4: Subagent 1 implements and runs Incremental SfM.
Step 5: Subagent 1 writes subagent1_record.md.
Step 6: Core Agent reviews Task 1 code and outputs.
Step 7: Core Agent either accepts Task 1 or requests fixes.
Step 8: Core Agent dispatches Task 2 to Subagent 2.
Step 9: Subagent 2 implements and runs ZNCC-based MVS.
Step 10: Subagent 2 writes subagent2_record.md.
Step 11: Core Agent reviews Task 2 code and outputs.
Step 12: Core Agent either accepts Task 2 or requests fixes.
Step 13: Core Agent writes final handover_summary.md.
```

Subagent 2 must not start final MVS execution until Task 1 outputs are available.

---

# 5. Agent Work Record Requirements

Every agent must write a work record after completing its work.

All work records must be saved under:

```text
./agent_message/agentwork_record/
```

Each work record must include three sections:

```text
1. 工作内容记录（中文）
2. 程序执行结果（中文）
3. Handover to Next Agent（English）
```

---

## 5.1 Work Record Template

Each agent must use the following template.

```markdown
# Agent Work Record

## Agent Name

Core Agent / Subagent 1 / Subagent 2

## Task Name

Write the task name here.

---

## 1. 工作内容记录（中文）

说明本 agent 本轮完成了哪些工作，包括：

- 修改或新增了哪些文件
- 实现了哪些模块
- 使用了哪些输入数据
- 输出了哪些结果文件
- 当前任务完成到什么程度

---

## 2. 程序执行结果（中文）

记录程序运行情况，包括：

- 执行了哪些命令
- 是否成功运行
- 生成了哪些输出文件
- 关键指标或日志结果
- 出现了哪些报错
- 如果有报错，如何处理或当前是否未解决

示例：

```text
执行命令：python main_sfm.py --config config.yaml
执行结果：成功 / 失败
输出文件：results/sparse/sparse.ply
关键结果：成功注册 18/25 张图像，平均重投影误差 4.2 px
```

---

## 3. Handover to Next Agent（English）

Write handover information for the next agent in English.

This section must include:

- What files are ready for the next agent
- Where the files are stored
- What file formats are used
- What assumptions were made
- What known issues remain
- What the next agent should pay attention to

Example:

```text
The SfM outputs are ready for the MVS stage.
Camera poses are stored in ./results/sparse/camera_poses.txt.
Camera intrinsics are stored in ./results/sparse/cameras.json.
Sparse 3D points are stored in ./results/sparse/points3D.json.
The sparse point cloud is stored in ./results/sparse/sparse.ply.
Subagent 2 should use only the exported files and should not rely on internal variables from Task 1.
Known issue: the current reconstruction scale is arbitrary because no real-world scale reference is provided.
```
```

---

# 6. Required Work Record Files

## 6.1 Core Agent Record

Path:

```text
./agent_message/agentwork_record/core_agent_record.md
```

The Core Agent record should include:

```text
1. Project initialization details
2. Created directory structure
3. Config file status
4. Task dispatching status
5. Code review results
6. Acceptance results
7. Final integration status
```

---

## 6.2 Subagent 1 Record

Path:

```text
./agent_message/agentwork_record/subagent1_record.md
```

Subagent 1 record must include:

```text
1. SfM modules implemented
2. Input image path
3. Feature extraction result
4. Matching result
5. RANSAC verification result
6. Registered image count
7. Sparse point count
8. Reprojection error if available
9. Exported SfM files
10. Handover information for Subagent 2 in English
```

---

## 6.3 Subagent 2 Record

Path:

```text
./agent_message/agentwork_record/subagent2_record.md
```

Subagent 2 record must include:

```text
1. MVS modules implemented
2. SfM files read from Task 1
3. Selected reference/source views
4. Depth range estimation result
5. Depth map generation result
6. Confidence map generation result
7. Partial point cloud generation result
8. Dense point cloud fusion result
9. dense.ply output status
10. Handover information for Core Agent in English
```

---

## 6.4 Final Handover Summary

Path:

```text
./agent_message/agentwork_record/handover_summary.md
```

The Core Agent must write this file after reviewing all tasks.

It should include:

```text
1. Whether Task 1 passed acceptance
2. Whether Task 2 passed acceptance
3. Final output file locations
4. Known limitations
5. Suggested V2 improvements
```

---

# 7. Code Writing Rules

All agents must follow these coding rules.

```text
1. Use clear module boundaries.
2. Do not write all code into one large script.
3. Use config.yaml for key parameters.
4. Avoid hard-coded absolute paths.
5. Use relative paths based on the project root.
6. All input images must be read from ./data/image/ unless otherwise configured.
7. All generated results must be written to ./results/.
8. All logs must be written to ./results/logs/.
9. All agent communication records must be written to ./agent_message/agentwork_record/.
10. Each main script should be runnable from the project root.
```

Recommended command format:

```bash
python main_sfm.py --config config.yaml
python main_mvs.py --config config.yaml
```

---

# 8. Configuration Rules

The project should use a shared config file:

```text
./config.yaml
```

Recommended content:

```yaml
paths:
  image_dir: ./data/image
  results_dir: ./results
  agent_record_dir: ./agent_message/agentwork_record

image:
  resize_width: 1000

camera:
  use_calibrated_intrinsics: false
  fx_scale: 1.2

sift:
  max_features: 4000

matching:
  strategy: sequential
  neighbor_range: 3
  ratio_threshold: 0.75

ransac:
  essential_threshold: 1.0
  confidence: 0.999
  min_inliers: 50

sfm:
  reprojection_error_threshold: 5.0
  pnp_min_inliers: 30
  triangulation_min_angle: 1.0

mvs:
  source_view_num: 3
  depth_samples: 64
  patch_size: 5
  stride: 2
  zncc_threshold: 0.5
  depth_percentile_min: 5
  depth_percentile_max: 95

fusion:
  voxel_size: 0.02
  outlier_nb_neighbors: 20
  outlier_std_ratio: 2.0
```

Agents may modify parameters, but they must record changes in their work record.

---

# 9. Acceptance and Review Rules

## 9.1 Core Agent Review Requirements

The Core Agent must review each task using the acceptance criteria in V1_TASK.md.

For Task 1, the Core Agent must check:

```text
1. Whether required SfM output files exist
2. Whether sparse.ply can be opened
3. Whether camera_poses.txt is valid
4. Whether cameras.json is valid
5. Whether points3D.json and tracks.json exist
6. Whether enough images are registered
7. Whether sparse point cloud is visually reasonable
8. Whether subagent1_record.md is complete
```

For Task 2, the Core Agent must check:

```text
1. Whether required MVS output files exist
2. Whether Task 2 reads only exported Task 1 files
3. Whether depth maps are generated
4. Whether confidence maps are generated
5. Whether partial point clouds are generated
6. Whether dense.ply can be opened
7. Whether dense.ply has more points than sparse.ply
8. Whether dense point cloud is visually reasonable
9. Whether subagent2_record.md is complete
```

---

## 9.2 Failed Acceptance Handling

If a task fails acceptance, the Core Agent must:

```text
1. Identify the failed acceptance item.
2. Write the issue clearly in core_agent_record.md.
3. Return the task to the responsible subagent for correction.
4. Require the subagent to update its work record after correction.
```

A task should not be marked as accepted if required output files are missing.

---

# 10. Logging Rules

All agents must write runtime logs.

Required log paths:

```text
./results/logs/sfm_log.txt
./results/logs/mvs_log.txt
./results/logs/core_review_log.txt
```

Logs should include:

```text
1. Runtime command
2. Start and end time if available
3. Input path
4. Output path
5. Key parameter values
6. Key metrics
7. Warnings
8. Errors
```

---

# 11. Error Handling Rules

When an error occurs, the responsible agent must:

```text
1. Record the exact error message.
2. Record which command caused the error.
3. Record which file or module is involved.
4. Try to provide a clear fix or workaround.
5. If unresolved, clearly state it in the work record.
```

Do not silently ignore failed commands.

Do not claim a task is complete if the main output file was not generated.

---

# 12. Data and File Interface Rules

Subagents must communicate through files, not hidden variables.

Task 1 must provide these files to Task 2:

```text
./results/sparse/sparse.ply
./results/sparse/camera_poses.txt
./results/sparse/cameras.json
./results/sparse/points3D.json
./results/sparse/tracks.json
```

Task 2 must read these files directly.

Task 2 must not rely on temporary Python objects, internal variables, or memory states from Task 1.

---

# 13. Suggested Additional Checks

The following checks are recommended before final acceptance.

```text
1. Check that image filenames are consistently ordered.
2. Check that all paths in config.yaml are relative paths.
3. Check that no absolute local machine path is hard-coded.
4. Check that generated PLY files are not empty.
5. Check that sparse.ply and dense.ply use the same world coordinate system.
6. Check that dense.ply has more points than sparse.ply.
7. Check that the project can be rerun from a clean results directory.
8. Check that each agent record is updated after its final code version.
```

---

# 14. V1 Completion Definition

V1 is complete only when:

```text
1. Task 1 passes Core Agent review.
2. Task 2 passes Core Agent review.
3. All required output files exist.
4. sparse.ply and dense.ply can be opened.
5. All required agent work records exist.
6. Core Agent has written handover_summary.md.
```

Final required outputs:

```text
./results/sparse/sparse.ply
./results/sparse/camera_poses.txt
./results/sparse/cameras.json
./results/sparse/points3D.json
./results/sparse/tracks.json
./results/dense/dense.ply
./results/dense/depth_maps/
./results/dense/confidence_maps/
./results/logs/sfm_log.txt
./results/logs/mvs_log.txt
./agent_message/agentwork_record/core_agent_record.md
./agent_message/agentwork_record/subagent1_record.md
./agent_message/agentwork_record/subagent2_record.md
./agent_message/agentwork_record/handover_summary.md
```

---

# 15. Known V1 Limitations

The following limitations are acceptable in V1:

```text
1. No mesh reconstruction.
2. No texture mapping.
3. No Three.js frontend.
4. No full Bundle Adjustment.
5. Arbitrary reconstruction scale if no real-world scale reference is provided.
6. Sparse or noisy dense point cloud is acceptable if the main sculpture structure is visible.
7. MVS may be slow because ZNCC plane sweeping is computationally expensive.
```

These limitations should be considered for V2 improvements.
