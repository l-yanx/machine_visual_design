# l3_BoVW：空间分块 BoVW

## 1. 项目任务说明

在固定 **1920×1080** 的图像上，用 **3×3 空间分块 + Dense SIFT + 共享视觉词典（K-Means）** 提取高维表示；以 **每人一文件夹** 为身份单元，对文件夹内多幅人脸图的特征做 **逐维平均** 得到该人的 **库中向量**，供后续 **按余弦相似度**（L2-单位向量下为点积）的最近邻身份检索（见 `match_face.py` 或自写批量推理）。

## 2. 文件架构、数据与库、环境

### 2.1 代码与脚本（简述）

| 路径/文件 | 作用 |
|-----------|------|
| `bovw.py` | 3×3 分块、Dense SIFT 提取与编码、空间 BoVW 工具函数 |
| `train_bovw.py` | 从数据集收集描述子、训练 K-Means 词典、生成每人原型特征与 `.npy` 输出 |
| `match_face.py` | 单张查询图与库中特征比余弦相似度（越大越近），输出最相近身份 |

### 2.2 数据目录（输入，文件系统“库表”前身）

`--dataset` 指向的目录（默认 `./dataset`）约定如下；层次与 2.1 表一致，**表头三列**方便对照“放什么、训练怎么用”。（由于涉及人脸数据 已忽略未上传）

| 路径（相对 `dataset` 根） | 内容 | 说明 |
|--------------------------|------|------|
| `某人/` | 多幅人脸图像 | **子目录名 = 该人身份标签**（如 `张三/` → 以后 `label` 里出现 `张三`） |
| 该人文件夹内文件 | `*.jpg` / `*.png` 等 | 经 `list_image_files` 扫描，**多图**先各自编成 9×K 维，**再对该人做逐维平均** 得到一行原型 |
| `vedio` / `video` | 任意 | **排除**，不作为身份、不读图（`person_root_dirs`） |
| 根下直接放图 | 无 | **不支持**；必须**一人一个子文件夹** |
| 图像分辨率 | 任意 | 非 **1920×1080** 会先**缩放到该尺寸**再提特征（`TARGET_SIZE`） |

### 2.3 身份库（训练输出，NumPy 文件）

由 `train_bovw.py` 写入 `--out`（默认 `output/`），即检索用的 **已注册身份库**；`match_face.py` 与批量代码读同一组文件。**推理时 `k-visual` 与 `visual_vocab` 的 K 必须与训练时一致。**

| 文件 | 形状 / dtype | 行/列约定 | 在系统中的角色 |
|------|----------------|-----------|----------------|
| `label.npy` | 一维 `object`，长度 = 注册身份数 *N* | `label[i]` 为**第 *i* 人**的字符串，与 `features` **第 *i* 行**一一对应 | 人名表：把**行号**解释成**可读身份** |
| `features.npy` | `(*N*, 9×K)`，`float32`，默认 `(*N*, 900)`；每行 **L2=1** | 第 *i* 行 = 第 *i* 人原型（多图 L2-向量**平均**后再 **L2-单位化**） | **查表主体**：与**同为 L2-单位**的查询向量算 **余弦相似度**（点积） |
| `visual_vocab.npy` | *(K, 128)*，默认 **(100, 128)** | 行 = 词；列 = 128 维 SIFT 子空间中的聚类中心 | **公共词典**：训练一次固定；对**库图/查询图**做编码时**都必须**用同一 `centers` |

**三者关系（逻辑键）**：

| 关系 | 说明 |
|------|------|
| `len(label) == features.shape[0]` | 人名与特征行数严格同长 |
| `label[i]` ↔ `features[i, :]` | 第 *i* 个注册名 ↔ 第 *i* 行原型，检索时 `argmax` 余弦 行号再查 `label` |
| `visual_vocab` 与人数 | 与 *N* **无关**；K 个词为**全局**共享，不随人增减而变维（K 只由训练与 `--k-visual` 决定） |
| 查询图 | 不在 `label`/`features` 里；经同一 `encode_image_spatial_bow(..., centers)` 得 **9×K、L2=1** 的向量，再与 `features` 每行算**余弦相似度** |

**升级说明**：若曾用**全图 100 维**旧版，或曾得到过 **未在拼接后做 L2** 的 9×K `output/`，需**重新**运行 `train_bovw.py`，使 `visual_vocab` / `features` 与当前 `encode` 约定一致。

### 2.4 环境说明（Conda）

```bash
cd l3_BoVW
conda env create -f environment.yml
conda activate l3_bovw
```

依赖：**Python 3.11**、**NumPy**、**scikit-learn**、**OpenCV**（`conda-forge` 的 `opencv` 含 SIFT）。  
在 Cursor/VS Code 中若 `sklearn` 报“无法解析导入”，请将 **Python 解释器** 选为 **`l3_bovw` 环境**，与终端中 `conda activate` 一致。

