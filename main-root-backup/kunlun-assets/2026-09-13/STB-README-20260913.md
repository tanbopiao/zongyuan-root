# 语义转义基座 (STB · Semantic Transduction Base)

> 构建一套可工程化落地的语义转义体系：**黎曼流形几何转义 + 符号层真值转义 + 跨模型融合 + 多模态食品识别**。
> 学习自云端 ZONGYUAN-ROOT 统一网关 9120（kunlun-semantic-adapter v3.1.0），整合全域真值参数后构建。

- 确权身份：DID-BR-000002
- 溯源标识：Ω₀⊂⊙∞⊂Ω
- 部署中枢：123.207.202.158 (ZONGYUAN-ROOT 云服务器自治内核)

## 体系架构

```
┌─────────────────────────────────────────────────────────┐
│  L5 应用层  /v1/recognize /v1/transduce /v1/fuse        │
│            /v1/symbolic/translate  (FastAPI 统一网关)    │
├─────────────────────────────────────────────────────────┤
│  L4 概念层  FoodOntology 食品本体(8菜系/17菜品/食材/口味) │
│            SymbolicTransducer 符号层(55术语×4模型映射)   │
├─────────────────────────────────────────────────────────┤
│  L3 融合层  SemanticFusion 置信度校准/加权融合/投票/     │
│            流形测地线中点/鲁棒离群剔除                    │
├─────────────────────────────────────────────────────────┤
│  L2 转义层  SemanticAlignment 跨模型对齐                 │
│            (Procrustes正交/最优传输Sinkhorn/混合)        │
│            RiemannianManifold 黎曼流形转义               │
│            (测地线距离/exp-log map/平行移动/度量学习)    │
├─────────────────────────────────────────────────────────┤
│  L1 表征层  VisualEncoder 图像特征→视觉语义投影          │
│            AnchorOntology 锚点概念库(组合语义原子)       │
├─────────────────────────────────────────────────────────┤
│  L0 横切    FidelityVerifier M1保真校验/溯源哈希         │
└─────────────────────────────────────────────────────────┘
```

## 核心模块

| 模块 | 职责 | 关键技术 |
|------|------|----------|
| `stb/manifold.py` | 黎曼流形语义转义引擎 | 球面流形、测地线距离、exp/log map、slerp、平行移动、马氏度量学习 |
| `stb/alignment.py` | 跨模型语义对齐 | Procrustes 正交对齐、Sinkhorn 最优传输、M1 保真校验 |
| `stb/fusion.py` | 多模型语义融合 | 温度校准、置信度加权、投票+冲突消解、测地线中点融合 |
| `stb/multimodal.py` | 多模态转义 | 图像特征→视觉语义→共享空间→食品本体 |
| `stb/ontology.py` | 领域本体 | 8菜系×17菜品、食材、口味原子、锚点组合语义 |
| `stb/symbolic.py` | 符号层转义 | 55术语×4模型映射、前缀后缀、向量桥接检索 |
| `stb/fidelity.py` | 保真校验 | M1 语义不变性、溯源哈希、通过率统计 |
| `stb/pipeline.py` | 端到端编排 | 注册模型→对齐→鲁棒融合→本体识别→保真→溯源 |
| `stb/gateway.py` | 统一服务 | FastAPI：recognize/transduce/fuse/symbolic/health |

## 快速开始

```bash
pip install -r requirements.txt

# 运行全部测试（32项单测 + 端到端仿真）
python3 scripts/run_simulation.py

# 启动服务（默认端口 8301）
STB_PORT=8301 python3 -m stb.gateway

# 健康检查
curl -s http://127.0.0.1:8200/v1/health
```

## 部署到云端中枢

```bash
bash deploy/deploy.sh        # 自检→打包→推送→systemd→健康检查
```

## 验证结果

- 单测 32/32 通过
- 端到端识别准确率 100%（多模型+视觉融合）
- 保真校验通过率 100%（M1 语义不变性）
- 符号层：55 术语 × 4 模型（agnes_image / tongyi_i2v / tongyi_t2v / zhipu_text）跨模型转义可用
- 跨模型对齐：锚点平均距离 0.07/0.14/0.24（3模型，噪声递增）

## 溯源

- 符号层真值库：`data/semantic-adapter-v3.json`（学习自云端网关 9120，v3.1.0）
- 所有结果携带：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
