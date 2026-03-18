# 高频/低频融合（A 高频 + B 低频）

输入两张图片（分辨率可不同），先统一到同一分辨率，然后：

- A 取 **高频**：\(A_{high} = A - G_{\sigma_{high}}(A)\)
- B 取 **低频**：\(B_{low} = G_{\sigma_{low}}(B)\)
- 融合输出：\(Out = B_{low} + gain \cdot A_{high}\)

其中 \(G_{\sigma}(\cdot)\) 是高斯模糊（低通）。

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
  --out out/fused.png \
  --resize auto \
  --sigma-low 4 \
  --sigma-high 4 \
  --high-gain 1.0
```

### 参数建议

- `--sigma-low`: 越大越“只保留低频”（更平滑）。常用 4~12
- `--sigma-high`: 定义“高频”的尺度。越小保留越细的纹理。常用 1~4
- `--high-gain`: 高频叠加强度，过大可能出现过锐/溢出。常用 0.7~1.5

## 说明

- 默认 `--resize auto` 会选择两张图中 **面积更大** 的那张作为目标分辨率，然后把另一张缩放过去。
- 目前按 **彩色 BGR 三通道** 处理；如输入有 alpha 通道会被忽略。
