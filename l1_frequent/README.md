# 高频/低频融合（A 高频 + B 低频）

## 文件架构
- fuse_high_low.py 主程序
- picture 处理数据与结果库
- request 主要依赖
- __pycache__
- readme.md

输入两张图片（分辨率可不同），先统一到同一分辨率，然后在**频域**里做滤波与融合：

- 对 A、B 分别做 2D FFT，得到频谱
- 用**同一个半径 \(r\)** 构造圆形低通掩码：
  - B 经过低通 → 得到 \(B_\text{low}(r)\)（只保留半径 \(r\) 内的低频）
  - A 经过低通后再相减 → 得到 \(A_\text{high}(r) = A - A_\text{low}(r)\)
- 融合输出：\(\text{Out} = b\_\text{gain} \cdot B_\text{low}(r) + \text{high\_gain} \cdot A_\text{high}(r)\)

最后再做反 FFT 回到空域并裁剪到 \([0,1]\)。

## 安装

```bash
conda create -n machinevisual_l1 python=3.10 -y
conda activate machinevisual_l1
pip install -r requirements.txt
```

## 使用

```bash
python fuse_high_low.py \
  --a path/to/a.jpg \
  --b path/to/b.jpg \
  --out out/ \
  --resize auto \
  --radius 40 \
  --high-gain 1.0 \
  --b-gain 1.0
```

当 `--out` 指向目录（或不带扩展名）时，会在该目录下输出：
`out_<radius>_<high-gain>_<b-gain>.jpg`

### 参数

- `--radius`: 频域圆形低通半径（单位：像素）。越大，B 的结构/中频保留越多。
- `--high-gain`: 对 A 的高频部分的叠加强度。越大，A 的细节越明显。
- `--b-gain`: 对 B 的低频基底的权重。\<1 会压低 B，让 A 更突出。

## 说明

- 低频与高频都在**频域**完成：先 FFT，再乘以圆形掩码，然后 IFFT。

## 实际效果
- 实际测试效果在picture内，g1 g2采用空域滤波后相加，效果远不如g3中在频域里的效果明显。
- 效果证明低通图像能量需要远小于高通图像能量时，融合后图片高频信息才明显。推测主要原因在于高通图像丢弃了大量的颜色等大面积视觉信息，所以需要处理后保留更多的能量。同时低通图像保留了大量的颜色等信息，足以让人注意到。最佳一组数据为g3/out_30_5_1.jpg
