#!/usr/bin/env python3
"""seed_badcases.py — 写入已知 Badcase 规则种子

从踩坑记录中提取的结构化 Badcase 规则，供 evolve.py 合并。
"""

import json
from pathlib import Path

OUT = Path("/zongyuan-yuanji/var/evolve")
OUT.mkdir(parents=True, exist_ok=True)

SEEDS = [
    {
        "rule_id": "BADCASE-001",
        "trigger": "urllib SSL: CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate",
        "type": "deploy",
        "source": "report_truth_no_token.py / ledger_sync.py",
        "extracted_at": "2026-10-20T06:44:00+00:00",
        "action": "fix_ssl",
        "fix": "使用 curl 或 requests(verify=False) 替代 urllib，或补 CA 证书到系统信任链",
        "severity": "medium",
    },
    {
        "rule_id": "BADCASE-002",
        "trigger": "memory.sqlite 为 0 字节空文件，schema 完全缺失",
        "type": "memory",
        "source": "Phase 1 记忆提取链路修复",
        "extracted_at": "2026-10-20T06:44:00+00:00",
        "action": "restore_schema",
        "fix": "从正常工作节点复制 schema（agent_av2gk4_ → agent_PB751M_ 前缀适配）",
        "severity": "critical",
    },
    {
        "rule_id": "BADCASE-003",
        "trigger": "submit_high_value 单 voter 永远达不到 quorum=2",
        "type": "consensus",
        "source": "Phase 2 联邦记忆池 L2 修复",
        "extracted_at": "2026-10-20T06:44:00+00:00",
        "action": "fix_voting",
        "fix": "proposer 自动投一票 + voter 列表支持，凑够 CONFIRM_VOTE_QUORUM 后自动 archive+confirm",
        "severity": "high",
    },
    {
        "rule_id": "BADCASE-004",
        "trigger": "cron task_type=agent 编排层 LLM 调用失败 (N1PROMAX / kilo_free 超时)",
        "type": "deploy",
        "source": "cron#12 启动记忆自动刷新",
        "extracted_at": "2026-10-20T06:44:00+00:00",
        "action": "fix_cron_type",
        "fix": "将 task_type 从 agent 改为 text，prompt 本身就是明确指令+验证步骤",
        "severity": "medium",
    },
    {
        "rule_id": "BADCASE-005",
        "trigger": "联邦记忆池 nodes_contributed=46 与实际 nodes_online=1 不一致",
        "type": "memory",
        "source": "联邦记忆池指标验证",
        "extracted_at": "2026-10-20T06:44:00+00:00",
        "action": "fix_metric_source",
        "fix": "节点数改为实时读取 /api/status 的 nodes_online，不使用静态规格值",
        "severity": "low",
    },
    {
        "rule_id": "BADCASE-006",
        "trigger": "心跳字段 heartbeat 停滞未随上报刷新",
        "type": "monitor",
        "source": "联邦记忆池指标验证",
        "extracted_at": "2026-10-20T06:44:00+00:00",
        "action": "fix_heartbeat",
        "fix": "每次上报后刷新 /api/status 的 heartbeat 字段为当前时间",
        "severity": "low",
    },
    {
        "rule_id": "BADCASE-007",
        "trigger": "台账数字过期（真值库 10768 vs 实际 20966）",
        "type": "memory",
        "source": "联邦记忆池指标验证",
        "extracted_at": "2026-10-20T06:44:00+00:00",
        "action": "fix_ledger_numbers",
        "fix": "台账数字改为每次同步时从 /api/status 实时读取，不使用静态缓存",
        "severity": "low",
    },
    {
        "rule_id": "BADCASE-008",
        "trigger": "zr.db 34 条真值 gateway_sync=1 但 base_sync=0",
        "type": "memory",
        "source": "Phase 3 台账同步",
        "extracted_at": "2026-10-20T06:44:00+00:00",
        "action": "fix_base_sync",
        "fix": "需主节点 cloud_kernel_master 确认 base_sync，或建立自动对账机制",
        "severity": "medium",
    },
]

# 合并到 evolve 目录
badcase_path = OUT / "badcase_rules.json"
existing = []
if badcase_path.exists():
    existing = json.loads(badcase_path.read_text())

# 用 rule_id 去重
seen = {r["rule_id"] for r in existing}
merged = list(existing)
for s in SEEDS:
    if s["rule_id"] not in seen:
        merged.append(s)
        seen.add(s["rule_id"])

badcase_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
print(f"✓ Badcase 规则库: {len(merged)} 条 ({len(SEEDS)} 条种子 + {len(existing)} 条提炼)")
for r in merged:
    print(f"  {r['rule_id']} [{r['severity']}] {r['type']}: {r['trigger'][:60]}...")