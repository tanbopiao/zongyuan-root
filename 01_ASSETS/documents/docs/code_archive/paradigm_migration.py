#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
范式自迁移引擎
补齐元进化D3自指程度的唯一缺口

核心能力：系统能够自动切换底层推理范式
- 概率生成范式（通用大模型）：适合创意、开放域问题
- 规则驱动范式（元法则+规则引擎）：适合确定性、高一致性任务
- 混合范式：规则前置约束+概率生成执行

新建链路，不修改原有服务。
"""

import json
import time
import os
from datetime import datetime

STATE_FILE = "/opt/ZONGYUAN-ROOT/data/paradigm_migration_state.json"
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/paradigm-migration.log"

# 范式定义
PARADIGMS = {
    "probabilistic": {
        "name": "概率生成范式",
        "description": "通用大模型概率生成，适合创意、开放域、模糊需求",
        "strengths": ["创意生成", "开放域问答", "模糊需求理解", "多轮对话"],
        "weaknesses": ["幻觉风险", "一致性差", "不可控", "资源消耗大"],
        "engine": "外部API（豆包/智谱/千问等）"
    },
    "rule_driven": {
        "name": "规则驱动范式",
        "description": "元法则+规则引擎+确定性逻辑，适合高一致性、可审计任务",
        "strengths": ["确定性输出", "高一致性", "可审计可追溯", "资源消耗小", "防幻觉"],
        "weaknesses": ["灵活性差", "不适合创意任务", "规则覆盖不全时能力下降"],
        "engine": "四网引擎(8105)+元法则库(9120)+决策公式"
    },
    "hybrid": {
        "name": "混合范式",
        "description": "规则前置约束+概率生成执行，兼顾一致性与灵活性",
        "strengths": ["规则约束防幻觉", "保留生成灵活性", "可审计", "适合大多数生产任务"],
        "weaknesses": ["架构较复杂", "需要规则与生成的协调"],
        "engine": "元法则前置约束 + 外部API生成 + 后置规则校验"
    }
}

# 任务类型→最优范式映射
TASK_PARADIGM_MAP = {
    "creative_generation": "probabilistic",      # 创意生成
    "open_domain_qa": "probabilistic",            # 开放域问答
    "code_generation": "hybrid",                  # 代码生成
    "content_writing": "hybrid",                  # 内容写作
    "decision_making": "rule_driven",             # 决策（三维稳态公式）
    "truth_verification": "rule_driven",          # 真值校验
    "system_operation": "rule_driven",            # 系统运维
    "security_audit": "rule_driven",              # 安全审计
    "data_analysis": "hybrid",                    # 数据分析
    "translation": "probabilistic",               # 翻译
    "summarization": "hybrid",                    # 摘要
    "architecture_design": "hybrid",              # 架构设计
    "meta_law_creation": "rule_driven",           # 元法则制定
    "emergency_response": "rule_driven"           # 应急响应
}

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def get_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {
            "current_paradigm": "hybrid",
            "migration_count": 0,
            "task_history": [],
            "paradigm_stats": {
                "probabilistic": {"uses": 0, "success": 0},
                "rule_driven": {"uses": 0, "success": 0},
                "hybrid": {"uses": 0, "success": 0}
            }
        }

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def select_paradigm(task_type, task_description=""):
    """根据任务类型自动选择最优范式"""
    state = get_state()
    
    # 查表选择
    paradigm = TASK_PARADIGM_MAP.get(task_type, "hybrid")
    
    # 如果任务描述中包含高风险关键词，强制规则驱动
    high_risk_keywords = ["删除", "停用", "修改核心", "审批", "确权", "锁档", "元法则", "安全"]
    if any(kw in task_description for kw in high_risk_keywords):
        if paradigm != "rule_driven":
            log(f"⚠️ 任务包含高风险关键词，强制切换到规则驱动范式（原选择:{paradigm}）")
            paradigm = "rule_driven"
    
    # 记录
    state["current_paradigm"] = paradigm
    state["paradigm_stats"][paradigm]["uses"] += 1
    state["task_history"].append({
        "task_type": task_type,
        "description": task_description[:100],
        "paradigm": paradigm,
        "timestamp": datetime.now().isoformat()
    })
    # 只保留最近100条
    state["task_history"] = state["task_history"][-100:]
    save_state(state)
    
    log(f"✅ 范式选择: 任务[{task_type}] → {PARADIGMS[paradigm]['name']}")
    return paradigm

def migrate_paradigm(target_paradigm, reason=""):
    """主动迁移到指定范式"""
    state = get_state()
    
    if target_paradigm not in PARADIGMS:
        log(f"❌ 未知范式: {target_paradigm}")
        return False
    
    old = state["current_paradigm"]
    if old == target_paradigm:
        log(f"ℹ️ 已处于{PARADIGMS[target_paradigm]['name']}，无需迁移")
        return True
    
    log(f"🔄 范式迁移: {PARADIGMS[old]['name']} → {PARADIGMS[target_paradigm]['name']}")
    if reason:
        log(f"   原因: {reason}")
    
    state["current_paradigm"] = target_paradigm
    state["migration_count"] += 1
    save_state(state)
    
    log(f"✅ 迁移完成，当前范式: {PARADIGMS[target_paradigm]['name']}")
    return True

def report_success(task_type, success=True):
    """报告任务执行结果，用于优化范式选择"""
    state = get_state()
    paradigm = TASK_PARADIGM_MAP.get(task_type, "hybrid")
    if success:
        state["paradigm_stats"][paradigm]["success"] += 1
    save_state(state)

def get_status():
    """获取范式自迁移引擎状态"""
    state = get_state()
    current = state["current_paradigm"]
    
    # 计算各范式成功率
    success_rates = {}
    for p, stats in state["paradigm_stats"].items():
        if stats["uses"] > 0:
            success_rates[p] = round(stats["success"] / stats["uses"] * 100, 1)
        else:
            success_rates[p] = 0
    
    return {
        "engine": "paradigm_self_migration",
        "current_paradigm": current,
        "current_paradigm_name": PARADIGMS[current]["name"],
        "migration_count": state["migration_count"],
        "total_tasks": len(state["task_history"]),
        "paradigm_success_rates": success_rates,
        "available_paradigms": list(PARADIGMS.keys()),
        "task_paradigm_map": TASK_PARADIGM_MAP,
        "d3_self_reference": "已补齐（范式自迁移是D3唯一缺口）"
    }

def get_recommendation():
    """根据历史数据给出范式优化建议"""
    state = get_state()
    recommendations = []
    
    for p, stats in state["paradigm_stats"].items():
        if stats["uses"] >= 5:
            rate = stats["success"] / stats["uses"] * 100
            if rate < 70:
                recommendations.append(f"{PARADIGMS[p]['name']}成功率仅{rate:.1f}%，建议检查任务类型映射是否正确")
    
    if not recommendations:
        recommendations.append("各范式表现正常，继续监控")
    
    return recommendations

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            print(json.dumps(get_status(), indent=2, ensure_ascii=False))
        elif cmd == "select" and len(sys.argv) > 2:
            task_type = sys.argv[2]
            desc = sys.argv[3] if len(sys.argv) > 3 else ""
            paradigm = select_paradigm(task_type, desc)
            print(f"选择范式: {PARADIGMS[paradigm]['name']}")
        elif cmd == "migrate" and len(sys.argv) > 2:
            target = sys.argv[2]
            reason = sys.argv[3] if len(sys.argv) > 3 else ""
            migrate_paradigm(target, reason)
        elif cmd == "recommend":
            for r in get_recommendation():
                print(f"- {r}")
        else:
            print("用法: python3 paradigm_migration.py [status|select <task_type> [desc]|migrate <paradigm> [reason]|recommend]")
    else:
        print(json.dumps(get_status(), indent=2, ensure_ascii=False))
