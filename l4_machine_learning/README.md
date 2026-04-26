# 基于 InsightFace 的人脸识别系统

使用 InsightFace 的 **RetinaFace（`det_10g`）** 检测 + 关键点对齐 + **ArcFace（`w600k_r50`）** 提取 512 维 embedding，构建注册库；识别阶段对查询图执行同流程并基于 **余弦相似度** 做 1:N 身份判定。默认使用 **GPU**。

---

## 1. 目录结构

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
├── models/                     # InsightFace 模型缓存（首次运行自动下载）
├── environment.yml             # conda 环境定义
├── fr_utils.py                 # 共享工具：建模型、选脸、对齐、L2 归一化
├── build_gallery.py            # 注册：检测 → 对齐 → 提特征 → 写库
└── recognize.py                # 识别：对输入图做 1:N 匹配
```

> 数据要求：`dataset/<身份名>/*.jpg`，每张图建议只含 1 张人脸；如有多脸将自动取置信度最高且面积最大的那张。

---

## 2. 环境安装

需要先装好 **miniconda/anaconda**，本机 NVIDIA 驱动 ≥ 525（支持 CUDA 12）。CUDA / cuDNN 运行库不必单独装，由 conda env 中的 `nvidia-*` pip wheel 提供。

```bash
cd /home/lyx/machine_visual/l4_machine_learning

conda env create -f environment.yml          # 1) 建环境，从源码编译 InsightFace
conda activate insightface-fr
bash setup_env.sh                            # 2) 写激活钩子（隔离 user-site + 注册 CUDA 库）
conda deactivate && conda activate insightface-fr   # 3) 重新激活让钩子生效
```

> **仅 CPU 运行**：编辑 `environment.yml`，把 `onnxruntime-gpu==1.23.2` 改为 `onnxruntime==1.18.0`，并删除整段 `nvidia-*` wheel；运行命令加 `--ctx-id -1`。`setup_env.sh` 仍然推荐执行（避免 `~/.local` 中其它包污染）。

校验安装：

```bash
python -c "
import insightface, numpy, onnxruntime as ort
from insightface.app import FaceAnalysis
print('insightface:', insightface.__version__, insightface.__file__)
print('numpy      :', numpy.__version__)
print('providers  :', ort.get_available_providers())
"
```

要求：

- `insightface.__file__` 在 `miniconda3/envs/insightface-fr/...` 下（**不是** `~/.local/...`）
- `providers` 中含 `CUDAExecutionProvider`
- `from insightface.app import FaceAnalysis` 不报 `numpy.dtype size changed`

执行 `build_gallery.py` 时，日志里如果看到 `Applied providers: ['CUDAExecutionProvider', ...]`，说明确实在 GPU 上跑。

---

## 3. 注册：构建人脸特征库

```bash
python build_gallery.py
```

完整可选参数：

| 参数 | 默认 | 说明 |
|------|------|------|
| `--dataset` | `./dataset` | 原始图片根目录，按身份分子文件夹 |
| `--aligned` | `./aligned_dataset` | 对齐结果输出目录 |
| `--embedding-dir` | `./embedding` | 特征库目录 |
| `--gallery-name` | `gallery.npz` | 特征库文件名 |
| `--model` | `buffalo_l` | InsightFace 模型包名（`buffalo_l` / `buffalo_s` 等） |
| `--model-root` | `./models` | 模型缓存目录 |
| `--ctx-id` | `0` | GPU 编号；`-1` 表示 CPU |
| `--det-size` | `640 640` | 检测输入分辨率 W H |
| `--det-thresh` | `0.5` | 检测置信度阈值 |

示例：

```bash
# GPU 0 上构建
python build_gallery.py --ctx-id 0

# 仅 CPU
python build_gallery.py --ctx-id -1

# 自定义路径与更高检测阈值
python build_gallery.py \
    --dataset ./dataset \
    --aligned ./aligned_dataset \
    --embedding-dir ./embedding \
    --det-thresh 0.6
```

运行结束后会得到：

- `aligned_dataset/<身份>/001.jpg ...`：112×112 对齐人脸
- `embedding/gallery.npz`：注册特征库（key：`embeddings` / `labels`）
- `embedding/gallery_meta.json`：每条记录对应的源图、对齐图、检测分数

---

## 4. 识别：1:N 身份匹配

输入可以是单张图、多张图、或包含图片的目录（递归）。

```bash
# 单张图
python recognize.py path/to/query.jpg

# 多张图
python recognize.py img1.jpg img2.png img3.jpeg

# 整个目录
python recognize.py path/to/folder/

# CPU 推理 + 自定义阈值与 Top-K
python recognize.py path/to/folder/ --ctx-id -1 --threshold 0.4 --topk 5
```

完整可选参数：

| 参数 | 默认 | 说明 |
|------|------|------|
| `inputs`（位置参数） | — | 一个或多个图片文件 / 目录 |
| `--gallery` | `./embedding/gallery.npz` | 注册库路径 |
| `--threshold` | `0.35` | 余弦相似度阈值，低于则判为 `unknown` |
| `--model` | `buffalo_l` | 与建库时保持一致 |
| `--model-root` | `./models` | 模型缓存目录 |
| `--ctx-id` | `0` | GPU 编号；`-1` 表示 CPU |
| `--det-size` | `640 640` | 检测分辨率 |
| `--det-thresh` | `0.5` | 检测置信度阈值 |
| `--topk` | `3` | 输出前 K 个相似度最高的候选 |

每张图输出一行 JSON，例如：

```json
{
  "image": "/path/to/query.jpg",
  "prediction": "lhp",
  "best_similarity": 0.7321,
  "threshold": 0.35,
  "top_matches": [
    {"identity": "lhp", "similarity": 0.7321},
    {"identity": "wmb", "similarity": 0.2154},
    {"identity": "zhh", "similarity": 0.1873}
  ]
}
```

若图中未检测到人脸，会输出 `[no face] <path>`，并跳过。

---

## 5. 阈值经验值

ArcFace + L2 归一化下，余弦相似度大致经验范围：

- `> 0.5`：很可能同一人
- `0.35 ~ 0.5`：可能同一人，建议人工复核
- `< 0.3`：通常不同人

请基于自己数据集调整 `--threshold`；可在已知正负样本上扫描 ROC 选最优值。

---

## 6. 常见问题

- **首次运行需要下载模型**：约 280MB，自动落到 `./models/models/buffalo_l/`。

- **`numpy.dtype size changed, may indicate binary incompatibility`**  
  典型原因：`~/.cache/pip/wheels/` 里缓存了一份针对其它 numpy 版本编译的 InsightFace wheel 被复用。  
  修复：
  ```bash
  pip cache remove insightface
  pip install --force-reinstall --no-cache-dir --no-binary insightface --no-deps "insightface==0.7.3"
  ```
  本仓库 `environment.yml` 已加 `--no-binary=insightface`，重建环境时会自动从源码编译。

- **`Applied providers: ['CPUExecutionProvider']` / `libcublasLt.so.12: cannot open shared object file`**  
  说明 `onnxruntime-gpu` 找不到 CUDA 12 / cuDNN 9 运行库。本项目通过 `nvidia-*` pip wheel 提供这些库，并由 `setup_env.sh` 写入的激活脚本把对应路径加进 `LD_LIBRARY_PATH`。如果忘了执行 `setup_env.sh`，会回落到 CPU。

- **`ModuleNotFoundError: No module named 'onnx'` 等链式缺失**  
  通常是用了 `pip install --no-deps`，没装齐依赖。直接 `conda env create -f environment.yml` 重建即可。

- **`~/.local/lib/python3.10/site-packages` 污染**  
  本项目通过 `setup_env.sh` 写入 `PYTHONNOUSERSITE=1` 的激活脚本来隔离 user-site。重激活环境后 `python -c "import sys; print('local' in '\n'.join(sys.path))"` 应输出 `False`。

- **新增/删除身份**：直接增删 `dataset/<身份>/` 后重新运行 `build_gallery.py`。

---

## 7. 一键最小流程示例

```bash
conda activate insightface-fr

python build_gallery.py --ctx-id 0
python recognize.py some_test_image.jpg --ctx-id 0
```
