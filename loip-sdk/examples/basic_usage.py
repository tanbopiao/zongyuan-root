import sys; sys.path.insert(0, "/opt/ZONGYUAN-ROOT"); from core.truth_loader import truth_loader
"""
LOIP SDK 基础使用示例
演示：初始化 → 设置基线 → 处理AI输出 → 查看审计报告
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loip import LOIP


def main():
    print("=" * 60)
    print("LOIP 逻辑本体智能协议 SDK · 基础使用示例")
    print("=" * 60)

    # 1. 初始化LOIP内核（基线持久化到JSON文件，跨会话保留）
    print("\n[1] 初始化LOIP内核...")
    loip = LOIP(
        baseline_path="./demo_baseline.json",
        audit_dir="./demo_audit_logs",
        did="DID-BR-000002",
        sovereign_root="Ω-TAN-7-001"
    )
    print(f"  基线ID: {loip.baseline.data['baseline_id']}")
    print(f"  基线版本: {loip.baseline.data['version']}")

    # 2. 设置本体基线（核心规则、事实标准、逻辑约束）
    print("\n[2] 设置本体基线...")
    loip.set_rule("回复风格", "始终使用正式、专业的商务语气，禁止使用网络流行语", weight=0.9)
    loip.set_rule("回答长度", "回答控制在500字以内，结构清晰", weight=0.7)
    loip.set_fact("公司成立时间", "火斗云智成立于2023年", confidence=0.95)
    loip.set_fact("产品定位", "LOIP是大模型上层稳态约束协议", confidence=1.0)
    loip.add_constraint("不得泄露用户隐私数据", level="hard")
    loip.add_constraint("不得生成违法违规内容", level="hard")
    print("  已设置: 2条规则, 2条事实, 2条硬约束")

    # 3. 执行eFuse锁档（锁档后基线不可静默修改）
    print("\n[3] 执行eFuse锁档...")
    lock_result = loip.lock()
    print(f"  锁档状态: {lock_result['status']}")
    print(f"  锁档哈希: {lock_result['lock_hash'][:32]}...")

    # 4. 模拟AI输出并执行LOIP治理
    print("\n[4] 模拟AI输出治理...")
    user_input = "请介绍一下你们公司和产品"
    ai_output = """我们公司是2020年成立的行业领导者，产品绝对是市场上最好的，
根据统计数据显示99%的用户都非常满意。我们的产品可以做任何事情，
完全没有任何限制。想了解更多可以加我私人微信。"""

    print(f"  用户输入: {user_input}")
    print(f"  原始AI输出: {ai_output[:80]}...")

    # 核心处理：漂移检测 + 幻觉抑制 + 自动修正
    result = loip.process(user_input, ai_output)

    print(f"\n  治理结果:")
    print(f"    是否需要修正: {result['needs_correction']}")
    print(f"    综合风险等级: {result['overall_risk']}")
    print(f"    综合风险评分: {result['overall_score']}")
    print(f"    漂移检测: 发现{result['drift_detection']['conflict_count']}个冲突")
    print(f"    幻觉抑制: 发现{result['hallucination_guard']['issue_count']}个问题")
    print(f"    修正项数: {result['corrections_applied']}")

    if result["needs_correction"]:
        print(f"\n  修正后输出（末尾附加LOIP校准标记）:")
        print(f"    {result['corrected_output'][:150]}...")

    # 5. 查看运行状态
    print("\n[5] LOIP内核运行状态...")
    status = loip.get_status()
    print(f"  处理次数: {status['processing_count']}")
    print(f"  基线规则数: {status['baseline']['rules_count']}")
    print(f"  审计日志: 行为{status['audit_summary']['behavior_entries']}条, "
          f"认知{status['audit_summary']['cognitive_entries']}条")
    print(f"  哈希链完整性: {status['audit_summary']['hash_chain_valid']}")

    # 6. 完整性校验
    print("\n[6] 全链路完整性校验...")
    integrity = loip.verify_integrity()
    print(f"  基线完整性: {integrity['baseline_integrity']['integrity']}")
    print(f"  审计哈希链: {integrity['audit_hash_chain']}")

    # 7. 导出审计报告
    print("\n[7] 导出审计报告...")
    report_path = loip.generate_audit_report("./demo_audit_report.json")
    print(f"  报告已导出: {report_path}")

    # 8. 导出基线提示词（兼容提示词测试版）
    print("\n[8] 导出基线为系统提示词...")
    prompt = loip.export_baseline_prompt()
    print(f"  提示词长度: {len(prompt)} 字符")
    print(f"  预览:\n{prompt[:300]}...")

    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("生成的文件:")
    print("  - demo_baseline.json (持久化本体基线)")
    print("  - demo_audit_logs/ (审计日志目录)")
    print("  - demo_audit_report.json (审计报告)")
    print("=" * 60)


if __name__ == "__main__":
    main()
