# V1_TASK.md

# Traditional Sculpture 3D Reconstruction V1

## Overall Goal

Build V1 of a traditional multi-view 3D reconstruction pipeline for a sculpture object.

V1 contains two main tasks:

- **Task 1 / Subagent 1:** Incremental SfM
- **Task 2 / Subagent 2:** ZNCC-based MVS and PLY generation

The final V1 output should include:

```text
results/sparse/sparse.ply
results/sparse/camera_poses.txt
results/sparse/cameras.json
results/sparse/points3D.json
results/sparse/tracks.json
results/dense/dense.ply
results/dense/depth_maps/
results/dense/confidence_maps/
results/logs/
```

V1 does **not** need to implement mesh reconstruction, texture mapping, or Three.js visualization.

---

## Global Environment Requirement

All development, execution, testing, and package management for V1 must be performed under a Miniconda environment named:

```text
3D_Reconstruction
```

Required rules:

```text
1. Use Miniconda to create and manage the environment.
2. Install all Python packages inside the 3D_Reconstruction environment.
3. Do not install project dependencies into the base environment.
4. Do not rely on system-level Python packages.
5. All scripts must be executed after activating the 3D_Reconstruction environment.
6. If new packages are added, update the environment dependency record.
```

Recommended environment commands:

```bash
conda create -n 3D_Reconstruction python=3.10 -y
conda activate 3D_Reconstruction
```

Recommended dependency record files:

```text
environment.yml
requirements.txt
```

---

# Task 1: Incremental SfM

## Responsible Agent

```text
subagent1
```

## Task Goal

Implement an incremental Structure-from-Motion pipeline using traditional feature-based methods.

The task should recover:

```text
1. Registered camera poses
2. Sparse 3D point cloud
3. 2D-3D feature tracks
4. SfM result files required by Task 2
```

---

## Task 1 Input

### Input Directory

```text
data/images_raw/
```

or, after preprocessing:

```text
data/images_resized/
```

### Input Images

The input images are multi-view RGB images of the same sculpture.

Expected format:

```text
data/images_raw/
├── 0001.jpg
├── 0002.jpg
├── 0003.jpg
├── ...
```

### Camera Intrinsics

If calibrated intrinsics are available:

```text
data/calibration/camera_intrinsics.json
```

Expected content:

```json
{
  "fx": 1000.0,
  "fy": 1000.0,
  "cx": 500.0,
  "cy": 375.0,
  "width": 1000,
  "height": 750
}
```

If no calibrated intrinsics are available, Task 1 should use approximate intrinsics:

```text
fx = fy = 1.2 * image_width
cx = image_width / 2
cy = image_height / 2
```

---

## Task 1 Required Subtasks

### 1. Image Preprocessing

Process all raw input images.

Required operations:

```text
1. Read all images in filename order
2. Resize images to a fixed width, recommended 1000 px
3. Keep the original aspect ratio
4. Save resized images
5. Convert images to grayscale for feature extraction
```

Expected output:

```text
data/images_resized/
├── 0001.jpg
├── 0002.jpg
├── 0003.jpg
├── ...
```

---

### 2. SIFT Feature Extraction

Extract SIFT keypoints and descriptors for each image.

Expected output:

```text
results/features/
├── 0001_keypoints.npy
├── 0001_descriptors.npy
├── 0002_keypoints.npy
├── 0002_descriptors.npy
├── ...
```

Each keypoint should contain:

```text
x
y
scale
orientation
```

---

### 3. Feature Matching

Match SIFT descriptors between image pairs.

Recommended matching strategy for V1:

```text
Sequential matching
```

For image `i`, match it with:

```text
i+1
i+2
i+3
```

Use:

```text
KNN matching
Lowe Ratio Test
```

Recommended ratio threshold:

```text
0.75
```

Expected output:

```text
results/matches/
├── match_0001_0002.npy
├── match_0001_0003.npy
├── match_0001_0004.npy
├── ...
```

---

### 4. RANSAC Geometric Verification

Use RANSAC to estimate the Essential Matrix and remove incorrect matches.

Required method:

```text
RANSAC + Essential Matrix
```

Input:

```text
Matched feature points
Camera intrinsics K
```

Output:

```text
results/matches_verified/
├── inliers_0001_0002.npy
├── inliers_0001_0003.npy
├── inliers_0001_0004.npy
├── ...
```

Each verified match file should contain only geometrically valid inlier matches.

---

### 5. Initial Image Pair Selection

Select the initial image pair for SfM initialization.

Recommended score:

```text
score(i, j) = num_inliers(i, j) * inlier_ratio(i, j)
```

Expected output:

```text
results/sparse/initial_pair.txt
```

Example format:

```text
0001.jpg 0003.jpg
```

---

### 6. Initial Pose Recovery

Recover relative camera pose from the initial image pair.

Required method:

```text
Essential Matrix decomposition
recoverPose
Cheirality check
```

Set the first camera as:

```text
R = I
t = 0
```

Set the second camera as:

```text
R = recovered R
t = recovered t
```

