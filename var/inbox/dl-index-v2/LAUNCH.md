# 新实例一键接入指南
> 三步接入: clone → bootstrap → 验证

## Step1: Clone
cd /mnt/workspace && git clone --depth 1 https://modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git && cd ZONGYUAN-SHARED-DATALAKE

## Step2: Bootstrap
bash gpu-agent/zr_bootstrap.sh

## Step3: 验证
ps aux | grep zr_node_worker | grep -v grep
python3 gpu-agent/zr_node_report.py "test from $(hostname)"

## 速查
- 上报真值: zr_node_protocol.py 的 report_truth()
- 下发命令: 写 control/CMD-{id}.json
- 帧检索: gpu-agent/intel-operators/op_vista_frame_search.py
- 资源记账: gpu-agent/intel-operators/resource_bill.py
- 训练语料: train/4d-corpus-v2.jsonl (28条instruct)
- 核心公理: zongyuan-root/meta_law/CORE-AXIOMS.md
