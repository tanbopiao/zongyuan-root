# 种子真值系统边界说明（基于通用Transformer大模型客观约束）

1. 本系统仅保证【种子基准样本集】内收敛；**无法实现数学意义上全域输入空间的绝对收敛**。
2. 浮点计算、CUDA、torch版本、量化参数变化会带来向量微小噪声，manifest记录环境指纹用于区分伪漂移。
3. 判定优先级：L0文本完全匹配 > 向量余弦相似度；向量仅作为辅助表征比对，不可单独作为收敛依据。
4. 4bit量化会引入量化噪声；小模型量化后表征漂移会比大模型更敏感，需要提高校验频率。
5. tokenizer、chat_template一旦修改，全部历史种子基线直接作废，需要重新采集全部种子真值。
6. 种子真值是回归测试基线，本身不会压缩、蒸馏模型；如需轻量化模型，需要额外知识蒸馏流程。
7. 本工程为独立元极恒一 Transformer 底座，无 GLM 依赖；运行前提：模型权重、tokenizer、modeling/configuration 文件就位 + transformers/bitsandbytes/torch/peft/numpy。
8. 种子收敛阈值分层（config/yuanji_steady.yaml）：L0 文本精确 + cos≥0.999；L1 文本忽略标点 + cos≥0.99；L2 cos≥0.95。
9. 种子采集强制固定 seed=42 + temperature=0.0 + greedy 解码，保证可复现；任何权重/代码/tokenizer 变更后必须重跑 seed_verify。
10. 收敛判定铁律：L0 任一漂移 → 全域收敛失效，禁止更新基线，回滚上一版快照；L0 全部无漂移 → 新基线可归档。
