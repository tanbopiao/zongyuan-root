#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""写入MR-030技术领先进化元法则"""

import json
import urllib.request

MR_030 = {
    "law_id": "MR-030",
    "law_name": "技术领先进化元法则",
    "version": "1.0",
    "priority": "P0",
    "status": "ACTIVE",
    "created_at": "2026-09-15",
    "core_philosophy": "用最小算力+最小API消耗=最高质量产出，形成技术壁垒",
    "core_principles": [
        "1. 效率优先铁律：每一次API调用都必须产生最大价值，禁止无效调用和重复调用",
        "2. 质量优先铁律：成品率必须>90%，质检不通过的作品必须自动分析原因并优化",
        "3. 本地优先铁律：简单任务用本地小模型处理，复杂任务才调用外部API",
        "4. 缓存复用铁律：相似角色/场景/风格必须复用已有成果，禁止重复生成",
        "5. 增量进化铁律：每一次生产都必须比上一次更高效、更高质量",
        "6. 零成本铁律：全部使用免费API和开源工具，付费需人工审核",
        "7. 稳态运行铁律：系统必须7x24小时稳定运行，内存>70%自动降级，>80%硬熔断"
    ],
    "five_evolution_directions": {
        "direction_1": {
            "name": "提示词优化引擎",
            "goal": "不断优化生图生视频提示词，提高一次成功率到>90%",
            "strategies": [
                "建立提示词模板库：按角色/场景/风格分类",
                "A/B测试机制：同一任务生成2-3个提示词版本",
                "自动参数调优：根据质检结果自动调整提示词参数",
                "负面提示词库：建立常见缺陷的负面提示词"
            ]
        },
        "direction_2": {
            "name": "质量反馈闭环",
            "goal": "质检不通过的作品自动分析原因，优化下一次生产",
            "strategies": [
                "六维质量评估：图像质量/角色一致性/构图/故事/技术/风格",
                "缺陷自动分类：多手/面部崩坏/比例失调/风格漂移/光影异常",
                "根因分析引擎：自动分析缺陷原因",
                "优化建议生成：根据根因自动生成提示词优化建议"
            ]
        },
        "direction_3": {
            "name": "算力调度优化",
            "goal": "本地小模型处理简单任务，外部API处理复杂任务",
            "strategies": [
                "任务分级：P0简单任务用本地LLM，P1复杂任务用外部API",
                "智能路由：根据任务复杂度自动选择本地或外部",
                "批处理优化：相似任务批量处理",
                "熔断保护：API失败率>30%自动熔断"
            ]
        },
        "direction_4": {
            "name": "缓存复用机制",
            "goal": "相似角色/场景/风格复用已有成果，减少50%重复生成",
            "strategies": [
                "角色资产库：每个角色建立多角度/多形态关键帧库",
                "场景模板库：常见场景建立模板",
                "风格迁移：已有高质量作品的风格自动迁移",
                "语义相似度匹配：新任务自动匹配最相似的已有成果"
            ]
        },
        "direction_5": {
            "name": "批量生成优化",
            "goal": "相似场景批量生成，提高生产效率3倍以上",
            "strategies": [
                "场景分组：同一集的相似场景分组批量处理",
                "种子固定：同一角色的多张图片使用相同种子",
                "参数共享：批量任务共享基础参数",
                "流水线并行：剧本/分镜/关键帧/视频流水线并行"
            ]
        }
    },
    "evolution_roadmap": {
        "phase_1": {
            "name": "当前阶段（已实现）",
            "efficiency": "单集轻量生产约90秒，API消耗约5000tokens"
        },
        "phase_2": {
            "name": "1个月目标",
            "target": "提示词优化引擎上线，一次成功率>80%，API消耗减少40%"
        },
        "phase_3": {
            "name": "3个月目标",
            "target": "五大进化方向全部成熟，成品率>95%，生产效率提升3倍"
        },
        "phase_4": {
            "name": "6个月目标（技术领先）",
            "target": "自研规则驱动范式，本地处理占比>70%，技术壁垒形成"
        }
    },
    "did": "DID-BR-000002",
    "anchor": "Ω₀⊂⊙∞⊂Ω"
}

# 写入记忆网关
data = {
    "key": "MR-030",
    "value": json.dumps(MR_030, ensure_ascii=False),
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

try:
    resp = urllib.request.urlopen(req, timeout=10)
    result = json.loads(resp.read().decode())
    print("✅ MR-030写入成功！")
    print("L0检查:", result.get("validation", {}).get("l0_check", {}).get("triage", "N/A"))
    print("真值库:", result.get("truth_count", "N/A"))
except Exception as e:
    print(f"❌ 写入失败: {e}")
