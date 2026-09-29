#!/usr/bin/env python3
"""资产治理质量门禁：不合格资产自动告警"""
import json
import os
import hashlib
from datetime import datetime

OUTPUT_DIR = "/home/user/Doubao/chats/38439832899843586/quality_gate"
os.makedirs(OUTPUT_DIR, exist_ok=True)

WORK_DIR = "/home/user/Doubao/chats/38439832899843586"

# 扫描所有工具脚本
tools = []
for f in os.listdir(WORK_DIR):
    if f.endswith('.sh') or f.endswith('.py'):
        filepath = os.path.join(WORK_DIR, f)
        size = os.path.getsize(filepath)
        
        # 质量检查
        issues = []
        score = 100
        
        # 检查1: 文件大小
        if size < 100:
            issues.append("文件过小(<100B)")
            score -= 20
        elif size > 100000:
            issues.append("文件过大(>100KB)")
            score -= 10
        
        # 检查2: 语法检查（shell）
        if f.endswith('.sh'):
            import subprocess
            result = subprocess.run(['bash', '-n', filepath], capture_output=True, text=True)
            if result.returncode != 0:
                issues.append(f"语法错误: {result.stderr[:50]}")
                score -= 30
        
        # 检查3: 有注释/文档
        with open(filepath, 'r', errors='ignore') as fh:
            content = fh.read()
            if '#' not in content[:500] and f.endswith('.sh'):
                issues.append("缺少注释")
                score -= 10
        
        # 检查4: 哈希
        sha256 = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        tools.append({
            "filename": f,
            "size": size,
            "score": max(0, score),
            "issues": issues,
            "passed": score >= 60,
            "sha256": sha256
        })

# 生成质量门禁报告
passed = [t for t in tools if t['passed']]
failed = [t for t in tools if not t['passed']]

report = {
    "gate_id": "QG-" + datetime.now().strftime("%Y%m%d_%H%M%S"),
    "checked_at": datetime.now().isoformat(),
    "total_assets": len(tools),
    "passed": len(passed),
    "failed": len(failed),
    "pass_rate": len(passed) / len(tools) if tools else 0,
    "threshold": 60,
    "assets": tools,
    "failed_assets": failed,
    "gate_status": "PASS" if len(failed) == 0 else "FAIL"
}

with open(os.path.join(OUTPUT_DIR, "quality_gate_report.json"), 'w') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("✅ 资产质量门禁检查完成")
print(f"  检查资产数: {len(tools)}")
print(f"  通过: {len(passed)}")
print(f"  失败: {len(failed)}")
print(f"  通过率: {report['pass_rate']:.1%}")
print(f"  门禁状态: {report['gate_status']}")
print()
if failed:
    print("【未通过资产】")
    for t in failed:
        print(f"  ❌ {t['filename']}: 得分{t['score']}, 问题: {', '.join(t['issues'])}")
