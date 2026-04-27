# 基于 InsightFace 的人脸识别系统

---

## 1. 项目简介

本项目实现了一个**端到端的 1:N 人脸识别系统**：给定按身份组织的少量人脸照片作为注册库，对任意一张查询图判定它属于哪一位已注册成员（或判为 `unknown`）。整个流程基于 [InsightFace](https://github.com/deepinsight/insightface) 工具库，默认在 **GPU** 上运行，并提供 **余弦相似度**与 **SVM** 两种身份判定方式。

系统由以下模块协同完成：


| 模块              | 实现                                         | 作用                                |
| --------------- | ------------------------------------------ | --------------------------------- |
| **人脸检测**        | InsightFace `det_10g`（RetinaFace/SCRFD 系列） | 在原图上找到所有人脸的 **bbox + 5 个关键点**     |
| **人脸对齐**        | `face_align.norm_crop`                     | 用 5 点关键点做仿射变换，把人脸**标准化为 112×112** |
| **特征提取**        | InsightFace `w600k_r50`（ArcFace）           | 从对齐脸抽取 **512 维 embedding** 作为身份表征 |
| **注册库**         | `embedding/gallery.npz`                    | 把所有注册脸的 embedding 与身份标签持久化        |
| **匹配 (cosine)** | NumPy 内积                                   | 与库内向量做**余弦相似度**取最大，超阈值则命中         |
| **匹配 (SVM)**    | `sklearn.svm.SVC`                          | 在 embedding 上训练**支持向量机**做闭集分类     |
| **可视化**         | PCA + t-SNE + 热力图                          | 直观验证 embedding 聚簇质量               |


---

## 2. 文件架构

```
l4_machine_learning/
├── dataset/                    # 原始数据：每个子文件夹一个身份
│   ├── lhp/  001.jpg 002.jpg ...
│   ├── ln/
│   ├── wmb/
│   ├── zhh/
│   └── zzs/
├── aligned_dataset/            # build_gallery.py 生成的 112×112 对齐脸
├── embedding/                  # 注册特征库
│   ├── gallery.npz             #   embeddings (N,512), labels (N,)
│   └── gallery_meta.json       #   每条样本的元信息
├── svm/                        # SVM 分类器
│   ├── train_svm.py
│   └── svm_model.pkl           #   训练后生成
├── visualization/              # 可视化脚本与产物
│   ├── visualize.py
│   └── output/
│       ├── tsne_scatter.png
│       └── pairwise_heatmap.png
├── models/                     # InsightFace 预训练模型缓存（首次运行自动下载）
├── test/                       # 自由放置的测试图片
├── environment.yml             # conda 环境定义
├── setup_env.sh                # 写入激活钩子（隔离 user-site + 注册 CUDA 库）
├── fr_utils.py                 # 共享工具：建模型、选脸、对齐、L2 归一化
├── build_gallery.py            # 注册：检测 → 对齐 → 提特征 → 写库
└── recognize.py                # 识别：1:N 匹配（cosine 或 svm）
```

---

## 3. Pipeline 与各模块原理

整条流水线分为 **检测 → 对齐 → 表征 → 匹配** 四步，对**注册**和**识别**两条路径同样适用：

```
原图 ──► 检测 (RetinaFace) ──► 5 点关键点
                              │
                              ▼
                   仿射对齐 (norm_crop, 112×112)
                              │
                              ▼
            ArcFace 推理 (w600k_r50, 512-D embedding)
                              │
                              ▼
       ┌──────────────────────┴──────────────────────┐
       │ 注册：写入 gallery.npz                      │
       │ 识别：与 gallery 比对 (cosine) 或经 SVM 分类 │
       └─────────────────────────────────────────────┘
```

### 3.1 人脸检测：RetinaFace（`det_10g`）

`buffalo_l` 中携带的检测网络是基于 **RetinaFace / SCRFD** 思路的 ONNX 模型 `det_10g.onnx`：

- 输入：缩放并填充到 `det_size`（默认 640×640）的 BGR 图。
- 输出：每张脸的 **bbox（x1, y1, x2, y2, score）** 与 **5 个关键点**（左右眼、鼻尖、左右嘴角）。
- 网络是 **多尺度 anchor-free** 单阶段检测器，主干 ResNet-10 风格，速度 / 精度折中较好；置信度低于 `--det-thresh` 的脸会被丢弃。

工程上当一张图含多张脸时，本项目通过 `pick_primary_face` 选 **置信度最高、面积最大** 的那张作为主角。

### 3.2 人脸对齐：5 点关键点 → 仿射变换

ArcFace 的训练数据是 **112×112 标准化人脸**，要求两眼、鼻尖、嘴角位置近似对齐到一组**模板坐标**。本项目调用 InsightFace 自带的：

```python
face_align.norm_crop(img, landmark=face.kps, image_size=112, mode="arcface")
```

它在源 5 点和模板 5 点之间求最小二乘的 **2D 相似变换（旋转 + 等比缩放 + 平移）**，再用该变换 warp 出 112×112 的对齐图。这一步把不同姿态/角度/尺寸的脸拉到同一坐标系，是 ArcFace 能稳定工作的前提。

### 3.3 特征提取：ArcFace（`w600k_r50`）

- 主干：`w600k_r50.onnx` ≈ ResNet-50 backbone，最后输出 **512 维向量**。
- 训练：在 WebFace600K（约 60 万 ID、千万张图）上以 **ArcFace 损失**优化：
  $$
  L = -\log \frac{\exp\bigl(s\cos(\theta_{y_i}+m)\bigr)}{\exp\bigl(s\cos(\theta_{y_i}+m)\bigr) + \sum_{j\ne y_i}\exp\bigl(s\cos\theta_j\bigr)}
  $$
  其中 \(\theta_j\) 是 embedding 与第 \(j\) 类权重向量的夹角，\(m\) 是 **加性角度间隔**。这鼓励同一身份的 embedding 在单位超球面上聚拢，不同身份相互拉开。
- 因此 ArcFace embedding 的语义距离**本质就是角度距离**：把 embedding **L2 归一化**后，**余弦相似度 = 内积**，可直接作为身份相似度度量。

本项目对每张对齐脸取出 embedding 后执行 v \leftarrow v/v，再写入 `embedding/gallery.npz`。

### 3.4 匹配方式 A：余弦相似度

注册库存 N 个已 L2 归一化的 embedding g_i 以及对应身份 l_i。查询脸的 embedding 也归一化为 q，则：

$$\text{sim}(q, g_i) = q \cdot g_i \in [-1, 1]$$

- 取 i^* = \arg\max_i \text{sim}(q, g_i)；
- 若 \text{sim}(q, g_{i^*}) \ge \tau（`--threshold`，默认 0.35），预测为 l_{i^*}；
- 否则判为 `unknown`。

最朴素也最常用的开集人脸识别策略：**注册库即特征库，查询即向量检索**。

### 3.5 匹配方式 B：SVM 分类器

把 `embedding/gallery.npz` 当作监督学习数据集 (g_i, l_i)，用 `sklearn.svm.SVC` 训练一个**多类支持向量机**：

- **Kernel = linear**：在 512 维空间为每两类找最大间隔超平面（one-vs-one），决策由所有二分类投票得到。ArcFace embedding 在球面上对身份近似线性可分，linear 核通常足够。
- **Kernel = rbf**：可建模非线性边界，对类内方差大的场景偶尔更稳。
- **概率输出**：`probability=True` 时 `sklearn` 在二分类决策值上做 **Platt scaling**（拟合一个 sigmoid），再通过成对耦合（Wu, Lin & Weng, 2004）转为 K 类后验概率 p(y=k\mid q)。

判定规则：

- 取 k^* = \arg\max_k p(y=k\mid q)；
- 若 p(y=k^*\mid q) \ge \tau（`--threshold`，建议 0.5～0.7），预测为类 k^*；
- 否则判 `unknown`。

直观上，SVM 抓的是 **「类整体在 embedding 空间的边界」**，cosine 抓的是 **「与库中最相似的某一张脸」**。

### 3.6 表征质量验证：PCA(50) → t-SNE(2) 与相似度热力图

为了**直观验证 ArcFace embedding 是否真的把不同人分得开**，`visualization/visualize.py` 把 5 个身份共 608 张脸的 512 维 embedding 先用 **PCA 压到 50 维**（保留 ≈ 97.4% 方差），再用 **t-SNE 投影到 2 维**做散点图：

t-SNE 2D 散点图

5 个身份各自形成**紧密、互不重叠的色团**——说明 ArcFace 把同一人的不同照片拉到了 embedding 空间的同一小邻域，把不同人推得很开，**类内方差远小于类间距离**。这正是后续无论用 cosine 还是 SVM 都能拿到接近 100% 准确率的根本原因。

进一步，把所有样本两两余弦相似度画成热力图（按身份排序，使同身份样本相邻）：

两两余弦相似度热力图

可以看到 **5 个对角块明显高亮**（块内 ≈ 0.6 ~ 1.0），块外区域偏暗（≈ 0.0 ~ 0.3）；这与「类内紧、类间松」的几何结论完全一致。

### 3.7 cosine 与 SVM 的优缺点对比


| 维度             | Cosine                       | SVM                                                |
| -------------- | ---------------------------- | -------------------------------------------------- |
| 核心思想           | 与库内**单个最相似样本**比对             | 用一个**类整体的决策边界**做分类                                 |
| 是否需要训练         | 否（建库即用）                      | 需要 `train_svm.py`                                  |
| 库扩展（加身份/换人）    | **直接重建 gallery** 即可          | 必须**重训** SVM                                       |
| 推理复杂度          | O(N \times D)，与库样本数 N 成正比    | linear 核 O(K \times D)，与类别数 K 成正比；N \gg K 时 SVM 更快 |
| 类内一致性          | 依赖最相似那一张图                    | 在所有训练样本上拟合边界，对类内姿态/光照变化更鲁棒                         |
| 类别相近时          | 容易被一两张极端样本带偏                 | 边界由间隔最大化决定，更稳                                      |
| `unknown` 判定   | **天然支持**：相似度 < τ 直接判 unknown | 较弱：闭集 softmax 总要分配概率                               |
| 样本极少（每人 1～3 张） | 仍然能用                         | 不稳定，决策面被少量样本主导                                     |
| 调参难度           | 1 个阈值                        | kernel / C / gamma / 阈值                            |
| 解释性            | 高：可输出最相似样本路径                 | 较低：决策值 / 概率不直观对应到具体样本                              |


**何时优先选 cosine**：注册成员经常增减（员工进出、客户登记）、需要严格 `unknown` 判定（开集 / 黑名单）、每个身份样本数少、库规模小到中等。

**何时优先选 SVM**：类别集合**固定且长期稳定**（教室点名、固定团队考勤）、每个身份样本充足且姿态/光照多样、库样本数 N \gg K 想让推理代价只与 K 有关、想得到**校准过**的概率值。

---

## 4. 与传统人脸识别方法相比的优势

相对于 **DenseSIFT+Kmeans+BoVW** 等传统流水线，本项目有以下显著优势：

1. **自动检测并裁剪人脸**
  传统方案（如直接拿原图做 LBPH）往往要求**手动框出人脸或预先裁剪**；本项目用 RetinaFace 自动定位多张人脸的 bbox + 5 点关键点，整张大图直接进、人脸自动出，免人工。
2. **特征提取更有效**
  DensSIFT 等基于像素或人工设计的局部纹理特征，在跨光照、跨年龄、跨姿态时区分度急剧下降；ArcFace 在 60 万身份、千万张图上以**加性角度间隔损失**端到端学习，得到的 512 维 embedding 类内紧、类间松，单纯的余弦相似度即可达到当下 SOTA 级的识别效果（见第 3.6 节散点图与热力图）。
3. **关键点对齐让模型对姿态 / 光照鲁棒**
  传统方法直接在原始裁剪图上算特征，**侧脸、抬头、强逆光**都会显著拉低识别率；本项目用 5 点关键点把每张脸 warp 到统一的 112×112 模板，再喂进 backbone，姿态与光照差异在表征前已被大幅抹平。
4. **新增 / 删除身份零成本，无需重训 backbone**
  传统的「特征 + 分类器」流水线（如 EigenFaces + 全局 PCA 子空间）每加一个人都要重算子空间或重训分类器；本项目 backbone 是**预训练好的 ArcFace**，新增成员只需「几张图 → 一次前向 → 写入 `gallery.npz`」即可生效，cosine 不用训、SVM 也只需在轻量 embedding 上重训一次。

---

## 5. 环境与运行

### 5.1 环境安装

需要先装好 **miniconda / anaconda**，本机 NVIDIA 驱动 ≥ 525（支持 CUDA 12）。CUDA / cuDNN 运行库不必单独装，由 conda env 中的 `nvidia-`* pip wheel 提供。

```bash
conda env create -f environment.yml          # 1) 建环境，从源码编译 InsightFace
conda activate insightface-fr
bash setup_env.sh                            # 2) 写激活钩子（隔离 user-site + 注册 CUDA 库）
conda deactivate && conda activate insightface-fr   # 3) 重新激活让钩子生效
```

> **仅 CPU 运行**：编辑 `environment.yml`，把 `onnxruntime-gpu==1.23.2` 改为 `onnxruntime==1.18.0`，并删除整段 `nvidia-`* wheel；运行命令加 `--ctx-id -1`。

### 5.2 运行

#### Step 1 — 准备数据

把每个身份的若干张照片放进 `dataset/<身份名>/`，结构如「文件架构」一节所示。

#### Step 2 — 注册：构建特征库

```bash
python build_gallery.py --ctx-id 0
```

完成后生成 `aligned_dataset/`、`embedding/gallery.npz`、`embedding/gallery_meta.json`。


| 参数                | 默认                  | 说明                 |
| ----------------- | ------------------- | ------------------ |
| `--dataset`       | `./dataset`         | 原始图片根目录            |
| `--aligned`       | `./aligned_dataset` | 对齐结果输出目录           |
| `--embedding-dir` | `./embedding`       | 特征库目录              |
| `--ctx-id`        | `0`                 | GPU 编号；`-1` 表示 CPU |
| `--det-size`      | `640 640`           | 检测分辨率              |
| `--det-thresh`    | `0.5`               | 检测置信度阈值            |


#### Step 3 — 训练 SVM 分类器

如果打算用 SVM 模式识别：

```bash
python svm/train_svm.py            # 默认 linear 核，C=1.0
```


| 参数          | 默认                        | 说明               |
| ----------- | ------------------------- | ---------------- |
| `--gallery` | `./embedding/gallery.npz` | 训练数据来源           |
| `--out`     | `./svm/svm_model.pkl`     | 输出路径（pickle）     |
| `--kernel`  | `linear`                  | `linear` / `rbf` |
| `--C`       | `1.0`                     | 正则化强度            |


#### Step 4 — 识别

```bash
# 余弦匹配
python recognize.py path/to/query.jpg

# SVM 匹配
python recognize.py path/to/query.jpg --matcher svm --threshold 0.5

# 多输入 / 整个目录 / CPU
python recognize.py img1.jpg img2.png path/to/folder/ --ctx-id -1
```


| 参数             | 默认                        | 说明                            |
| -------------- | ------------------------- | ----------------------------- |
| `inputs`（位置参数） | —                         | 一个或多个图片文件 / 目录                |
| `--matcher`    | `cosine`                  | `cosine` 或 `svm`              |
| `--gallery`    | `./embedding/gallery.npz` | cosine 匹配器使用                  |
| `--svm-model`  | `./svm/svm_model.pkl`     | svm 匹配器使用                     |
| `--threshold`  | `0.35`                    | cosine：最低相似度；svm：最低概率（建议 0.5） |
| `--ctx-id`     | `0`                       | GPU 编号；`-1` 表示 CPU            |
| `--topk`       | `3`                       | 输出前 K 个候选                     |


每张查询图输出一行 JSON：

```json
{"image": "query.jpg", "matcher": "cosine", "prediction": "lhp",
 "best_similarity": 0.7321, "threshold": 0.35,
 "top_matches": [{"identity": "lhp", "similarity": 0.7321}, ...]}

{"image": "query.jpg", "matcher": "svm", "prediction": "lhp",
 "best_probability": 0.9652, "threshold": 0.5,
 "top_matches": [{"identity": "lhp", "probability": 0.9652}, ...]}
```

#### 可视化

```bash
python visualization/visualize.py
```

输出 `visualization/output/tsne_scatter.png` 与 `visualization/output/pairwise_heatmap.png`，供检查 embedding 聚簇质量。

### 5.3 一键最小流程

```bash
conda activate insightface-fr

python build_gallery.py --ctx-id 0
python svm/train_svm.py                          # 可选：仅在打算用 SVM 时
python recognize.py test/some.jpg                                  # cosine
python recognize.py test/some.jpg --matcher svm --threshold 0.5    # SVM
```

### 5.4 阈值经验值

ArcFace + L2 归一化下，cosine 相似度的经验范围：

- `> 0.5` 很可能同一人 / `0.35 ~ 0.5` 可能同一人 / `< 0.3` 通常不同人

SVM 概率的经验范围：

- `> 0.7` 高置信 / `0.5 ~ 0.7` 可接受 / `< 0.5` 判 `unknown`