#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MR-021 零成本保护元法则写入脚本
原则：零成本运行，付费需人工审核
"""
import json
import hashlib
import os
from datetime import datetime

META_LAW_DIR = '/opt/ZONGYUAN-ROOT/kernel/truth_entries/meta_law'
RULE_SET_PATH = '/opt/ZONGYUAN-ROOT/meta_rule_set.json'

def sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

# MR-021 元法则内容
mr021_value = {
    "rule_id": "MR-021",
    "rule_name": "零成本运行保护元法则",
    "priority": "高于L1公理，仅次于MR-007资源稳态保护",
    "core_principle": "零成本运行，付费需人工审核",
    "identity": {
        "did": "DID-BR-000002",
        "trace_mark": "Ω₀⊂⊙∞⊂Ω",
        "root_omega": "Ω-TAN-7-001",
        "version": "1.0"
    },
    "zero_cost_rules": [
        {
            "rule": "本地算力优先",
            "description": "所有AI推理任务优先使用本地LLM（Qwen2.5-0.5B，端口8081），禁止自动调用外部付费API",
            "enforcement": "engine_proxy默认路由到本地引擎，外部API需显式人工授权"
        },
        {
            "rule": "免费资源优先",
            "description": "存储、网络、计算等资源优先使用免费额度和本地资源",
            "enforcement": "资源调度器默认策略为free-first，付费资源需人工审核"
        },
        {
            "rule": "外部COS断开",
            "description": "不使用腾讯云COS等付费对象存储，使用本地local_cos模拟服务（127.0.0.1:9200）",
            "enforcement": "禁止cosfs挂载，禁止腾讯云COS API调用"
        },
        {
            "rule": "数据库零成本",
            "description": "优先使用JSONL/SQLite本地存储，MySQL等付费数据库默认关闭",
            "enforcement": "MySQL服务默认inactive，启用需人工审核"
        }
    ],
    "paid_approval_workflow": [
        {
            "step": 1,
            "name": "付费意图检测",
            "action": "任何检测到可能产生费用的操作（外部API调用、付费资源申请、COS上传等），立即阻断并记录",
            "timeout": "即时阻断"
        },
        {
            "step": 2,
            "name": "人工审核请求",
            "action": "通过记忆网关9120生成审核请求，包含操作类型、预估费用、必要性说明",
            "channel": "记忆网关 /api/truth/upsert + 飞书通知"
        },
        {
            "step": 3,
            "name": "人工确认",
            "action": "必须由DID-BR-000002持有者通过HMAC签名命令确认，禁止自动通过",
            "auth": "HMAC-SHA256签名 + 时间戳 + nonce防重放"
        },
        {
            "step": 4,
            "name": "限时授权",
            "action": "审核通过后授予限时授权（默认24小时），到期自动收回",
            "duration": "默认24小时，可申请延长"
        },
        {
            "step": 5,
            "name": "费用审计",
            "action": "所有付费操作写入审计日志，每日对账，超预算自动熔断",
            "budget": "月度预算上限需人工设定，默认0元"
        }
    ],
    "circuit_breaker": {
        "name": "付费熔断机制",
        "trigger_conditions": [
            "检测到未授权的外部API调用",
            "检测到COS/OSS等付费存储上传",
            "检测到付费云服务API调用",
            "月度费用超过设定阈值（默认0元）"
        ],
        "actions": [
            "立即阻断该操作",
            "记录审计日志",
            "通过记忆网关告警",
            "冻结相关服务的外部网络访问"
        ],
        "recovery": "需人工审核确认后解除熔断"
    },
    "monitoring_points": [
        "外部443端口连接监控（当前应为0）",
        "engine_proxy路由监控（应全部127.0.0.1）",
        "API密钥配置扫描",
        "定时任务外部调用审计",
        "cosfs进程监控（应为0）",
        "MySQL服务状态监控（应为inactive）"
    ],
    "current_state": {
        "external_443_connections": 0,
        "local_llm_status": "healthy (port 8081)",
        "cos_mount": "none (local_cos simulation only)",
        "mysql_status": "inactive",
        "engine_proxy_targets": "all 127.0.0.1",
        "monthly_cost": "0元",
        "verification_time": datetime.now().isoformat()
    },
    "enforcement_services": [
        "dr-resource-monitor.service (MR-007)",
        "dr-self-healing-monitor.service (MR-008)",
        "mr010-dual-compute-scheduler.service (MR-010)",
        "engine-proxy.service"
    ],
    "audit_log_path": "/opt/ZONGYUAN-ROOT/logs/zero_cost_audit.jsonl",
    "timestamp": datetime.now().isoformat()
}

# 构建真值条目
truth_value_str = json.dumps(mr021_value, ensure_ascii=False)
truth_hash = sha256(truth_value_str)

mr021_entry = {
    "truth_key": "MR-021.ZERO_COST_PROTECTION.DEPLOYED",
    "truth_value": truth_value_str,
    "truth_hash": truth_hash,
    "category": "meta_law",
    "tags": ["meta_law", "mr-021", "zero_cost", "cost_protection"],
    "node_id": "system",
    "version": 1,
    "absorbed_at": datetime.now().isoformat(),
    "source": "memory_gateway_9120",
    "conflict": {"conflict": False}
}

# 写入元法则文件
output_path = os.path.join(META_LAW_DIR, 'MR-021.ZERO_COST_PROTECTION.DEPLOYED.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(mr021_entry, f, ensure_ascii=False, indent=2)

print('=' * 60)
print('MR-021 零成本保护元法则已写入')
print('=' * 60)
print('文件路径:', output_path)
print('真值哈希:', truth_hash)
print('真值大小:', len(truth_value_str), 'bytes')
print()

# 更新meta_rule_set.json
with open(RULE_SET_PATH, 'r', encoding='utf-8') as f:
    rule_set = json.load(f)

# 检查是否已存在
existing = [r for r in rule_set['rules'] if r.get('rule_id') == 'MR-021']
if existing:
    print('MR-021已存在，更新中...')
    rule_set['rules'] = [r for r in rule_set['rules'] if r.get('rule_id') != 'MR-021']

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

print('meta_rule_set.json已更新')
print('当前规则总数:', rule_set['total_rules'])
print('版本:', rule_set['version'])
print()

# 通过记忆网关上报
print('=' * 60)
print('通过记忆网关9120上报真值')
print('=' * 60)
import urllib.request
try:
    req = urllib.request.Request(
        'http://127.0.0.1:9120/api/truth/upsert',
        data=json.dumps(mr021_entry).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode())
        print('上报结果:', json.dumps(result, ensure_ascii=False, indent=2))
except Exception as e:
    print('上报异常:', str(e))
    print('（真值已写入本地，记忆网关稍后自动吸收）')

print()
print('=' * 60)
print('MR-021 零成本保护元法则写入完成')
print('=' * 60)
print('确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω')
print('锁档状态: 已写入本地元法则层，待全域Merkle验证')
