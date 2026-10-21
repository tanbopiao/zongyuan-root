#!/usr/bin/env bash
set -e
echo "[1/2] 装 torch-cpu"
python3 -m pip install -q torch --index-url https://download.pytorch.org/whl/cpu 2>&1 | tail -1 || true
echo "[2/2] 装 transformers/bnb/psutil/numpy/pyyaml"
python3 -m pip install -q transformers bitsandbytes psutil pyyaml numpy 2>&1 | tail -1 || true
echo "=== 版本 ==="
python3 -c "import torch,transformers,psutil,yaml,numpy;print(\"torch\",torch.__version__);print(\"transformers\",transformers.__version__);print(\"cpu_threads\",torch.get_num_threads())"
