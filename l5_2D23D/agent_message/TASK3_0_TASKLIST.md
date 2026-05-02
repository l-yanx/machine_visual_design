# TASK3_0_TASKLIST.md

# Task 3.0 — Dense Point Cloud Quality Check & Cleaning

## 0. Global Requirement

All agents must use the existing Miniconda environment from V1/V2:

```bash
source /home/lyx/miniconda3/etc/profile.d/conda.sh
conda activate 3D_Reconstruction
```

Do not create a new Conda environment unless the Core Agent explicitly decides that the existing environment is broken.

All package installation, script execution, testing, and debugging must be done inside:

```text
3D_Reconstruction
```

---

# 1. Agent Naming and Scope

## Core Agent Name

```text
Core Agent V2-Task3.0
```

## Subagent Name

```text
Subagent 5 V2-Task3.0
```

Task 3.0 is a continuation of the previous V1/V2 reconstruction project.  
The goal is not to directly generate mesh first. The goal is to clean and validate the dense point cloud before any mesh reconstruction.

---

# 2. Mandatory Pre-Work

Before writing or modifying code, the agents must read:

```text
agent_message/agentwork_record/core_agent_record.md
agent_message/agentwork_record/subagent1_record.md
agent_message/agentwork_record/subagent2_record.md
agent_message/agentwork_record/handover_summary.md
```

The agents must also inspect the full project structure and relevant code files, including but not limited to:

```text
config.yaml
main_sfm.py
main_mvs.py
sfm/
mvs/
results/sparse/
results/dense/
results/mesh/          # create if missing
visualization/
agent_message/
```

The agents must understand:

```text
1. How Task 1 generated sparse.ply and cameras.json
2. How Task 2 generated dense.ply
3. Existing file paths and naming conventions
4. Existing config.yaml format
5. Existing logging style
6. Existing point cloud output format
```

The subagent must not assume access to internal variables from previous tasks.  
It must only read exported files and existing project files.

---

# 3. Task 3.0 Main Goal

Implement a dense point cloud quality checking and cleaning module.

## Input

```text
results/dense/dense.ply
```

Optional inputs:

```text
results/sparse/sparse.ply
results/sparse/cameras.json
results/dense/depth_maps/
results/dense/confidence_maps/
data/images_resized/
config.yaml
```

## Required Output

```text
results/mesh/dense_cleaned.ply
results/mesh/cleaning_report.txt
results/mesh/pointcloud_before_after.png
results/logs/task3_0_cleaning_log.txt
```

Optional intermediate outputs:

```text
results/mesh/dense_valid_only.ply
results/mesh/dense_statistical_cleaned.ply
results/mesh/dense_radius_cleaned.ply
results/mesh/dense_dbscan_cleaned.ply
results/mesh/dense_voxel_downsampled.ply
results/mesh/dense_with_normals.ply
```

---

# 4. File Structure to Add

Subagent 5 should create the following files if they do not already exist:

```text
mesh/
├── pointcloud_io.py
├── pointcloud_quality.py
├── pointcloud_filter.py
├── pointcloud_cluster.py
├── pointcloud_visualize.py
├── export_cleaned.py
└── utils.py

main_clean_pointcloud.py
```

The implementation should follow the existing project style:

```text
1. Use config.yaml for parameters when possible
2. Use relative paths
3. Write logs into results/logs/
4. Write cleaned outputs into results/mesh/
5. Do not overwrite V1/V2 records
```

---

# 5. Task List

Each task below corresponds to one function or one clearly separated module-level capability.

---

## Task 3.0.1 — Read Previous Records and Inspect Project

### Responsible Agent

```text
Core Agent V2-Task3.0
Subagent 5 V2-Task3.0
```

### Function / Capability

Read previous agent records and inspect the current project structure.

### Required Actions

```text
1. Read all previous agent work records
2. Inspect config.yaml
3. Inspect main_sfm.py and main_mvs.py
4. Inspect sfm/ and mvs/ modules
5. Inspect results/dense/dense.ply
6. Confirm whether results/mesh/ exists
7. Confirm whether results/logs/ exists
```

### Output

```text
agent_message/agentwork_record/subagent5_v2_task3_0_record.md
```

The record must include a short summary of what was found.

### Acceptance Criteria

```text
1. Subagent confirms the dense.ply path exists
2. Subagent confirms the current Conda environment is 3D_Reconstruction
3. Subagent confirms previous records were read
4. Subagent confirms project structure before coding
```

---

## Task 3.0.2 — Add Task 3.0 Configuration

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Add or verify cleaning-related parameters in `config.yaml`.

### Suggested Config Section

