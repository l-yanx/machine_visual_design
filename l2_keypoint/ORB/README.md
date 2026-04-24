# ORB 关键点检测与匹配实验

## 1. 主要工作

本工程完成以下任务：

- 对输入图像进行 ORB 关键点检测；
- 将图像 A 变换得到图像 B（旋转、平移、透视、模糊）；
- 比较两种相似性匹配方式的效果，并将匹配上的关键点连接可视化：
  - 方式一：`ratio + mutual`（基础相似度匹配）
  - 方式二：`ratio + RANSAC`（几何一致性过滤）

## 2. 必要的包

依赖见 `requirements.txt`：

- `numpy>=1.20`
- `opencv-python>=4.5`

建议 Python 3 环境运行。

安装方式：

```bash
pip install -r requirements.txt
```

## 3. 每个 py 文件作用

- `orb_detector.py`  
  ORB 关键点检测与可视化绘制，输出关键点坐标和 ORB 描述子。

- `image_transformer.py`  
  负责图像变换：旋转、平移、透视映射、高斯模糊，输入 A 输出 B。

- `match_and_stitch.py`  
  采用 `ratio + mutual` 进行 ORB 描述子匹配；将 A、B 拼接并连接匹配关键点。

- `match_and_stitch_ransac.py`  
  采用 `ratio + RANSAC` 进行内点筛选；将 A、B 拼接并连接 RANSAC 内点匹配。

## 4. 怎么运行工程

在 `ORB` 目录下执行：

```bash
# 方式一：ratio + mutual
python3 match_and_stitch.py ../picture/building.png --result-dir result -o result/final_orb.png

# 方式二：ratio + RANSAC
python3 match_and_stitch_ransac.py ../picture/building.png --result-dir result -o result/final_orb_ransac.png
```

运行后会在 `result` 目录生成：

- 关键点图：`a1_orb*.png`、`b1_orb*.png`
- 拼接匹配图：`final_orb.png` 或 `final_orb_ransac.png`

常用参数（两种脚本基本一致）：

- 变换参数：`--angle` `--tx` `--ty` `--perspective` `--blur-ksize` `--blur-sigma`
- ORB 参数：`--nfeatures` `--scale-factor` `--nlevels` `--fast-threshold`
- 匹配参数：`--ratio`
- RANSAC 额外参数：`--ransac-thresh`

## 5. 实验数据记录

测试图像：`../picture/building.png`

| 运行方式 | 命令 | 关键点数 A | 关键点数 B | 初始匹配数 | RANSAC 内点数 | 最终连线数 |
|---|---|---:|---:|---:|---:|---:|
| ratio + RANSAC | `python3 match_and_stitch_ransac.py ../picture/building.png --result-dir result -o result/final_orb_ransac.png` | 1200 | 1200 | 657 | 631 | 631 |
| ratio + mutual | `python3 match_and_stitch.py ../picture/building.png --result-dir result -o result/final_orb.png` | 1200 | 1200 | - | - | 538 |

## 6. 总结

本次 ORB 实验中，在同一组 `building.png` 数据上，`ratio + RANSAC` 保留的有效连线数（631）高于 `ratio + mutual`（538），且经过几何一致性约束后内点含义更明确。整体看，ORB 在该场景下关键点数量充足，匹配结果稳定，适合后续与 Harris 方案做横向对比分析。
但是明显`ratio + mutual`相似性匹配方式有错误匹配，连线出现交叉；`ratio + RANSAC` 并没有明显错误。