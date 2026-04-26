#!/usr/bin/env bash
# 在已激活的 insightface-fr 环境中执行：写入两个激活钩子脚本。
# 1) 禁用 ~/.local user-site，避免与系统全局 numpy/insightface 冲突
# 2) 把 nvidia-* wheel 的 lib 路径加入 LD_LIBRARY_PATH，让 onnxruntime-gpu 能找到 CUDA12/cuDNN9
set -euo pipefail

if [[ -z "${CONDA_PREFIX:-}" ]]; then
  echo "请先 conda activate insightface-fr 再运行此脚本" >&2
  exit 1
fi

mkdir -p "$CONDA_PREFIX/etc/conda/activate.d"

cat > "$CONDA_PREFIX/etc/conda/activate.d/no_user_site.sh" <<'EOF'
export PYTHONNOUSERSITE=1
EOF

cat > "$CONDA_PREFIX/etc/conda/activate.d/cuda_libs.sh" <<'EOF'
NV_BASE="$CONDA_PREFIX/lib/python3.10/site-packages/nvidia"
for sub in cublas cudnn cuda_runtime cuda_nvrtc cufft curand nvjitlink; do
  d="$NV_BASE/$sub/lib"
  [ -d "$d" ] && export LD_LIBRARY_PATH="$d:${LD_LIBRARY_PATH:-}"
done
EOF

echo "Wrote:"
ls -1 "$CONDA_PREFIX/etc/conda/activate.d/"
echo ""
echo "请重新激活以生效:"
echo "  conda deactivate && conda activate insightface-fr"
