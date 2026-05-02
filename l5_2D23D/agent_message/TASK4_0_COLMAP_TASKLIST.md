# TASK4_0_COLMAP_TASKLIST.md

# Task 4.0: COLMAP Reconstruction Pipeline

## 0. Task Purpose

This task replaces the current self-written SfM/MVS reconstruction pipeline with a mature COLMAP-based reconstruction pipeline, prioritizing final reconstruction quality and usable visualization results.

The goal is to use COLMAP to generate:

```text
1. Sparse reconstruction
2. Dense point cloud
3. Mesh reconstruction
4. GLB model for Three.js visualization
5. Reconstruction report
```

This task keeps the previous custom SfM/MVS pipeline as a reference, but the final effect-oriented reconstruction should be based on COLMAP outputs.

---

# 1. Global Requirements

## 1.1 Conda Environment

All Python scripts, conversion scripts, report scripts, and validation scripts must run inside the existing Miniconda environment:

```bash
conda activate 3D_Reconstruction
```

Do not create a new Conda environment unless explicitly approved by the user or Core Agent.

If additional Python packages are required, install them inside:

```text
3D_Reconstruction
```

Example acceptable Python packages:

```text
numpy
open3d
trimesh
pygltflib
matplotlib
pillow
pyyaml
```

## 1.2 COLMAP Dependency

This task assumes the `colmap` command is available in the system path.

Before running reconstruction, the responsible agent must check:

```bash
colmap -h
```

If COLMAP is not installed, the agent must not use `sudo` or modify system packages without permission. The agent should record the issue in `communication.md` and ask Core Agent for installation handling.

## 1.3 Input Image Directory

Input images must be read from:

```text
./data/image/
```

Expected format:

```text
./data/image/
├── 001.jpg
├── 002.jpg
├── 003.jpg
└── ...
```

The task should not use previous resized images unless explicitly configured.

## 1.4 Output Root Directory

All COLMAP-related outputs must be written to:

```text
./results/colmap/
```

Required final outputs:

```text
./results/colmap/database.db
./results/colmap/sparse/
./results/colmap/dense/fused.ply
./results/colmap/dense/meshed-poisson.ply
./results/colmap/dense/meshed-delaunay.ply
./results/colmap/model/model.glb
./results/colmap/report/reconstruction_report.md
```

## 1.5 Agent Record and Communication Rules

Each Subagent must write its work record in Chinese into the shared document:

```text
./agent_message/agentwork_record/task4_0_colmap_subagent_records.md
```

Each Subagent must write handover data for Core Agent and other Subagents in English into:

```text
./agent_message/communication/task4_0/<subagent_name>/communication.md
```

Each `communication.md` must include:

```text
1. Files generated
2. File paths
3. File formats
4. Commands executed
5. Key metrics
6. Known issues
7. Data needed by the next Subagent
```

---

# 2. Agent Organization

## 2.1 Core Agent V4

Responsible for:

```text
1. Read previous agent records and full project files.
2. Read this task list.
3. Dispatch one function to one Subagent.
4. Check each Subagent's submitted metric checklist.
5. Check each Subagent's communication.md compliance.
6. After all Subagents finish, run the full COLMAP pipeline once from start to end.
7. Confirm that the whole project is usable.
8. If the full pipeline fails, identify the problematic file/module and return it to the corresponding Subagent for correction.
9. Write final Task 4.0 summary.
```

Core Agent V4 does not need to deeply review every line of implementation code. Its acceptance responsibility is based on:

```text
1. Whether each Subagent's metrics are complete.
2. Whether communication.md is compliant.
3. Whether the full pipeline can run successfully.
4. Whether final required output files exist and can be opened.
```

---

# 3. Task Breakdown

Each Subagent corresponds to one function. Each function must be implemented as an independent module or script when applicable.

Recommended directory structure:

```text
./colmap_pipeline/
├── check_inputs.py
├── run_feature_extraction.py
├── run_matching.py
├── run_sparse_mapping.py
├── run_dense_reconstruction.py
├── run_meshing.py
├── convert_to_glb.py
├── validate_colmap_outputs.py
├── generate_report.py
└── utils.py

./main_colmap.py
```

---

# Task 4.0-A: Project and Input Check

## Responsible Agent

```text
Subagent 4.0-A
```

