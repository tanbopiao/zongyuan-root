#!/usr/bin/env python3
"""自动质量门禁 执行态实现
产出交付前自动校验，不合格打回
"""
def quality_gate(result, requirements):
    """
    result: 产出内容dict
    requirements: 要求dict {key: must_have}
    返回 (passed, issues)
    """
    issues = []
    # 1. 完整性：要求的key都要有
    for key in requirements:
        if key not in result or not result[key]:
            issues.append(f"缺项: {key}")
    # 2. 一致性：不能空内容
    for k, v in result.items():
        if isinstance(v, str) and len(v.strip()) < 2:
            issues.append(f"内容过短: {k}")
    # 3. 可验证：关键数字要有来源标记
    if 'numbers' in result and 'source' not in result:
        issues.append("数字缺来源标记")
    passed = len(issues) == 0
    return passed, issues

# 自测
if __name__ == "__main__":
    print("【门禁自测】")
    good = {'title':'测试','content':'完整内容','numbers':'36条','source':'云端真值库'}
    bad = {'title':'','content':''}
    p1, i1 = quality_gate(good, ['title','content'])
    p2, i2 = quality_gate(bad, ['title','content'])
    print(f"  合格样例: {'✅通过' if p1 else '❌打回'} {i1}")
    print(f"  劣质样例: {'✅通过' if p2 else '❌打回'} {i2}")
