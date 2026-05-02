# Machine Visual — 计算机视觉课程实验

本项目包含五个实验模块，覆盖经典视觉算法到深度学习与三维重建。

## l1_frequent — 高频/低频频域融合

两张图像在频域中融合：对 A、B 分别做 2D FFT，用圆形低通掩码提取 B 的低频（结构/颜色基底）和 A 的高频（细节纹理），在频域加权叠加后 IFFT 回到空域。

```
Out = b_gain × B_low(r) + high_gain × A_high(r)
```

## l2_keypoint — 角点检测与特征匹配

在统一管线（原图 → 几何/photometric 变换 → 独立检测 → 匹配 → 拼接可视化）下对比三种方法：

| 方法 | 特征点 | 描述子 | 匹配 |
|---|---|---|---|
| Harris | 梯度二阶矩角点响应 | 邻域强度 + 梯度方向直方图 | ratio + mutual / RANSAC |
| ORB | FAST 金字塔关键点 | 二进制 oBRIEF（汉明距离） | ratio + mutual / RANSAC |
| SIFT | DoG 空间极值点 | 128 维梯度方向直方图（L2） | ratio + mutual / RANSAC |

RANSAC 分支通过单应性几何一致性筛除外点，视觉上匹配更干净。

## l3_BoVW — Dense-SIFT + K-Means 词袋人脸识别

不依赖深度学习的经典人脸识别流水线：

1. 人脸图 → 3×3 空间分块（保留粗粒度空间结构）
2. 每块做 5×5 网格 Dense-SIFT（128 维描述子，共 225 个/图）
3. K-Means 聚类（K=100）训练共享视觉词典
4. 每块统计词频直方图后拼接为 900 维特征，L2 归一化
5. 欧氏距离最近邻匹配身份

核心改进：3×3 分块保留五官空间布局；每图单独入库而非按人求重心，保留姿态多样性。

## l4_machine_learning — 基于 InsightFace/ArcFace 的人脸识别

现代深度学习方案，对比上一实验的传统 BoVW 方法：

- **检测**：RetinaFace（bbox + 5 点关键点）
- **对齐**：仿射变换 → 112×112 标准化人脸
- **特征**：ArcFace (w600k_r50) 输出 512 维 L2 归一化 embedding
- **匹配**：余弦相似度（开集天然支持 unknown）或 SVM 分类器（闭集更稳）

ArcFace embedding 类内紧、类间松，单纯余弦相似度即可达到高准确率。

## l5_2D23D — 多视角图像三维重建

从多视角 RGB 图像重建物体三维模型（稀疏点云 → 稠密点云 → Mesh → GLB）。包含两条路线：

- **V1–V3 自研**：从零实现增量式 SfM（SIFT + KNN 匹配 + RANSAC + PnP + 三角测量）、ZNCC-MVS 深度估计、点云清理（统计/半径离群点去除、DBSCAN 聚类）、泊松表面重建
- **V4 COLMAP**：使用成熟工具链（feature_extractor → exhaustive_matcher → mapper → patch_match_stereo → stereo_fusion → poisson_mesher），追求更好的实际重建效果

最终输出 GLB 模型，用 Three.js 前端展示。