## Function

Check project structure, previous records, COLMAP availability, Conda environment, and input images.

## Required Reading

Before implementation, this Subagent must read:

```text
./AGENT_WORK_PROTOCOL.md
./V1_TASK.md
./V2_TASK.md
./TASK3_0_TASKLIST.md
./agent_message/agentwork_record/
```

## Input

```text
./data/image/
./config.yaml
./agent_message/agentwork_record/
```

## Output

```text
./results/colmap/check/input_check_report.md
./agent_message/communication/task4_0/subagent_4_0_A/communication.md
```

## Required Work

```text
1. Check whether the 3D_Reconstruction Conda environment is active or usable.
2. Check whether the colmap command exists.
3. Check whether ./data/image/ exists.
4. Count valid input images.
5. Check image extensions and whether images can be opened.
6. Check whether previous records exist.
7. Create required output directories under ./results/colmap/.
```

## Acceptance Metrics

```text
1. input_check_report.md exists.
2. Number of valid images is reported.
3. COLMAP availability is reported.
4. Conda environment status is reported.
5. Required result directories are created.
6. communication.md is written in English and includes handover data.
```

---

# Task 4.0-B: COLMAP Feature Extraction

## Responsible Agent

```text
Subagent 4.0-B
```

## Function

Run COLMAP feature extraction on input images.

## Input

```text
./data/image/
./results/colmap/check/input_check_report.md
```

## Output

```text
./results/colmap/database.db
./results/colmap/logs/feature_extraction.log
./agent_message/communication/task4_0/subagent_4_0_B/communication.md
```

## Required Command

Preferred GPU command:

```bash
colmap feature_extractor \
    --database_path ./results/colmap/database.db \
    --image_path ./data/image \
    --ImageReader.single_camera 1 \
    --SiftExtraction.use_gpu 1
```

If GPU fails, use CPU fallback:

```bash
colmap feature_extractor \
    --database_path ./results/colmap/database.db \
    --image_path ./data/image \
    --ImageReader.single_camera 1 \
    --SiftExtraction.use_gpu 0
```

## Required Work

```text
1. Run feature extraction.
2. Save command output to feature_extraction.log.
3. Confirm database.db exists.
4. Record GPU or CPU mode.
5. Record whether the command succeeded.
```

## Acceptance Metrics

```text
1. database.db exists.
2. feature_extraction.log exists.
3. Feature extraction command succeeds.
4. GPU/CPU mode is recorded.
5. communication.md is written in English and includes database path.
```

---

# Task 4.0-C: COLMAP Feature Matching

## Responsible Agent

```text
Subagent 4.0-C
```

## Function

Run COLMAP feature matching.

## Input

```text
./results/colmap/database.db
```

## Output

```text
./results/colmap/logs/matching.log
./agent_message/communication/task4_0/subagent_4_0_C/communication.md
```

## Required Command

For fewer than 100 images, use exhaustive matcher:

```bash
colmap exhaustive_matcher \
    --database_path ./results/colmap/database.db \
    --SiftMatching.use_gpu 1
```

If GPU fails:

```bash
colmap exhaustive_matcher \
    --database_path ./results/colmap/database.db \
    --SiftMatching.use_gpu 0
```

## Required Work

```text
1. Run exhaustive matching.
2. Save command output to matching.log.
3. Record whether GPU or CPU mode was used.
4. Record command success or failure.
```

## Acceptance Metrics

```text
1. matching.log exists.
2. Matching command succeeds.
3. database.db still exists after matching.
4. communication.md is written in English.
```

---

# Task 4.0-D: COLMAP Sparse Reconstruction

## Responsible Agent

```text
Subagent 4.0-D
```

## Function

Run COLMAP mapper to generate sparse reconstruction.

## Input

```text
./data/image/
./results/colmap/database.db
```

## Output

```text
./results/colmap/sparse/
./results/colmap/logs/sparse_mapping.log
./agent_message/communication/task4_0/subagent_4_0_D/communication.md
```

## Required Command

```bash
colmap mapper \
    --database_path ./results/colmap/database.db \
    --image_path ./data/image \
    --output_path ./results/colmap/sparse
```

## Required Work

```text
1. Run sparse mapping.
2. Save command output to sparse_mapping.log.
3. Confirm at least one sparse model exists, usually ./results/colmap/sparse/0/.
4. Record number of sparse models generated.
5. Record path of the selected sparse model for later tasks.
```

