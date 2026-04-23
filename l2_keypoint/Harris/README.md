# Harris 角点检测与匹配实验

## 1. 主要工作

本工程完成以下任务：

- 对输入图像进行 Harris 角点检测；
- 将图像 A 变换得到图像 B（旋转、平移、透视、模糊）；
- 比较两种相似性匹配方式的效果，并将匹配上的角点连接可视化：
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

- `harris_detector.py`  
Harris 角点检测与可视化绘制，输出角点坐标和带角点标注图。
- `image_transformer.py`  
负责图像变换：旋转、平移、透视映射、高斯模糊，输入 A 输出 B。
- `match_and_stitch.py`  
采用 `ratio + mutual` 进行角点匹配；将 A、B 拼接并连接匹配角点。
- `match_and_stitch_ransac.py`  
采用 `ratio + RANSAC` 进行匹配内点筛选；将 A、B 拼接并连接 RANSAC 内点匹配。

## 4. 怎么运行工程

在 `Harris` 目录下执行：

```bash
# 方式一：ratio + mutual
python3 match_and_stitch.py ../picture/cat1.jpg --result-dir result -o result/final_match.png

# 方式二：ratio + RANSAC
python3 match_and_stitch_ransac.py ../picture/cat1.jpg --result-dir result -o result/final_ransac.png
```

运行后会在 `result` 目录生成：

- 角点图：`a1_corners*.png`、`b1_corners*.png`
- 拼接匹配图：`final_match.png` 或 `final_ransac.png`

常用参数（两种脚本基本一致）：

- 变换参数：`--angle` `--tx` `--ty` `--perspective` `--blur-ksize` `--blur-sigma`
- Harris 参数：`--max-corners` `--quality-level` `--min-distance` `--block-size` `--harris-k`
- 匹配参数：`--patch-radius` `--ratio`
- RANSAC 额外参数：`--ransac-thresh`

## 5. 实验数据记录

测试图像：`../picture/building.png`


| 运行方式           | 命令                                                                                                          | 角点数 A | 角点数 B | 初始匹配数 | RANSAC 内点数 | 最终连线数 |
| -------------- | ----------------------------------------------------------------------------------------------------------- | ----- | ----- | ----- | ---------- | ----- |
| ratio + RANSAC | `python3 match_and_stitch_ransac.py ../picture/building.png --result-dir result -o result/final_ransac.png` | 812   | 668   | 31    | 19         | 19    |
| ratio + mutual | `python3 match_and_stitch.py ../picture/building.png --result-dir result -o result/final_match.png`         | 812   | 668   | -     | -          | 19    |


## 6. 总结

本次实验使用 Harris 角点检测并对比了两种匹配策略。在 `building.png` 上，两种方法最终连线数相同，说明在该组参数与图像条件下，基础匹配已经较稳定；`ratio + RANSAC` 额外提供了几何一致性约束，能显式给出“初始匹配→内点”的筛选过程（31 → 19），可解释性更强，也更适合后续扩展到视角变化更大的场景。
但是很明显，使用直方图做相似性匹配时匹配了错误的角点，出现了交叉连线；但是ransac匹配基本正确，精确率明显大于前者。