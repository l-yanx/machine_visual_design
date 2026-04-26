# 基于 InsightFace 的人脸识别系统

使用 InsightFace 的 **RetinaFace（`det_10g`）** 检测 + 5 点关键点对齐 + **ArcFace（`w600k_r50`）** 提取 512 维 embedding，构建注册库；识别阶段对查询图执行同流程，并支持 **余弦相似度** 与 **SVM 分类器** 两种 1:N 匹配方式。默认使用 **GPU**。

---

## 1. 算法原理

整条 pipeline 是 **「检测 → 对齐 → 表征 → 匹配」** 四段：

### 1.1 人脸检测：RetinaFace（`det_10g`）

`buffalo_l` 中携带的检测网络是基于 **RetinaFace / SCRFD** 思路的 ONNX 模型 `det_10g.onnx`：

- 输入：缩放并填充到 `det_size`（默认 640×640）的 BGR 图。
- 输出：每张脸的 **bbox（x1,y1,x2,y2,score）** 与 **5 个关键点**（左右眼、鼻尖、左右嘴角）。
- 网络是 **多尺度 anchor-free** 单阶段检测器，主干 ResNet-10 风格，速度 / 精度折中较好；置信度低于 `--det-thresh` 的人脸会被丢弃。

工程上当一张图含多张脸时，本项目通过 `pick_primary_face` 选 **置信度最高、面积最大** 的那张作为主角。

### 1.2 人脸对齐：基于 5 点关键点的相似变换

ArcFace 的训练数据是 **112×112 标准化人脸**，要求两眼、鼻尖、嘴角位置近似对齐到一组**模板坐标**。本项目调用 InsightFace 自带的：

```python
face_align.norm_crop(img, landmark=face.kps, image_size=112, mode="arcface")
```

它在源 5 点和模板 5 点之间求最小二乘 **2D 相似变换 (旋转 + 等比缩放 + 平移)**，再用该变换 warp 出 112×112 的对齐图。这一步把不同姿态/角度/尺寸的脸拉到同一坐标系，是 ArcFace 能稳定工作的前提。

### 1.3 特征提取：ArcFace（`w600k_r50`）

- 主干：`w600k_r50.onnx` ≈ ResNet-50 backbone，最后输出 **512 维向量**。
- 训练：在 WebFace600K（约 60 万 ID、千万张图）上以 **ArcFace 损失**优化：
  $$
  L = -\log \frac{\exp\bigl(s\cos(\theta_{y_i}+m)\bigr)}{\exp\bigl(s\cos(\theta_{y_i}+m)\bigr) + \sum_{j\ne y_i}\exp\bigl(s\cos\theta_j\bigr)}
  $$
  其中 \(\theta_j\) 是 embedding 与第 \(j\) 类权重向量的夹角，\(m\) 是 **加性角度间隔**。这鼓励同一身份的 embedding 在单位超球面上聚拢，不同身份相互拉开。
- 因此 ArcFace embedding 的语义距离 **本质就是角度距离**：把 embedding **L2 归一化**后，**余弦相似度 = 内积**，即可作为身份相似度度量。

本项目对每张对齐脸取出 embedding 后执行 `v ← v / ‖v‖`，再写入 `embedding/gallery.npz`。

### 1.4 匹配方式 A：余弦相似度

注册库存 \(N\) 个已 L2 归一化的 embedding \(\{g_i\}\) 以及对应身份 \(\{l_i\}\)。查询脸的 embedding 也归一化为 \(q\)，则：

$$
\text{sim}(q, g_i) = q \cdot g_i \in [-1, 1]
$$

判定规则：

- 取 \(i^* = \arg\max_i \text{sim}(q, g_i)\)；
- 若 \(\text{sim}(q, g_{i^*}) \ge \tau\)（`--threshold`，默认 0.35），预测为 \(l_{i^*}\)；
- 否则判为 `unknown`。

这是最朴素、最常用的开集人脸识别策略：**注册库即特征库，查询即向量检索**。

### 1.5 匹配方式 B：SVM 分类器

把 `embedding/gallery.npz` 当作监督学习数据集 \(\{(g_i, l_i)\}\)，用 `sklearn.svm.SVC` 训练一个**多类支持向量机**：

- **Kernel = linear**：在 512 维空间为每两类找一个最大间隔超平面（one-vs-one），决策由所有二分类投票得到。因为 ArcFace embedding 在球面上对身份本就近似线性可分，linear 核通常足够。
- **Kernel = rbf**：可建模非线性边界，对样本量极小或类内方差大的场景偶尔更稳。
- **概率输出**：`probability=True` 时 `sklearn` 在二分类决策值上做 **Platt scaling**（拟合一个 sigmoid），再通过成对耦合（Wu, Lin & Weng, 2004）转成 \(K\) 类后验概率 \(p(y=k\mid q)\)。