**训练：**

```bash
conda activate l3_bovw
cd l3_BoVW
python train_bovw.py --dataset ./dataset --out ./output
```

**推理：**

```bash
python match_face.py /path/to/query.jpg
```

默认从 `./output/` 读取三个 `.npy`；可用 `--art_dir` 指定目录。可选：`--k-visual` 改每块直方图长度；`--max-train-samples N` 在描述子极多时对参与 K-Means 的样本子采样。

## 3. 训练视觉词典的算法：3×3 Dense-SIFT + K-Means 身份建库

- **空间划分**：将 **1920×1080** 图均匀划为 **3×3=9** 个区域，**行主序**（左→右、上→下）编号 0…8。
- **每区域内 Dense SIFT**：在子块内用 **5×5** 密集网格取关键点，每点 **128 维** SIFT 描述子（每块 25 个描述子，块间**独立**提特征，见 `REGION_GRID` / `DESCRIPTOR_DIM`）。
- **共享视觉词典（K-Means）**：对**训练集所有人、所有子块**上的全部 **128 维**描述子**合并**为矩阵，统一做一次 **K-Means，K=100**（可调 `--k-visual`），得到 **K 个聚类中心** `visual_vocab.npy`，**九块共用同一本词典**。
- **单图表示**：对每一子块，用词典做 **bag-of-words** 得 **K 维**直方图，并对该块直方图做 **L1 归一化**；9 个 **K 维**向量按行主序**拼接**为 **9×K 维**后，**再对整段拼接向量做 L2 单位化**（`bovw.l2_unit_vector`），使每幅图以 **L2=1** 的向量参与后续**相似度**计算。
- **身份级建库**：对每个人文件夹内多幅图在 **L2-单位化**后的 **9×K** 向量做 **逐维算术平均**，**再 L2-单位化**得到**一人一行**的 `features.npy`；`label.npy` 存对应人名。查询图同样经 `encode_image_spatial_bow` 得到 L2-单位查询向量，与 `features` 各行算 **余弦相似度**（`q·f_i`），**值越大越相似**。（单位向量下与最小**欧氏距离**的排序**一致**，仅量纲与解释不同。）

## 4. 迭代过程简述

### 4.1 方法迭代：从全图到 3×3 分块

- **初期**：在整幅图像上提特征、用 **单一 BoVW 直方图** 表示人脸（**不做空间分割**；对应早期 **100 维**、全图一袋子词的那一版，见后文「升级说明」）。实现简单，但**人脸对齐稍差或姿态变化**时，局部纹理统计混在一起，**检索/识别区分度不足，准确率不够理想**。
- **调整**：在保留 **Dense SIFT + K-Means 视觉词典** 框架的前提下，引入 **3×3 空间划分**：每个子区域单独统计词频再拼接，使表示中带有 **左右 / 上下 等空间结构**，与「五官大致位置稳定」的假设更一致，从而在相同度量（如**余弦相似度**；单位特征下与欧氏排序等价）下 **比全图单一直方图更稳、更准确**。当前代码即这一版，特征维为 **9×K**（默认 900）。

### 4.2 当前训练脚本的实现流程（`train_bovw.py`）

1. **遍历数据**：对每个人、每张图，按 3×3 子块收集 Dense SIFT，**拼成**全体描述子矩阵；可选 `--max-train-samples` 用 **固定随机种子 42** 子采样，避免描述子过多时 K-Means 过慢（见 `train_bovw.py` 中 `RNG`）。
2. **K-Means 训练词典**：在子采样或全量描述子集上拟合 **K-Means**（`n_init=10`，`max_iter=300`，`random_state=42`），一次得到聚类中心并保存为 `visual_vocab.npy`。
3. **回写身份特征**：用该词典对每人每图做空间 BoVW（**含拼接后 L2**），再**按人**对多图向量 **mean 聚合**并 **L2-单位化**原型，写入 `label.npy` 与 `features.npy`。
4. **可复现性**：K-Means 使用 `random_state=42`；子采样使用 `numpy.random.Generator(42)`，相同数据与参数下结果可复现。

批量推理示例（与 `match_face` 一致）：

```python
import numpy as np
from bovw import encode_image_spatial_bow, load_bgr

labels = np.load("output/label.npy", allow_pickle=True)
features = np.load("output/features.npy")
centers = np.load("output/visual_vocab.npy")
q = encode_image_spatial_bow(load_bgr("query.jpg"), centers)
sims = features.astype(np.float64) @ q.astype(np.float64)
j = int(np.argmax(sims))
print(labels[j])
```