```yaml
cleaning:
  input_dense_ply: "results/dense/dense.ply"
  output_dir: "results/mesh"
  output_cleaned_ply: "results/mesh/dense_cleaned.ply"

  remove_nan_inf: true
  remove_duplicate_points: true

  use_color_filter: false
  color_filter_mode: "yellow_background"
  brightness_min: 0
  brightness_max: 255

  statistical_outlier:
    enabled: true
    nb_neighbors: 30
    std_ratio: 1.5

  radius_outlier:
    enabled: true
    radius_scale: 2.5
    min_neighbors: 8

  dbscan:
    enabled: true
    eps_scale: 2.5
    min_points: 20
    keep_largest_k: 1

  voxel_downsample:
    enabled: true
    voxel_size: 0.02

  normal_estimation:
    enabled: true
    radius_scale: 3.0
    max_nn: 30
    orient_normals: true

  visualization:
    enabled: true
    output_projection_png: "results/mesh/pointcloud_before_after.png"
```

### Output

```text
config.yaml
```

### Acceptance Criteria

```text
1. config.yaml contains a cleaning section
2. Existing V1/V2 config parameters are not removed
3. Cleaning script can read these parameters
```

---

## Task 3.0.3 — Point Cloud Loading and Basic Validation

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Load `results/dense/dense.ply` and validate that it is usable.

### Suggested Function

```python
load_point_cloud(path: str) -> open3d.geometry.PointCloud
```

### Required Checks

```text
1. File exists
2. File can be read by Open3D
3. Point count > 0
4. Points array shape is valid
5. Colors exist or are handled if missing
6. NaN / inf count is reported
```

### Output

```text
results/logs/task3_0_cleaning_log.txt
results/mesh/cleaning_report.txt
```

### Acceptance Criteria

```text
1. dense.ply is loaded successfully
2. Point count is written to the report
3. Bounding box is written to the report
4. Color availability is written to the report
```

---

## Task 3.0.4 — Basic Point Cloud Statistics

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Compute and report point cloud statistics.

### Suggested Function

```python
compute_point_cloud_stats(pcd) -> dict
```

### Required Statistics

```text
1. Number of points
2. Axis-aligned bounding box min/max
3. Bounding box extent
4. Centroid
5. Distance-to-centroid mean/std/min/max
6. Color mean/std/min/max if colors exist
7. Approximate nearest-neighbor distance statistics
```

### Output

```text
results/mesh/cleaning_report.txt
```

### Acceptance Criteria

```text
1. Report includes all required statistics
2. Report clearly distinguishes before-cleaning and after-cleaning statistics
```

---

## Task 3.0.5 — Remove Invalid and Duplicate Points

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Remove invalid points before advanced filtering.

### Suggested Function

```python
remove_invalid_points(pcd) -> open3d.geometry.PointCloud
```

### Required Processing

```text
1. Remove NaN points
2. Remove inf points
3. Remove duplicate points if possible
4. Preserve point colors
```

### Output

```text
results/mesh/dense_valid_only.ply
```

### Acceptance Criteria

```text
1. Output point cloud can be opened
2. No NaN or inf points remain
3. Point count before and after is recorded
```

---

## Task 3.0.6 — Statistical Outlier Removal

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Remove points with abnormal local neighborhood distance.

### Suggested Function

```python
apply_statistical_outlier_removal(
    pcd,
    nb_neighbors: int,
    std_ratio: float
) -> open3d.geometry.PointCloud
```

### Input

```text
results/mesh/dense_valid_only.ply
```

### Output

```text
results/mesh/dense_statistical_cleaned.ply
```

### Acceptance Criteria

```text
1. Statistical filtering runs successfully
2. Output point count is > 0
3. Removed point count is written to cleaning_report.txt
4. Output point cloud can be opened
```

---

## Task 3.0.7 — Radius Outlier Removal

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Remove isolated local points using radius-neighbor filtering.

### Suggested Function

```python
apply_radius_outlier_removal(
    pcd,
    radius: float,
    min_neighbors: int
) -> open3d.geometry.PointCloud
```

### Radius Selection

If radius is not explicitly configured, estimate it from nearest-neighbor distances:

```text
radius = median_nn_distance * radius_scale
```

### Input

```text
results/mesh/dense_statistical_cleaned.ply
```

### Output

```text
results/mesh/dense_radius_cleaned.ply
```

### Acceptance Criteria

```text
1. Radius filtering runs successfully
2. Radius value is recorded in cleaning_report.txt
3. Output point count is > 0
4. Output point cloud can be opened
```

---

## Task 3.0.8 — DBSCAN Main Cluster Extraction

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Use DBSCAN to retain the main object cluster and remove isolated background clusters.

### Suggested Function