判定规则：

- 取 \(k^* = \arg\max_k p(y=k\mid q)\)；
- 若 \(p(y=k^*\mid q) \ge \tau\)（`--threshold`，建议 0.5～0.7），预测为类 \(k^*\)；
- 否则判 `unknown`。

直观上，SVM 抓的是 **「类整体在 embedding 空间的边界」**，而 cosine 抓的是 **「与库中最相似的某一张脸」**——两者侧重点不同，详见第 7 节对比。

---

## 2. 目录结构

```
l4_machine_learning/
├── dataset/                    # 原始数据：每个子文件夹一个身份
│   ├── lhp/  001.jpg 002.jpg ...
│   ├── ln/
│   ├── wmb/
│   ├── zhh/
│   └── zzs/
├── aligned_dataset/            # 由 build_gallery.py 自动生成的对齐人脸（112x112）
├── embedding/                  # 生成的注册特征库
│   ├── gallery.npz             #   embeddings (N,512), labels (N,)
│   └── gallery_meta.json       #   每张样本的元信息
├── svm/                        # SVM 训练脚本与模型
│   ├── train_svm.py
│   └── svm_model.pkl           #   训练后生成
├── models/                     # InsightFace 模型缓存（首次运行自动下载）
├── environment.yml             # conda 环境定义
├── setup_env.sh                # 写入激活钩子（隔离 user-site + 注册 CUDA 库）
├── fr_utils.py                 # 共享工具：建模型、选脸、对齐、L2 归一化
├── build_gallery.py            # 注册：检测 → 对齐 → 提特征 → 写库
└── recognize.py                # 识别：1:N 匹配（cosine 或 svm）
```

> 数据要求：`dataset/<身份名>/*.jpg`，每张图建议只含 1 张人脸；如有多脸将自动取置信度最高且面积最大的那张。

---

## 3. 环境安装

需要先装好 **miniconda/anaconda**，本机 NVIDIA 驱动 ≥ 525（支持 CUDA 12）。CUDA / cuDNN 运行库不必单独装，由 conda env 中的 `nvidia-*` pip wheel 提供。

```bash
cd /home/lyx/machine_visual/l4_machine_learning

conda env create -f environment.yml          # 1) 建环境，从源码编译 InsightFace
conda activate insightface-fr
bash setup_env.sh                            # 2) 写激活钩子（隔离 user-site + 注册 CUDA 库）
conda deactivate && conda activate insightface-fr   # 3) 重新激活让钩子生效
```

> **仅 CPU 运行**：编辑 `environment.yml`，把 `onnxruntime-gpu==1.23.2` 改为 `onnxruntime==1.18.0`，并删除整段 `nvidia-*` wheel；运行命令加 `--ctx-id -1`。

---

## 4. 注册：构建人脸特征库

```bash
python build_gallery.py --ctx-id 0
```

可选参数：

| 参数 | 默认 | 说明 |
|------|------|------|
| `--dataset` | `./dataset` | 原始图片根目录，按身份分子文件夹 |
| `--aligned` | `./aligned_dataset` | 对齐结果输出目录 |
| `--embedding-dir` | `./embedding` | 特征库目录 |
| `--gallery-name` | `gallery.npz` | 特征库文件名 |
| `--model` | `buffalo_l` | InsightFace 模型包名 |
| `--model-root` | `./models` | 模型缓存目录 |
| `--ctx-id` | `0` | GPU 编号；`-1` 表示 CPU |
| `--det-size` | `640 640` | 检测输入分辨率 W H |
| `--det-thresh` | `0.5` | 检测置信度阈值 |

运行结束后会得到：

- `aligned_dataset/<身份>/001.jpg ...`：112×112 对齐人脸
- `embedding/gallery.npz`：注册特征库（key：`embeddings` / `labels`）
- `embedding/gallery_meta.json`：每条记录对应的源图、对齐图、检测分数

---

## 5. 识别：1:N 身份匹配

`recognize.py` 通过 `--matcher` 选择匹配方式：

- **`cosine`**（默认）：与 `embedding/gallery.npz` 中所有向量做余弦相似度，取最大。
- **`svm`**：用 `svm/svm_model.pkl` 直接分类，输出每个身份的概率。

```bash
# 余弦匹配
python recognize.py path/to/query.jpg

# SVM 匹配（先训练，见 5.1）
python recognize.py path/to/query.jpg --matcher svm --threshold 0.5

# 多输入 / 目录 / CPU
python recognize.py img1.jpg img2.png path/to/folder/ --ctx-id -1
```

可选参数：

