# Harris 角点与描述子匹配示例

本目录演示：由 **A** 经仿射（旋转、平移、模糊）得到 **B**；对 **A、B 各自独立**做 Harris 角点检测；在角点邻域构造**强度直方图 + 梯度方向直方图**描述子；用 **Lowe 距离比**与可选**互最近邻**做相似度匹配；左右拼接并连线可视化。

## 文件说明

| 文件 | 作用 |
|------|------|
| `harris_corner.py` | **角点检测**：`goodFeaturesToTrack` + Harris 响应，`cornerSubPix` 细化；`affine_apply_xy` 供其它实验使用。 |
| `image_transform.py` | **合成 B**：从 A 得到同尺寸 B 及 A→B 仿射矩阵（本管线匹配**不**使用该矩阵）。 |
| `corner_descriptors.py` | **描述子**：每个角点取正方形邻域，拼接归一化灰度强度直方图与梯度方向（0~π）直方图，再 L2 归一化。 |
| `match_corners.py` | **匹配**：`match_by_descriptor_similarity`（距离比 + 可选互最近邻）；另保留 `match_by_affine_prediction`（仿射预测匹配，供对照）。 |
| `run_harris_match.py` | **入口**：串联检测、描述子、匹配与可视化。 |
| `requirements.txt` | `numpy`、`opencv-python`。 |

## 运行方式

```bash
cd Harris
python run_harris_match.py              # 无参：内置棋盘图
python run_harris_match.py /path/to/img.png -o out.png
```

常用参数：`--seed`、`--ratio`、`--patch-radius`、`--no-mutual`、`--result-dir`。

**Harris 角点**：`--quality-level`（越小角点越多，可试 `0.002`～`0.005` 看面部弱纹理）、`--min-distance`（越小越密）、`--max-corners`、`--block-size`。

## 说明

匹配**不**使用合成时的真值仿射，仅靠邻域统计相似度；旋转较大时描述子对齐会变差，可适当增大 `--patch-radius` 或放宽 `--ratio` 做实验对比。

人像上角点多集中在毛发、镜框等强边缘处、面颊相对少，是 Harris 对「角状结构」的定义所致；单靠调参无法让面部与头发「均匀」分布，若需要面部关键点应使用人脸检测/关键点模型。
