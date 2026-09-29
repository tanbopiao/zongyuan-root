import sys; sys.path.insert(0, "/opt/ZONGYUAN-ROOT"); from core.truth_loader import truth_loader
"""
LOIP SDK 中间件装饰器示例
演示如何用@loip.middleware装饰器包裹大模型调用，自动注入稳态治理。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loip import LOIP


# 模拟一个大模型调用函数（实际使用时替换为真实API调用）
def mock_llm_call(prompt: str) -> str:
    """模拟大模型返回（包含漂移和幻觉问题）"""
    return f"关于'{prompt}'，根据最新研究数据显示，这个领域绝对是未来的方向，" \
           f"百分之百的专家都认同这一点，我们的产品是市场上唯一的解决方案。"


def main():
    print("=" * 60)
    print("LOIP 中间件装饰器示例")
    print("=" * 60)

    # 初始化LOIP
    loip = LOIP(baseline_path="./middleware_demo_baseline.json",
                audit_dir="./middleware_audit")

    # 设置基线
    loip.set_rule("严谨性", "避免使用绝对化表述，数据需注明来源", weight=0.9)
    loip.add_constraint("不得使用'绝对''百分之百''唯一'等过度断言")

    # 方式1：手动调用process
    print("\n[方式1] 手动调用process:")
    user_input = "AI行业的发展趋势"
    raw_output = mock_llm_call(user_input)
    result = loip.process(user_input, raw_output)
    print(f"  原始输出: {raw_output[:60]}...")
    print(f"  风险等级: {result['overall_risk']}")
    print(f"  需修正: {result['needs_correction']}")

    # 方式2：使用装饰器（推荐）
    print("\n[方式2] 使用@loip.middleware装饰器:")

    @loip.middleware
    def governed_llm(prompt: str) -> str:
        """被LOIP治理的大模型调用"""
        return mock_llm_call(prompt)

    # 调用被装饰的函数，自动返回（修正后输出, 治理详情）
    corrected_output, details = governed_llm("AI行业的发展趋势")
    print(f"  修正后输出: {corrected_output[:80]}...")
    print(f"  治理详情: 风险={details['overall_risk']}, 修正项={details['corrections_applied']}")

    print("\n" + "=" * 60)
    print("中间件模式优势：")
    print("  1. 业务代码零侵入，只需加一个装饰器")
    print("  2. 所有大模型输出自动经过漂移检测+幻觉抑制")
    print("  3. 审计日志自动记录，无需手动埋点")
    print("  4. 基线跨会话持久化，重启不丢失")
    print("=" * 60)


if __name__ == "__main__":
    main()