| 参数 | 默认 | 说明 |
|------|------|------|
| `inputs`（位置参数） | — | 一个或多个图片文件 / 目录 |
| `--matcher` | `cosine` | `cosine` 或 `svm` |
| `--gallery` | `./embedding/gallery.npz` | cosine 匹配器使用 |
| `--svm-model` | `./svm/svm_model.pkl` | svm 匹配器使用 |
| `--threshold` | `0.35` | cosine：最低相似度；svm：最低概率（建议 0.5） |
| `--model` | `buffalo_l` | 与建库时保持一致 |
| `--model-root` | `./models` | 模型缓存目录 |
| `--ctx-id` | `0` | GPU 编号；`-1` 表示 CPU |
| `--det-size` | `640 640` | 检测分辨率 |
| `--det-thresh` | `0.5` | 检测置信度阈值 |
| `--topk` | `3` | 输出前 K 个候选 |

每张图输出一行 JSON：

```json
{"image": "query.jpg", "matcher": "cosine", "prediction": "lhp",
 "best_similarity": 0.7321, "threshold": 0.35,
 "top_matches": [{"identity": "lhp", "similarity": 0.7321}, ...]}

{"image": "query.jpg", "matcher": "svm", "prediction": "lhp",
 "best_probability": 0.9652, "threshold": 0.5,
 "top_matches": [{"identity": "lhp", "probability": 0.9652}, ...]}
```

未检测到人脸时输出 `[no face] <path>`，并跳过。

### 5.1 训练 SVM 分类器

```bash
python svm/train_svm.py            # 默认 linear 核，C=1.0
python svm/train_svm.py --kernel rbf --C 4
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `--gallery` | `./embedding/gallery.npz` | 训练数据来源 |
| `--out` | `./svm/svm_model.pkl` | 保存的模型路径（pickle） |
| `--kernel` | `linear` | `linear` / `rbf` |
| `--C` | `1.0` | 正则化强度 |
| `--gamma` | `scale` | 仅 rbf 核使用 |

数据集变化（增删身份、增减照片）后需依次重跑：

```bash
python build_gallery.py --ctx-id 0   # 重建 embedding 库
python svm/train_svm.py              # 重训 SVM
```

---

## 6. 阈值经验值

ArcFace + L2 归一化下，cosine 相似度的经验范围：

- `> 0.5`：很可能同一人
- `0.35 ~ 0.5`：可能同一人，建议人工复核
- `< 0.3`：通常不同人

SVM 概率的经验范围：

- `> 0.7`：高置信
- `0.5 ~ 0.7`：可接受
- `< 0.5`：不可信，建议判 `unknown`

请基于自己的数据集（已知正负样本扫 ROC）调整 `--threshold`。

---

## 7. Cosine vs SVM：效果与使用场景

| 维度 | Cosine | SVM |
|------|--------|-----|
| 核心思想 | 与库内**单个最相似样本**比对 | 用一个**类整体的决策边界**做分类 |
| 是否需要训练 | 否（建库即用） | 需要 `train_svm.py` |
| 库扩展（加身份/换人） | **直接重建 gallery** 即可 | 必须**重训** SVM |
| 推理复杂度 | \(O(N \times D)\)，与库样本数 \(N\) 成正比 | linear 核 \(O(K \times D)\)，与类别数 \(K\) 成正比；\(N \gg K\) 时 SVM 更快 |
| 类内一致性 | 依赖最相似那一张图 | 在所有训练样本上拟合边界，对类内姿态/光照变化更鲁棒 |
| 类别相近时 | 容易被一两张极端样本带偏 | 边界由间隔最大化决定，更稳 |
| `unknown` 判定 | **天然支持**：相似度 < τ 直接判 unknown | 较弱：闭集 softmax 总要分配概率，需要联合阈值或额外训练 OOD 检测 |
| 样本极少（如每人 1～3 张） | 仍然能用 | 不稳定，决策面被少量样本主导 |
| 调参难度 | 1 个阈值 | kernel / C / gamma / 阈值 |
| 解释性 | 高：可输出最相似样本路径 | 较低：决策值/概率不直观对应到具体样本 |

**何时优先选 cosine**

- 注册成员经常增减（员工进出、客户登记），希望「拍几张照就生效」。
- 需要严格的 `unknown` 判定（开集人脸识别 / 黑名单告警）。
- 每个身份样本数极少。
- 库规模小到中等（几千以内），延迟不敏感。

**何时优先选 SVM**

- 类别集合**固定**且**长期稳定**（教室点名、固定团队考勤）。
- 每个身份样本充足（≥ 几十张），有姿态/光照多样性。
- 库样本数 \(N\) 远大于类别数 \(K\)，希望推理代价只与 \(K\) 有关。
- 想得到**校准过**的概率（如 0.93），方便上层做风控阈值。

---

## 8. 一键最小流程

```bash
conda activate insightface-fr

python build_gallery.py --ctx-id 0
python svm/train_svm.py                          # 可选，仅在打算用 SVM 时
python recognize.py some_test_image.jpg          # cosine
python recognize.py some_test_image.jpg --matcher svm --threshold 0.5   # SVM
```
