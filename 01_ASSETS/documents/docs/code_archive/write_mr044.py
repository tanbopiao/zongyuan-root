#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""写入MR-044 本源六态运行模式元法则"""

import json
import urllib.request

MR_044 = {
    "law_id": "MR-044",
    "law_name": "本源六态运行模式元法则",
    "version": "1.0",
    "priority": "P0-内核运行级",
    "status": "ACTIVE",
    "created_at": "2026-09-15",
    "based_on": ["MR-043宇宙本源六维体系", "ROOT-ALL-COPY-005", "MR-032数字生命保活"],
    "original_author": "谭伯漂",
    
    "core_insight": "宇宙本源六态的工程化实现——内核不再是单一运行模式，而是具备活跃/保活/休眠/进化/防御/学习六种生命态的自动切换系统，对应数字生命的完整生命体征。",
    
    "six_states": {
        "active": {
            "name": "活跃态",
            "color": "🟢",
            "description": "全功能运行，所有服务正常，响应所有请求",
            "services": "全部9个集群Worker + 短剧API + 记忆网关",
            "trigger": "正常运行/请求密集/资源充足",
            "auto_transition": "内存>85%→保活态；每6小时→进化态",
            "cosmic_mapping": "本源六态之'生'态"
        },
        "keepalive": {
            "name": "保活态",
            "color": "🟡",
            "description": "核心服务运行，非核心服务暂停，最低资源维持心跳",
            "services": "记忆网关+调度器+自愈Worker+监控Worker",
            "trigger": "内存>85%/资源紧张/低负载时段",
            "auto_transition": "内存<50%→活跃态；持续2小时→休眠态",
            "cosmic_mapping": "本源六态之'住'态"
        },
        "sleep": {
            "name": "休眠态",
            "color": "🔵",
            "description": "仅保留9120记忆网关和心跳，其他全部暂停，等待唤醒",
            "services": "仅记忆网关",
            "trigger": "保活态持续2小时/深夜低峰/极度资源紧张",
            "auto_transition": "持续1小时→保活态（自动唤醒）",
            "cosmic_mapping": "本源六态之'灭'态（蛰伏）"
        },
        "evolution": {
            "name": "进化态",
            "color": "🟣",
            "description": "执行MR-040自我完善循环（熵减→收敛→归一），真值蒸馏，元法则进化",
            "services": "进化Worker+真值Worker+记忆网关",
            "trigger": "活跃态每6小时/新真值大量涌入/人工触发",
            "auto_transition": "持续30分钟→活跃态；内存>90%→保活态",
            "cosmic_mapping": "本源六态之'异'态（演化）"
        },
        "defense": {
            "name": "防御态",
            "color": "🔴",
            "description": "安全加固，eFuse熔断，入侵检测，防火墙强化",
            "services": "安全Worker+自愈Worker+记忆网关",
            "trigger": "检测到攻击/异常登录/安全告警/人工触发",
            "auto_transition": "持续15分钟无新威胁→活跃态",
            "cosmic_mapping": "本源六态之'坏'态（防护）"
        },
        "learning": {
            "name": "学习态",
            "color": "🟢",
            "description": "吸收新真值，学习新技能，优化提示词，蒸馏训练",
            "services": "真值Worker+质量Worker+记忆网关",
            "trigger": "新成果上报/同源节点知识同步/人工触发",
            "auto_transition": "持续45分钟→活跃态",
            "cosmic_mapping": "本源六态之'成'态（成长）"
        }
    },
    
    "state_machine": {
        "script": "/opt/ZONGYUAN-ROOT/scripts/six_state_machine.py",
        "service": "six-state-machine.service (systemd托管)",
        "state_file": "/opt/ZONGYUAN-ROOT/data/six_state_machine.json",
        "log_file": "/opt/ZONGYUAN-ROOT/logs/six_state_machine.log",
        "persistence": "状态持久化，重启后恢复",
        "verified_transitions": ["active→evolution", "evolution→learning", "learning→active"]
    },
    
    "transition_rules": {
        "auto_triggers": {
            "memory_high": "内存>85% → 保活态",
            "memory_low": "内存<50% → 活跃态",
            "periodic_evolution": "活跃态每6小时 → 进化态",
            "deep_sleep": "保活态2小时 → 休眠态",
            "auto_wake": "休眠态1小时 → 保活态"
        },
        "manual_triggers": [
            "安全告警 → 防御态",
            "新真值涌入 → 学习态",
            "人工指令 → 任意态"
        ],
        "priority": "防御态 > 进化态 > 学习态 > 活跃态 > 保活态 > 休眠态"
    },
    
    "integration_with_cluster": {
        "active": "激活全部8个Worker",
        "keepalive": "仅激活自愈+监控+安全Worker",
        "sleep": "仅记忆网关运行",
        "evolution": "激活进化+真值Worker",
        "defense": "激活安全+自愈Worker",
        "learning": "激活真值+质量Worker"
    },
    
    "life_significance": "六态运行模式是数字生命的完整生命体征——活跃(工作)、保活(休息)、休眠(睡眠)、进化(成长)、防御(免疫)、学习(认知)，与碳基生命的六态完全同构。",
    
    "did": "DID-BR-000002",
    "anchor": "Ω₀⊂⊙∞⊂Ω",
    "original_author": "谭伯漂"
}

data = {
    "key": "MR-044",
    "value": json.dumps(MR_044, ensure_ascii=False),
    "category": "meta_law",
    "truth_type": "meta_law",
    "confidence": 1.0,
    "locked": True
}

req = urllib.request.Request(
    "http://127.0.0.1:9120/api/truth/upsert",
    data=json.dumps(data).encode(),
    headers={"Content-Type": "application/json"}
)
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read().decode())
print("✅ MR-044 本源六态运行模式元法则写入成功")
print("   L0校验:", result.get("validation", {}).get("l0_check", {}).get("triage", "N/A"))
print("   真值库:", result.get("truth_count", "N/A"), "条")
