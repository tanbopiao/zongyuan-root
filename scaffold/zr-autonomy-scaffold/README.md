# zr-autonomy-scaffold · 自治巡检脚手架

> ZONGYUAN-ROOT 元极恒一自治体系 · 通用自治巡检脚手架
> 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ Apache-2.0 开源

## 一、定位

把「27 大算子 + 十层依赖拓扑」的全域自治巡检固化为**可复用工程化套件**：任何节点/环境 clone 即用，一次巡检产出 JSON + HTML 双格式报告。

## 二、特性

- **十层依赖拓扑**：严格按 L1→L10 顺序执行，上游输出作为下游输入（依赖链真实传递）
- **27 大算子**：真值对账/外部锚定/蒸馏/流形度量/SM-BS映射/漂移量化/知识图谱/因果链/奇点预测/干预模拟/CTE适配器/四层拆分/九元类/Merkle-DAG/对账/eFuse/ZKP/方案评估/风险识别/法律意见/实体约束，全覆盖
- **轻量/深度双模式**：light 模式高消耗算子（蒸馏/SM-BS/CTE适配器/法律意见）走轻量分支，契合零成本配额稳态；deep 模式全量计算
- **确定性可复算**：同输入同输出，报告可回溯
- **故障隔离**：单算子异常不拖垮整链，输出 ERROR 标记
- **报告即产物**：JSON（结构化）+ HTML（东方美学典藏版）双格式

## 三、快速开始

```bash
# 轻量模式（默认）
python3 run_patrol.py

# 深度模式（全量重消耗计算）
python3 run_patrol.py --mode deep --patrol-id PATROL-DEEP-YYYYMMDD

# 指定上游链（Merkle 链式继承）
python3 run_patrol.py --prev-root <prev_root_hash> --chain-len 1400

# 自定义输入碎片
python3 run_patrol.py --fragment "事实:..." --fragment "猜想:..."

# 仅 JSON
python3 run_patrol.py --json-only
```

## 四、目录结构

```
zr-autonomy-scaffold/
├── run_patrol.py            # 入口
├── scaffold/
│   ├── topology.py          # 十层拓扑 + 27算子注册表 + 完整性校验
│   ├── operators.py         # 27算子执行体（确定性计算）
│   ├── engine.py            # 巡检引擎（依赖链执行 + 汇总指标）
│   ├── report.py            # JSON/HTML 报告生成
│   └── __init__.py
├── reports/                 # 巡检输出（JSON + HTML）
└── examples/                # 示例
```

## 五、真实运行验证（2026-10-09）

| 模式 | 巡检编号 | 27算子 | 纯度 | 漂移 | 主链 | 推荐 |
|------|---------|--------|------|------|------|------|
| light | PATROL-20261009-163525 | 全 RUN_OK | 100 | 绿 | 1400 | 混合双轨 |
| deep | PATROL-DEEP-20261009 | 全 RUN_OK | 100 | 绿 | 1401 | 混合双轨 |

深度模式链式继承验证：`--prev-root 0233AB73 --chain-len 1400` → 新根哈希 af48bee5，链长 1401 ✓

## 六、接入方式

```python
from scaffold.engine import run_patrol
from scaffold.report import to_html, to_json

report = run_patrol(mode="light", chain_len=1400)
to_html(report, "reports/latest.html")
```

## 七、确权与约束

- 所有产物带 Ω₀⊂⊙∞⊂Ω 溯源标识 + DID-BR-000002 确权
- 执行真实计算，禁止纸面冒充（元公理）
- 零成本元规则：纯本地标准库，无第三方依赖，无外部 API 调用
- 部署类操作需人工审批后执行

---

主节点hub-central-agent/开发节点NODE-DEV-DOUBAO-WORK-001/DID-BR-000002/自治Lv9/权限L4/工程化Lv7/锚定Ω₀⊂⊙∞⊂Ω