```python
extract_main_cluster_dbscan(
    pcd,
    eps: float,
    min_points: int,
    keep_largest_k: int
) -> open3d.geometry.PointCloud
```

### EPS Selection

If eps is not explicitly configured, estimate it from nearest-neighbor distances:

```text
eps = median_nn_distance * eps_scale
```

### Input

```text
results/mesh/dense_radius_cleaned.ply
```

### Output

```text
results/mesh/dense_dbscan_cleaned.ply
```

### Acceptance Criteria

```text
1. DBSCAN runs successfully
2. Number of clusters is recorded
3. Largest cluster size is recorded
4. Kept cluster count is recorded
5. Output point count is > 0
6. Output point cloud can be opened
```

---

## Task 3.0.9 — Optional Color-Based Background Filtering

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Optionally remove background points based on color distribution.

### Suggested Function

```python
apply_color_filter(pcd, mode: str, params: dict) -> open3d.geometry.PointCloud
```

### Notes

This step should be optional and controlled by config:

```yaml
cleaning:
  use_color_filter: true
```

Example use case:

```text
Remove yellow desk mat background points.
```

### Output

```text
results/mesh/dense_color_filtered.ply
```

### Acceptance Criteria

```text
1. If disabled, the pipeline skips this step cleanly
2. If enabled, removed point count is reported
3. Output point cloud can be opened
4. The step must not delete all points
```

---

## Task 3.0.10 — Voxel Downsampling

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Downsample the cleaned point cloud to make density more uniform and prepare for normal estimation.

### Suggested Function

```python
apply_voxel_downsample(pcd, voxel_size: float) -> open3d.geometry.PointCloud
```

### Input

```text
Best cleaned point cloud from previous steps
```

### Output

```text
results/mesh/dense_voxel_downsampled.ply
```

### Acceptance Criteria

```text
1. Downsampling runs successfully
2. Voxel size is recorded
3. Output point count is > 0
4. Output point cloud can be opened
```

---

## Task 3.0.11 — Normal Estimation for Mesh Preparation

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Estimate point normals for the cleaned point cloud.

### Suggested Function

```python
estimate_and_orient_normals(
    pcd,
    radius: float,
    max_nn: int
) -> open3d.geometry.PointCloud
```

### Radius Selection

If radius is not explicitly configured:

```text
normal_radius = median_nn_distance * normal_radius_scale
```

### Output

```text
results/mesh/dense_with_normals.ply
results/mesh/dense_cleaned.ply
```

### Acceptance Criteria

```text
1. Normals are estimated successfully
2. Output point cloud has normals
3. dense_cleaned.ply is exported
4. dense_cleaned.ply can be opened
```

---

## Task 3.0.12 — Before/After Visualization

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Generate visual comparison between original dense point cloud and cleaned point cloud.

### Suggested Function

```python
save_before_after_projection(
    dense_ply_path: str,
    cleaned_ply_path: str,
    output_png: str
)
```

### Required Views

The visualization should include at least:

```text
1. XY projection
2. XZ projection
3. YZ projection
```

Recommended layout:

```text
Left: before cleaning
Right: after cleaning
```

### Output

```text
results/mesh/pointcloud_before_after.png
```

### Acceptance Criteria

```text
1. PNG file is generated
2. It visually compares before and after point clouds
3. It is referenced in cleaning_report.txt
```

---

## Task 3.0.13 — Cleaning Report Generation

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Generate a complete cleaning report in Chinese.

### Suggested Function

```python
write_cleaning_report(report_data: dict, output_path: str)
```

### Required Report Content

```text
1. Input file path
2. Output file path
3. Conda environment used
4. Original point count
5. Point count after each cleaning step
6. Removed point count and percentage for each step
7. Bounding box before and after
8. Nearest-neighbor distance statistics
9. DBSCAN cluster count and kept cluster size
10. Voxel size
11. Normal estimation parameters
12. Whether color filtering was enabled
13. Known limitations
14. Recommendation: whether the cleaned point cloud is suitable for mesh reconstruction
```

### Output

```text
results/mesh/cleaning_report.txt
```

### Acceptance Criteria

```text
1. Report is written in Chinese
2. Report includes all required content
3. Report clearly states whether mesh reconstruction is recommended
```

---

## Task 3.0.14 — Main Script Integration

### Responsible Agent

```text
Subagent 5 V2-Task3.0
```

### Function / Capability

Create a single runnable script for Task 3.0.

### Script

```text
main_clean_pointcloud.py
```

### Required Command

```bash
source /home/lyx/miniconda3/etc/profile.d/conda.sh && conda activate 3D_Reconstruction
python main_clean_pointcloud.py --config config.yaml
```

### Required Behavior

