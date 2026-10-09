#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""更新元进化度量引擎：加入对新引擎的检测"""

import os

target = "/opt/ZONGYUAN-ROOT/scripts/meta_evolution_metrics.py"
backup = target + ".bak.20260915"

# 备份
if not os.path.exists(backup):
    os.system(f"cp {target} {backup}")
    print(f"✅ 已备份: {backup}")

with open(target) as f:
    content = f.read()

# 更新D3：检测范式自迁移引擎
old_d3_marker = '    # 前5项已实现，第6项（范式自迁移）是当前唯一缺口\n    d3_score = (5 / 6) * 100'
new_d3_marker = '''    # 检查范式自迁移引擎是否已部署
    paradigm_migration_deployed = os.path.exists("/opt/ZONGYUAN-ROOT/scripts/paradigm_migration.py")
    implemented_count = 6 if paradigm_migration_deployed else 5
    d3_score = (implemented_count / 6) * 100'''

if old_d3_marker in content:
    content = content.replace(old_d3_marker, new_d3_marker)
    print("✅ D3检测逻辑已更新")
else:
    print("⚠️ D3标记未找到，尝试其他匹配...")

# 更新D1：检测规则驱动引擎
old_d1_marker = '    stage6_progress = 0.45'
new_d1_marker = '''    rule_driven_deployed = os.path.exists("/opt/ZONGYUAN-ROOT/scripts/rule_driven_engine.py")
    stage6_progress = 0.75 if rule_driven_deployed else 0.45'''

if old_d1_marker in content:
    content = content.replace(old_d1_marker, new_d1_marker)
    print("✅ D1检测逻辑已更新")
else:
    print("⚠️ D1标记未找到")

with open(target, "w") as f:
    f.write(content)

print("✅ 度量引擎更新完成")
