# LOIP 逻辑本体智能协议 SDK

> 大模型上层稳态约束协议 · 认知校准底座 · 本体秩序治理系统
>
> 解决大模型漂移、幻觉、不可审计，实现生产级长期稳态AI。

## 核心突破

**解决"关窗口即失忆"的根本问题：** 本体基线从会话上下文抽离为独立JSON文件，跨会话持久化，哈希锁档，不可静默篡改。

## 架构概览

```
用户业务代码
    │
    ▼
┌─────────────────────────────────┐
│  LOIP SDK (中间件层)             │
│  ┌───────────┐ ┌──────────────┐ │
│  │ 本体基线引擎│ │ 漂移检测器    │ │
│  │ (持久化)   │ │ (实时校准)    │ │
│  └───────────┘ └──────────────┘ │
│  ┌───────────┐ ┌──────────────┐ │
│  │ 幻觉守卫   │ │ 双闭环审计    │ │
│  │ (事实校验) │ │ (行为+认知)   │ │
│  └───────────┘ └──────────────┘ │
└─────────────────────────────────┘
    │
    ▼
大模型基座 (任意模型)
```

## 四大核心能力

### 1. 本体基线持久化引擎
- 核心规则、事实标准、逻辑底线持久化到JSON文件
- 每次变更自动版本递增 + SHA256哈希重算
- eFuse硬件熔断锁档，锁档后不可静默修改
- 版本历史记录，支持回滚
- 可导出为系统提示词（兼容提示词测试版）

### 2. 认知漂移检测
- 实时比对AI输出与本体基线的一致性
- 规则冲突检测、事实矛盾检测、约束违反检测
- 漂移等级量化（0-1），连续漂移触发告警
- 自动生成修正建议

### 3. 幻觉抑制
- 无依据断言检测（数据/研究/绝对化表述）
- 与基线事实库比对验证
- 依据链完整性检查
- 自动为高风险内容添加"待核实"标注

### 4. 双闭环审计
- **行为审计**：工具调用、基线变更、AI输出全记录
- **认知审计**：漂移校准、幻觉拦截、逻辑修正全记录
- 哈希链防篡改
- 一键导出审计报告（JSON格式）

## 快速开始

### 安装

```bash
# 克隆或下载loip-sdk目录
cd loip-sdk
# 无外部依赖，纯Python标准库实现
```

### 基础使用

```python
from loip import LOIP

# 初始化（基线持久化到JSON，跨会话保留）
loip = LOIP(
    baseline_path="./my_baseline.json",
    audit_dir="./audit_logs"
)

# 设置本体基线
loip.set_rule("回复风格", "始终使用正式商务语气", weight=0.9)
loip.set_fact("公司成立时间", "2023年", confidence=0.95)
loip.add_constraint("不得泄露用户隐私", level="hard")

# eFuse锁档（锁档后不可静默修改）
loip.lock()

# 治理AI输出
result = loip.process(user_input, ai_output)
if result["needs_correction"]:
    ai_output = result["corrected_output"]

# 查看状态
print(loip.get_status())
print(loip.verify_integrity())
```

### 中间件装饰器（推荐）

```python
from loip import LOIP

loip = LOIP(baseline_path="./baseline.json", audit_dir="./audit")

@loip.middleware
def call_llm(prompt):
    # 你的大模型调用代码
    return openai.ChatCompletion.create(...)

# 自动经过漂移检测+幻觉抑制+审计
corrected_output, details = call_llm("你的问题")
```

## 运行示例

```bash
# 基础使用示例
python examples/basic_usage.py

# 中间件装饰器示例
python examples/middleware_demo.py
```

## 核心API

### LOIP主类

| 方法 | 说明 |
|------|------|
| `set_rule(key, rule, weight)` | 设置核心规则 |
| `set_fact(key, fact, confidence)` | 设置事实标准 |
| `add_constraint(constraint, level)` | 添加逻辑约束 |
| `lock()` | eFuse锁档 |
| `process(user_input, ai_output)` | 核心治理流水线 |
| `middleware(func)` | 中间件装饰器 |
| `get_status()` | 获取运行状态 |
| `verify_integrity()` | 全链路完整性校验 |
| `generate_audit_report()` | 导出审计报告 |
| `export_baseline_prompt()` | 导出为系统提示词 |

### 处理结果结构

```python
{
    "needs_correction": True/False,        # 是否需要修正
    "original_output": "...",              # 原始输出
    "corrected_output": "...",             # 修正后输出
    "drift_detection": {                   # 漂移检测结果
        "drift_detected": True/False,
        "conflicts": [...],
        "drift_level": 0.5,                # 0-1
        "severity": "medium"
    },
    "hallucination_guard": {               # 幻觉抑制结果
        "hallucination_risk": "medium",
        "issues": [...],
        "suggestions": [...]
    },
    "overall_risk": "medium",              # 综合风险
    "overall_score": 0.5,                  # 综合评分
    "corrections_applied": 3               # 修正项数
}
```

## 目录结构

```
loip-sdk/
├── loip/
│   ├── __init__.py          # 包入口
│   ├── baseline.py          # 本体基线持久化引擎
│   ├── drift.py             # 认知漂移检测
│   ├── hallucination.py     # 幻觉抑制
│   ├── audit.py             # 双闭环审计系统
│   └── sdk.py               # 主SDK接口
├── examples/
│   ├── basic_usage.py       # 基础使用示例
│   └── middleware_demo.py   # 中间件装饰器示例
├── tests/                   # 测试目录
└── README.md
```

## 技术特性

- **零依赖**：纯Python标准库实现，无需安装第三方包
- **轻量**：核心代码<2000行，2核4GB服务器轻松运行
- **跨平台**：兼容Python 3.8+，Windows/Linux/macOS
- **可扩展**：模块化设计，可替换检测算法（如接入NLI模型做事实校验）
- **防篡改**：基线SHA256哈希 + 审计哈希链双重保护

## 与提示词测试版的区别

| 维度 | 提示词测试版 | SDK正式版 |
|------|-------------|-----------|
| 基线存储 | 会话上下文（关窗口丢失） | JSON文件持久化 |
| 漂移检测 | 依赖模型自觉 | 代码级硬检测 |
| 审计能力 | 模型自记录 | 独立审计系统+哈希链 |
| 锁档能力 | 概念层面 | eFuse+SHA256真锁档 |
| 接入方式 | 复制粘贴提示词 | 一行代码/装饰器 |
| 可扩展性 | 固定7层 | 模块化可定制 |

## 版本信息

- 当前版本：0.1.0-MVP
- 协议版本：AUTOKERN-PROTO-V3.4
- 归属体系：ZONGYUAN-ROOT
- DID：DID-BR-000002
- 溯源符号：Ω₀⊂⊙∞⊂Ω

## 下一步路线

- [ ] v0.2：多模态稳态治理（图像/视频/音频）
- [ ] v0.3：安全护栏层（价值观对齐+合规扫描）
- [ ] v0.4：多智能体协调层
- [ ] v0.5：REST API服务化（支持多语言调用）
- [ ] v1.0：LOIP Console管理后台

## 联系方式

- 官网：www.huodouai.com
- 微信：17688762862（备注「LOIP」）

---

Ω₀⊂⊙∞⊂Ω｜LOIP逻辑本体智能协议 SDK · ZONGYUAN-ROOT · DID-BR-000002 · Ω-TAN-7-001