## Expected Sparse Model Files

```text
./results/colmap/sparse/0/cameras.bin
./results/colmap/sparse/0/images.bin
./results/colmap/sparse/0/points3D.bin
```

## Acceptance Metrics

```text
1. sparse_mapping.log exists.
2. ./results/colmap/sparse/ contains at least one model folder.
3. cameras.bin exists in selected sparse model.
4. images.bin exists in selected sparse model.
5. points3D.bin exists in selected sparse model.
6. communication.md is written in English and reports selected model path.
```

---

# Task 4.0-E: COLMAP Dense Reconstruction

## Responsible Agent

```text
Subagent 4.0-E
```

## Function

Run image undistortion, PatchMatch stereo, and stereo fusion.

## Input

```text
./data/image/
./results/colmap/sparse/0/
```

## Output

```text
./results/colmap/dense/
./results/colmap/dense/fused.ply
./results/colmap/logs/image_undistorter.log
./results/colmap/logs/patch_match_stereo.log
./results/colmap/logs/stereo_fusion.log
./agent_message/communication/task4_0/subagent_4_0_E/communication.md
```

## Required Commands

### Step 1: Image Undistortion

```bash
colmap image_undistorter \
    --image_path ./data/image \
    --input_path ./results/colmap/sparse/0 \
    --output_path ./results/colmap/dense \
    --output_type COLMAP
```

### Step 2: PatchMatch Stereo

```bash
colmap patch_match_stereo \
    --workspace_path ./results/colmap/dense \
    --workspace_format COLMAP \
    --PatchMatchStereo.geom_consistency true
```

### Step 3: Stereo Fusion

```bash
colmap stereo_fusion \
    --workspace_path ./results/colmap/dense \
    --workspace_format COLMAP \
    --input_type geometric \
    --output_path ./results/colmap/dense/fused.ply
```

## Required Work

```text
1. Run image undistorter.
2. Run PatchMatch stereo with geometric consistency enabled.
3. Run stereo fusion.
4. Confirm fused.ply exists.
5. Record runtime and command success/failure.
```

## Acceptance Metrics

```text
1. image_undistorter.log exists.
2. patch_match_stereo.log exists.
3. stereo_fusion.log exists.
4. ./results/colmap/dense/fused.ply exists.
5. fused.ply is not empty.
6. communication.md is written in English and includes fused.ply path.
```

---

# Task 4.0-F: COLMAP Meshing

## Responsible Agent

```text
Subagent 4.0-F
```

## Function

Generate mesh from COLMAP dense reconstruction.

## Input

```text
./results/colmap/dense/fused.ply
./results/colmap/dense/
```

## Output

```text
./results/colmap/dense/meshed-poisson.ply
./results/colmap/dense/meshed-delaunay.ply
./results/colmap/logs/poisson_mesher.log
./results/colmap/logs/delaunay_mesher.log
./agent_message/communication/task4_0/subagent_4_0_F/communication.md
```

## Required Commands

### Poisson Mesh

```bash
colmap poisson_mesher \
    --input_path ./results/colmap/dense/fused.ply \
    --output_path ./results/colmap/dense/meshed-poisson.ply
```

### Delaunay Mesh

```bash
colmap delaunay_mesher \
    --input_path ./results/colmap/dense \
    --output_path ./results/colmap/dense/meshed-delaunay.ply
```

## Required Work

```text
1. Run Poisson meshing.
2. Run Delaunay meshing if possible.
3. If one meshing method fails, record the reason and keep the successful one.
4. Confirm at least one mesh file exists.
```

## Acceptance Metrics

```text
1. At least one of meshed-poisson.ply or meshed-delaunay.ply exists.
2. Mesh file is not empty.
3. Meshing logs exist.
4. communication.md is written in English and reports which mesh is recommended.
```

---

# Task 4.0-G: Mesh to GLB Conversion

## Responsible Agent

```text
Subagent 4.0-G
```

## Function

Convert selected mesh to GLB for Three.js visualization.

## Input

```text
./results/colmap/dense/meshed-poisson.ply
./results/colmap/dense/meshed-delaunay.ply
```

## Output

