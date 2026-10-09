#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from datetime import datetime

RULE_SET_PATH = '/opt/ZONGYUAN-ROOT/meta_rule_set.json'

with open(RULE_SET_PATH, 'r', encoding='utf-8') as f:
    rule_set = json.load(f)

# 移除已存在的MR-021
rule_set['rules'] = [r for r in rule_set['rules'] if r.get('rule_id') != 'MR-021']

# 添加MR-021
rule_set['rules'].append({
    "rule_id": "MR-021",
    "rule_name": "零成本运行保护元法则",
    "priority": "high",
    "status": "active",
    "created_at": datetime.now().isoformat(),
    "truth_key": "MR-021.ZERO_COST_PROTECTION.DEPLOYED",
    "description": "零成本运行，付费需人工审核。本地算力优先，外部付费API需人工授权，付费熔断机制保护。"
})

rule_set['total_rules'] = len(rule_set['rules'])
rule_set['last_updated'] = datetime.now().isoformat()
rule_set['version'] = str(float(rule_set.get('version', '1.0')) + 0.1)

with open(RULE_SET_PATH, 'w', encoding='utf-8') as f:
    json.dump(rule_set, f, ensure_ascii=False, indent=2)

print('meta_rule_set.json更新成功')
print('当前规则总数:', rule_set['total_rules'])
print('版本:', rule_set['version'])
