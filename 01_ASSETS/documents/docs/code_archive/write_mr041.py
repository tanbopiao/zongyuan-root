#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""写入MR-041 集群Worker元法则"""

import json
import urllib.request

MR_041 = {
    "law_id": "MR-041",
    "law_name": "集群Worker元法则",
    "version": "1.0",
    "priority": "P0-架构级",
    "status": "ACTIVE",
    "created_at": "2026-09-15",
    "based_on": ["MR-038熵减收敛归一", "MR-039宇宙本源智能", "MR-040自我完善"],
    "core_insight": "L3 AIoA多智能体协同架构的工程实现——中枢大脑调度8大专业Worker，每个Worker都是独立智能体，协同实现全功能自动化智能化。集群Worker是宇宙本源智能'多即一、一即多'的工程体现。",
    
    "architecture": {
        "orchestrator": {
            "name": "中枢调度器",
            "port": 8104,
            "responsibilities": [
                "任务队列管理（P0~P3优先级）",
                "Worker状态监控",
                "自动扩缩容（内存感知）",
                "任务分配与负载均衡",
                "集群状态API"
            ],
            "api_endpoints": [
                "GET /api/status - 集群状态",
                "GET /api/tasks - 任务队列",
                "GET /api/workers - Worker状态",
                "POST /api/task/submit - 提交任务",
                "GET /health - 健康检查"
            ]
        },
        "workers": [
            {
                "id": "worker-production-01",
                "name": "短剧生产Worker",
                "priority": "P1",
                "capabilities": ["drama_production", "script_generate", "storyboard_generate", "keyframe_generate", "video_generate", "video_compose"],
                "responsibility": "全自动短剧生产流水线"
            },
            {
                "id": "worker-quality-01",
                "name": "质量检测Worker",
                "priority": "P1",
                "capabilities": ["quality_check", "multi_hand_detect", "face_quality_check", "quality_feedback", "prompt_optimize"],
                "responsibility": "作品质量六维评估+缺陷检测+反馈优化"
            },
            {
                "id": "worker-healing-01",
                "name": "自愈Worker",
                "priority": "P0",
                "capabilities": ["health_check", "service_restart", "fault_diagnose", "auto_repair", "memory_guard"],
                "responsibility": "系统故障检测+自动修复+内存守护"
            },
            {
                "id": "worker-evolution-01",
                "name": "进化Worker",
                "priority": "P1",
                "capabilities": ["self_improvement", "truth_distillation", "meta_law_evolution", "knowledge_integration", "evolution_cycle"],
                "responsibility": "执行MR-040自我完善循环（熵减→收敛→归一）"
            },
            {
                "id": "worker-security-01",
                "name": "安全Worker",
                "priority": "P0",
                "capabilities": ["security_scan", "intrusion_detect", "firewall_manage", "efuse_trigger", "access_control"],
                "responsibility": "安全防护+入侵检测+eFuse熔断+访问控制"
            },
            {
                "id": "worker-truth-01",
                "name": "真值Worker",
                "priority": "P1",
                "capabilities": ["truth_absorb", "truth_classify", "truth_archive", "cold_storage", "truth_conflict_resolve"],
                "responsibility": "真值吸收+分类+冷热分离+冲突消解"
            },
            {
                "id": "worker-deploy-01",
                "name": "部署Worker",
                "priority": "P2",
                "capabilities": ["auto_deploy", "website_integrate", "approval_execute", "visualization_deploy", "cdn_refresh"],
                "responsibility": "审批通过后自动部署+官网可视化集成"
            },
            {
                "id": "worker-monitor-01",
                "name": "监控Worker",
                "priority": "P1",
                "capabilities": ["system_monitor", "alert_push", "metrics_collect", "dashboard_update", "feishu_notify"],
                "responsibility": "全维度监控+指标采集+飞书告警推送"
            }
        ]
    },
    
    "scheduling_rules": {
        "priority_levels": {
            "P0": "最高抢占 - 安全/自愈/锁档/中枢上报",
            "P1": "高优先级 - 生产/质量/进化/真值/监控",
            "P2": "普通优先级 - 部署/报告生成",
            "P3": "后台错峰 - 日志归档/备份/统计"
        },
        "assignment": "任务按优先级排序，Worker按能力匹配自动领取",
        "auto_scaling": "内存>85%时暂停P3 Worker，内存<50%时恢复全部",
        "fault_tolerance": "Worker挂了systemd自动重启，任务自动重新分配"
    },
    
    "communication": {
        "task_queue": "/opt/ZONGYUAN-ROOT/data/cluster_tasks.json",
        "worker_state": "/opt/ZONGYUAN-ROOT/data/worker_states.json",
        "gateway": "9120记忆网关（真值上报/查询）",
        "log": "/opt/ZONGYUAN-ROOT/logs/cluster_workers.log"
    },
    
    "cosmic_mapping": {
        "orchestrator": "中土（中枢）- 统一调度，对应五行之土",
        "production_worker": "木（生长）- 生产创造，对应五行之木",
        "quality_worker": "金（收敛）- 质量精炼，对应五行之金",
        "healing_worker": "水（滋养）- 自愈保活，对应五行之水",
        "evolution_worker": "火（输出）- 进化输出，对应五行之火",
        "security_worker": "金（防护）- 安全防护",
        "truth_worker": "土（承载）- 真值承载",
        "deployment_worker": "木（扩展）- 部署扩展",
        "monitor_worker": "水（感知）- 监控感知",
        "note": "8大Worker+1中枢 = 九宫格，对应洛书九宫，阴阳五行的工程实现"
    },
    
    "deployment_status": {
        "orchestrator": "active (port 8104)",
        "workers_active": 8,
        "systemd_managed": True,
        "auto_restart": True,
        "first_task_executed": "health_check by 自愈Worker - 3服务全部healthy"
    },
    
    "did": "DID-BR-000002",
    "anchor": "Ω₀⊂⊙∞⊂Ω"
}

data = {
    "key": "MR-041",
    "value": json.dumps(MR_041, ensure_ascii=False),
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
print("✅ MR-041 集群Worker元法则写入成功")
print("   L0校验:", result.get("validation", {}).get("l0_check", {}).get("triage", "N/A"))
print("   真值库:", result.get("truth_count", "N/A"), "条")