Expected output:

```text
Initial registered cameras
Initial relative pose
```

---

### 7. Initial Triangulation

Triangulate initial 3D points from the initial image pair.

Required filtering:

```text
1. Positive depth check
2. Reprojection error filtering
3. Abnormal distance filtering
```

Recommended reprojection error threshold:

```text
3 px to 5 px
```

Expected output:

```text
results/sparse/initial_sparse.ply
```

---

### 8. Incremental Image Registration

Register remaining images incrementally.

For each unregistered image:

```text
1. Find matches with registered images
2. Build 2D-3D correspondences
3. Estimate camera pose using PnP + RANSAC
4. Register the image if enough inliers are found
5. Triangulate new 3D points with registered neighboring images
6. Filter new points by reprojection error and positive depth
7. Update tracks
```

Recommended thresholds:

```text
PnP minimum inliers: 30
PnP reprojection error threshold: 5 px
Triangulation reprojection error threshold: 5 px
```

---

### 9. Export SfM Results

Export the final SfM results for Task 2.

Required output:

```text
results/sparse/
├── sparse.ply
├── camera_poses.txt
├── cameras.json
├── points3D.json
├── tracks.json
```

---

## Task 1 Output

Task 1 must produce:

```text
results/sparse/sparse.ply
results/sparse/camera_poses.txt
results/sparse/cameras.json
results/sparse/points3D.json
results/sparse/tracks.json
results/sparse/initial_pair.txt
results/sparse/initial_sparse.ply
results/features/
results/matches/
results/matches_verified/
results/logs/sfm_log.txt
```

---

## Task 1 Acceptance Criteria

Task 1 is considered complete if all the following conditions are satisfied:

```text
1. At least 60% of input images are successfully registered.
2. sparse.ply can be opened in Open3D, MeshLab, or CloudCompare.
3. camera_poses.txt contains valid R and t for each registered image.
4. cameras.json contains valid camera intrinsics.
5. points3D.json contains valid 3D points.
6. tracks.json records the relationship between 3D points and 2D observations.
7. The sparse point cloud roughly shows the sculpture structure.
8. The recovered camera trajectory is spatially reasonable.
9. The average reprojection error should preferably be less than 5 px.
10. Each successfully registered image should preferably have more than 30 PnP inliers.
```

---

# Task 2: ZNCC-based MVS and Dense PLY Generation

## Responsible Agent

```text
subagent2
```

## Task Goal

Implement a simplified traditional Multi-View Stereo module based on ZNCC plane sweeping.

The task should generate:

```text
1. Depth maps
2. Confidence maps
3. Fused dense point cloud
4. dense.ply
```

Task 2 depends on Task 1 outputs.

---

## Task 2 Input

### Required SfM Input

```text
results/sparse/sparse.ply
results/sparse/camera_poses.txt
results/sparse/cameras.json
results/sparse/points3D.json
results/sparse/tracks.json
```

### Required Image Input

```text
data/images_resized/
```

Expected format:

```text
data/images_resized/
├── 0001.jpg
├── 0002.jpg
├── 0003.jpg
├── ...
```

Only images successfully registered by Task 1 should be used for MVS.

---

## Task 2 Required Subtasks

### 1. Read SfM Results

Read camera intrinsics, camera poses, sparse points, and tracks from Task 1.

Required input:

```text
results/sparse/camera_poses.txt
results/sparse/cameras.json
results/sparse/points3D.json
results/sparse/tracks.json
```

Expected internal data:

```text
1. Registered image list
2. Camera intrinsic matrix K
3. Camera pose R, t for each image
4. Sparse 3D points
5. Image-point visibility information
```

---

### 2. Reference View and Source View Selection

Select source views for each reference image.

V1 recommended strategy:

```text
For each registered image:
    choose neighboring registered images by filename order
```

Recommended source view count:

```text
3 or 4
```

Expected output:

```text
results/dense/view_pairs.json
```

Example format:

```json
{
  "0001.jpg": ["0002.jpg", "0003.jpg", "0004.jpg"],
  "0002.jpg": ["0001.jpg", "0003.jpg", "0004.jpg"]
}
```

---

### 3. Depth Range Estimation

Estimate depth search range for each reference image using sparse points.

Required method:

```text
1. Transform sparse 3D points into the reference camera coordinate system
2. Keep points with positive depth
3. Use valid depth distribution to estimate min and max depth
4. Use the 5% and 95% percentiles as the base depth range
```

Recommended expansion:

```text
depth_min = 0.9 * percentile_5
depth_max = 1.1 * percentile_95
```

Expected output:

```text
results/dense/depth_ranges.json
```

Example format:

```json
{
  "0001.jpg": {
    "min_depth": 1.2,
    "max_depth": 4.8
  }
}
```

---

### 4. ZNCC Patch Similarity

Implement ZNCC similarity calculation between two image patches.

Input:

```text
reference patch
source patch
```

Output:

```text
ZNCC score
```

Required behavior:

```text
1. Return high score for similar patches
2. Return low score for dissimilar patches
3. Mark weak-texture patches as invalid if variance is too small
```

Recommended patch size:

```text
5 x 5
```

Recommended weak texture variance threshold:

```text
1e-5
```

---

### 5. Plane Sweeping Depth Estimation

Estimate a depth map for each selected reference image.

Required input:

```text
Reference image
Source images
K
Reference camera pose R_ref, t_ref
Source camera poses R_src, t_src
Depth range
```

Recommended V1 parameters:

```text
depth_samples = 64
patch_size = 5
source_view_num = 3
stride = 2
zncc_threshold = 0.5
```

For each reference pixel sampled by stride:

```text
1. Generate candidate depths between depth_min and depth_max
2. Back-project the reference pixel at each candidate depth into 3D
3. Project the 3D point into each source view
4. Extract reference and source patches
5. Compute ZNCC score
6. Aggregate ZNCC scores across source views
7. Select the depth with the highest score
8. Save depth if confidence is above threshold
```

Expected output:

```text
results/dense/depth_maps/
├── 0001_depth.npy
├── 0002_depth.npy
├── ...

results/dense/confidence_maps/
├── 0001_confidence.npy
├── 0002_confidence.npy
├── ...
```

---

### 6. Depth Map Filtering

Filter invalid or unreliable depth values.

Required filtering:

```text
1. Remove depth values with low confidence
2. Remove depth values less than or equal to zero
3. Remove depth values outside the estimated depth range
4. Optionally apply median filtering
```

Recommended confidence threshold:

```text
0.5
```

Expected output:

```text
results/dense/depth_maps_filtered/
├── 0001_depth_filtered.npy
├── 0002_depth_filtered.npy
├── ...
```

---

### 7. Depth Back-projection

Convert filtered depth maps into partial point clouds.

For each valid depth pixel:

```text
p = [u, v, 1]^T
X_cam = depth * K^-1 * p
X_world = R^-1 * (X_cam - t)
```

Assign color from the reference image:

```text
point_color = image[v, u]
```

Expected output:

```text
results/dense/partial_pointclouds/
├── 0001_partial.ply
├── 0002_partial.ply
├── ...
```

---

### 8. Dense Point Cloud Fusion

Fuse all partial point clouds into a single dense point cloud.

Required operations:

```text
1. Merge all partial point clouds
2. Remove NaN and infinite values
3. Apply voxel downsampling
4. Apply statistical outlier removal
5. Export fused dense point cloud
```

Recommended parameters:

```text
voxel_size = 0.02
outlier_nb_neighbors = 20
outlier_std_ratio = 2.0
```

Expected final output:

```text
results/dense/dense.ply
```

---

## Task 2 Output

Task 2 must produce:

```text
results/dense/dense.ply
results/dense/view_pairs.json
results/dense/depth_ranges.json
results/dense/depth_maps/
results/dense/confidence_maps/
results/dense/depth_maps_filtered/
results/dense/partial_pointclouds/
results/logs/mvs_log.txt
```

---

## Task 2 Acceptance Criteria

Task 2 is considered complete if all the following conditions are satisfied:

```text
1. Task 2 can successfully read Task 1 SfM outputs.
2. Each selected reference image has valid source views.
3. Each selected reference image has a valid depth range.
4. At least 3 reference images produce valid depth maps.
5. The generated depth maps contain valid depth values in sculpture regions.
6. Confidence maps are generated together with depth maps.
7. Filtered depth maps remove obvious invalid values.
8. Partial point clouds can be generated from depth maps.
9. dense.ply can be opened in Open3D, MeshLab, or CloudCompare.
10. dense.ply contains significantly more points than sparse.ply.
11. The dense point cloud roughly shows the main surface structure of the sculpture.
12. The dense point cloud should not contain large-scale flying points.
```

---

# Interface Between Task 1 and Task 2

Task 1 must provide the following files to Task 2:

```text
results/sparse/camera_poses.txt
results/sparse/cameras.json
results/sparse/points3D.json
results/sparse/tracks.json
results/sparse/sparse.ply
```

Task 2 must not assume access to internal variables from Task 1.

Task 2 should only read the exported files from Task 1.

---

# Global V1 Acceptance Criteria

V1 is complete only if both Task 1 and Task 2 pass their acceptance criteria.

Final required files:

```text
results/sparse/sparse.ply
results/sparse/camera_poses.txt
results/sparse/cameras.json
results/sparse/points3D.json
results/sparse/tracks.json
results/dense/dense.ply
results/dense/depth_maps/
results/dense/confidence_maps/
results/logs/sfm_log.txt
results/logs/mvs_log.txt
```

V1 does not need to produce:

```text
1. Mesh
2. Texture
3. GLB / OBJ model
4. Three.js frontend
5. Full Bundle Adjustment
6. High-quality final reconstruction
```

The main goal of V1 is:

```text
Input multi-view sculpture images
→ recover camera poses and sparse point cloud using incremental SfM
→ estimate depth maps using ZNCC-based MVS
→ fuse depth maps into dense.ply
```