```text
1. Read config.yaml
2. Load results/dense/dense.ply
3. Run all enabled cleaning steps
4. Export intermediate outputs
5. Export dense_cleaned.ply
6. Export pointcloud_before_after.png
7. Export cleaning_report.txt
8. Write task3_0_cleaning_log.txt
```

### Acceptance Criteria

```text
1. Script runs from project root
2. Script completes without errors
3. All required outputs are generated
```

---

## Task 3.0.15 — Core Agent Code Review and Acceptance

### Responsible Agent

```text
Core Agent V2-Task3.0
```

### Function / Capability

Review Subagent 5 code and validate outputs.

### Required Checks

```text
1. Verify all required files exist
2. Verify dense_cleaned.ply opens with Open3D
3. Verify dense_cleaned.ply point count > 0
4. Verify cleaning_report.txt exists and is in Chinese
5. Verify pointcloud_before_after.png exists
6. Verify logs exist
7. Inspect whether the cleaned point cloud is more suitable for mesh than dense.ply
8. Decide whether Task 3.1 Mesh Reconstruction can start
```

### Output

```text
agent_message/agentwork_record/core_agent_v2_task3_0_record.md
```

### Acceptance Criteria

```text
1. Core Agent writes acceptance result
2. Core Agent records pass/fail status
3. If failed, Core Agent lists required fixes
4. If passed, Core Agent hands over to Task 3.1
```

---

# 6. Agent Work Record Requirement

Every agent must write a work record after finishing its part.

## Subagent 5 Record

```text
agent_message/agentwork_record/subagent5_v2_task3_0_record.md
```

Required sections:

```markdown
# Agent Work Record

## Agent Name

Subagent 5 V2-Task3.0

## Task Name

Task 3.0: Dense Point Cloud Quality Check & Cleaning

---

## 1. 工作内容记录（中文）

Describe implemented modules, modified files, and output files.

---

## 2. 程序执行结果（中文）

Include commands, runtime result, point counts, filtering statistics, and generated output files.

---

## 3. Handover to Next Agent（English）

Explain what files are ready for the next agent, where they are located, and whether mesh reconstruction is recommended.
```

## Core Agent Record

```text
agent_message/agentwork_record/core_agent_v2_task3_0_record.md
```

Required sections:

```markdown
# Agent Work Record

## Agent Name

Core Agent V2-Task3.0

## Task Name

Task 3.0 Coordination, Code Review, and Acceptance

---

## 1. 工作内容记录（中文）

Describe project inspection, review process, and validation.

---

## 2. 程序执行结果（中文）

Summarize command execution and output validation.

---

## 3. Handover to Next Agent（English）

State whether Task 3.1 Mesh Reconstruction can start and list required input files.
```

---

# 7. Final Task 3.0 Acceptance Criteria

Task 3.0 is complete only if all of the following are satisfied:

```text
1. Previous V1/V2 agent records were read.
2. Full project structure was inspected.
3. Existing Conda environment 3D_Reconstruction was used.
4. main_clean_pointcloud.py runs from the project root.
5. results/dense/dense.ply is loaded successfully.
6. results/mesh/dense_cleaned.ply is generated.
7. dense_cleaned.ply can be opened by Open3D.
8. dense_cleaned.ply has more than 0 points.
9. cleaning_report.txt is generated in Chinese.
10. pointcloud_before_after.png is generated.
11. task3_0_cleaning_log.txt is generated.
12. Subagent work record is generated.
13. Core Agent work record is generated.
14. Core Agent explicitly decides whether Task 3.1 Mesh Reconstruction can start.
```

---

# 8. Do Not Do in Task 3.0

Task 3.0 must not perform the following:

```text
1. Do not generate mesh.
2. Do not generate GLB.
3. Do not implement Three.js frontend.
4. Do not rerun SfM.
5. Do not rerun MVS.
6. Do not overwrite sparse.ply or dense.ply.
7. Do not delete previous V1/V2 outputs.
8. Do not create a new Conda environment.
```

Task 3.0 only cleans and validates the dense point cloud.

---

# 9. Handover to Task 3.1

If Task 3.0 passes, the next task should use:

```text
results/mesh/dense_cleaned.ply
```

as the only point cloud input for mesh reconstruction.

Task 3.1 should not use:

```text
results/dense/dense.ply
```

directly unless Core Agent explicitly rejects `dense_cleaned.ply`.

Potential next task:

```text
Task 3.1: Mesh Reconstruction from dense_cleaned.ply
```

Expected next outputs:

```text
results/mesh/mesh_poisson.ply
results/mesh/mesh_ball_pivoting.ply
results/mesh/mesh_cleaned.ply
results/mesh/model.glb
```
