import sys; sys.path.insert(0, "/opt/ZONGYUAN-ROOT"); from core.truth_loader import truth_loader
"""
LOIP v0.4 快速开始示例
5行代码接入稳态AI：大模型生成 + LOIP稳态治理 一键完成
"""
from loip import LOIP

# 方式1：从配置文件一键创建（推荐）
loip = LOIP.from_config("./config.example.json")

# 方式2：手动配置
# loip = LOIP(baseline_path="./baseline.json")
# loip.set_llm({"preset": "doubao-pro", "api_key": "你的API密钥"})

# 设置基线规则
loip.set_rule("风格", "正式商务语气，不使用网络流行语", weight=0.9)
loip.set_fact("公司成立时间", "2023年", confidence=0.95)

# 一键调用：大模型生成 + LOIP治理
result = loip.chat("介绍一下你们公司")

# 输出结果
print("=== 原始输出 ===")
print(result["raw_output"][:200])
print("\n=== 治理后输出 ===")
print(result["corrected_output"][:200])
print("\n=== 治理指标 ===")
g = result["governance"]
print(f"风险等级: {g['overall_risk']}")
print(f"漂移冲突: {g['drift_conflicts']}")
print(f"幻觉问题: {g['hallucination_issues']}")
print(f"安全威胁: {g['security_threats']}")
print(f"修正项数: {g['corrections_applied']}")
print(f"是否阻断: {g['blocked']}")

# 支持的模型预设
from loip.adapters import get_supported_models
print("\n=== 支持的模型预设 ===")
for name, info in get_supported_models().items():
    print(f"  {name}: {info['model']}")
