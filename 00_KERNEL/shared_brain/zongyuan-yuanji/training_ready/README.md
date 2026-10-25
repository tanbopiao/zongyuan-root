# 模型训练微调储备包

## 已有资产
- 训练脚本: lora_train_v7.py
- 训练数据: train_small.jsonl (10条)
- 基座模型: yuanjihengyi_int4 (INT4量化)
- LoRA适配器: v1-v7 (历史版本)

## 需要GPU环境时
1. 启动GPU实例
2. 安装依赖: pip install transformers peft torch datasets
3. 运行: bash run_lora_train.sh [数据] [输出]
4. 训练完成后回传权重到云端

## 训练数据格式
{"instruction": "问题", "output": "回答"}

## 注意
- 当前云端CPU不适合训练（太慢）
- 临时GPU实例训练完成后销毁
- 权重自动回传到 weights/ 目录