```text
./results/colmap/model/model.glb
./results/colmap/model/conversion_report.md
./agent_message/communication/task4_0/subagent_4_0_G/communication.md
```

## Required Work

```text
1. Choose a mesh file for conversion.
2. Prefer the better-looking mesh if quality information is available.
3. Convert PLY mesh to GLB using Python inside 3D_Reconstruction.
4. Validate that model.glb exists and is not empty.
```

## Recommended Python Method

Use `trimesh`:

```python
import trimesh
mesh = trimesh.load("./results/colmap/dense/meshed-poisson.ply")
mesh.export("./results/colmap/model/model.glb")
```

If `trimesh` is not installed, install it inside the existing environment:

```bash
pip install trimesh pygltflib
```

## Acceptance Metrics

```text
1. model.glb exists.
2. model.glb is not empty.
3. conversion_report.md exists.
4. Source mesh path is recorded.
5. communication.md is written in English and includes GLB path.
```

---

# Task 4.0-H: COLMAP Output Validation and Report

## Responsible Agent

```text
Subagent 4.0-H
```

## Function

Validate COLMAP outputs and generate reconstruction report.

## Input

```text
./results/colmap/sparse/0/
./results/colmap/dense/fused.ply
./results/colmap/dense/meshed-poisson.ply
./results/colmap/dense/meshed-delaunay.ply
./results/colmap/model/model.glb
```

## Output

```text
./results/colmap/report/reconstruction_report.md
./results/colmap/report/pointcloud_projection.png
./results/colmap/report/mesh_summary.md
./agent_message/communication/task4_0/subagent_4_0_H/communication.md
```

## Required Work

```text
1. Check whether required files exist.
2. Count fused point cloud points.
3. Count mesh vertices and faces if mesh exists.
4. Generate XY/XZ/YZ point cloud projection image.
5. Report whether GLB exists.
6. Compare COLMAP output with previous custom pipeline if previous outputs exist.
```

## Acceptance Metrics

```text
1. reconstruction_report.md exists.
2. pointcloud_projection.png exists.
3. fused.ply point count is reported.
4. mesh vertex/face count is reported if mesh exists.
5. model.glb status is reported.
6. communication.md is written in English.
```

---

# 4. Full Pipeline Script

A main script should be provided:

```text
./main_colmap.py
```

It should run the full pipeline in order:

```text
1. Input check
2. Feature extraction
3. Feature matching
4. Sparse mapping
5. Dense reconstruction
6. Meshing
7. GLB conversion
8. Report generation
```

The Core Agent V4 must run this script after all Subagents complete their work.

Recommended command:

```bash
conda activate 3D_Reconstruction
python main_colmap.py --config config.yaml
```

If a step fails, `main_colmap.py` should stop and print the failed step.

---

# 5. Final Acceptance Criteria

Task 4.0 is accepted only if:

```text
1. Core Agent V4 has read previous records and this task list.
2. Each Subagent has completed its assigned function.
3. Each Subagent has written Chinese work records into task4_0_colmap_subagent_records.md.
4. Each Subagent has written English communication.md.
5. The full pipeline can be run by Core Agent V4.
6. ./results/colmap/dense/fused.ply exists and is not empty.
7. At least one mesh file exists and is not empty.
8. ./results/colmap/model/model.glb exists and is not empty.
9. ./results/colmap/report/reconstruction_report.md exists.
10. Core Agent V4 writes final summary.
```

Final summary path:

```text
./agent_message/agentwork_record/task4_0_colmap_core_summary.md
```

---

# 6. Known Limitations

The following limitations are acceptable:

```text
1. Reconstruction scale may still be arbitrary.
2. Highly reflective, transparent, pure white, or low-texture objects may still reconstruct poorly.
3. COLMAP may fail if input images have insufficient overlap.
4. Texture mapping is not required in Task 4.0.
5. Three.js frontend integration is not required in Task 4.0, but model.glb must be generated for later use.
```

---

# 7. Recommended Follow-up Task

After Task 4.0, the next task can be:

```text
Task 4.1: Three.js COLMAP Result Viewer
```

Input:

```text
./results/colmap/model/model.glb
./results/colmap/dense/fused.ply
./results/colmap/report/reconstruction_report.md
```

Output:

```text
./frontend/index.html
./frontend/main.js
./frontend/assets/model.glb
```

