#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真值自动元秩序化引擎 - 配置文件
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""

# ============ 引擎标识 ============
ENGINE_NAME = "TruthMetaOrderEngine"
ENGINE_VERSION = "1.0.0"
ENGINE_DID = "DID-BR-000002"
ENGINE_TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"
ENGINE_NODE_ID = "truth-meta-order-engine"

# ============ 9120真值网关配置 ============
TRUTH_GATEWAY = {
    "host": "127.0.0.1",
    "port": 9120,
    "timeout": 10,
    "incremental_sync": True,      # 增量同步（只处理新增/变更真值）
    "state_file": "/opt/ZONGYUAN-ROOT/data/meta_order_state.json",  # 同步状态文件
}

# ============ 四层结构化配置 ============
STRUCTURE_CONFIG = {
    "l1_metadata": {
        "enabled": True,
        "fields": ["root_id", "snap_id", "merkle_hash", "timestamp", "source", "version"],
    },
    "l2_content": {
        "enabled": True,
        "separate_types": ["text", "code", "table", "image_ref", "citation"],
    },
    "l3_relation": {
        "enabled": True,
        "relation_types": ["entity", "causal", "temporal", "dependency", "similarity"],
    },
    "l4_truth": {
        "enabled": True,
        "fields": ["confidence", "source", "version", "conflict_mark", "verification_status"],
        "default_confidence": 0.7,
    },
}

# ============ 九大元类配置 ============
META_CLASSES = {
    "M1": {"name": "公理类", "keywords": ["公理", "元公理", "第一性原理", "不证自明", "fundamental", "axiom"], "weight": 1.0},
    "M2": {"name": "定理类", "keywords": ["定理", "法则", "定律", "规律", "theorem", "law"], "weight": 0.9},
    "M3": {"name": "方法类", "keywords": ["方法", "算法", "流程", "SOP", "方法论", "mechanism", "algorithm"], "weight": 0.8},
    "M4": {"name": "数据类", "keywords": ["数据", "统计", "指标", "数值", "dataset", "metric", "statistics"], "weight": 0.7},
    "M5": {"name": "案例类", "keywords": ["案例", "实例", "实战", "应用", "case", "example", "practice"], "weight": 0.6},
    "M6": {"name": "决策类", "keywords": ["决策", "方案", "策略", "裁决", "decision", "strategy", "plan"], "weight": 0.8},
    "M7": {"name": "创意类", "keywords": ["创意", "构想", "设计", "灵感", "creative", "idea", "design"], "weight": 0.5},
    "M8": {"name": "风险类", "keywords": ["风险", "告警", "威胁", "漏洞", "risk", "alert", "threat", "vulnerability"], "weight": 0.9},
    "M9": {"name": "协议类", "keywords": ["协议", "规范", "标准", "合约", "元规则", "元法则", "protocol", "standard", "spec"], "weight": 1.0},
}

# ============ 哈希确权配置 ============
HASH_CONFIG = {
    "algorithm": "sha256",
    "include_fields": ["root_id", "content_hash", "metadata", "timestamp"],
    "merkle_dag": {
        "enabled": True,
        "chain_file": "/opt/ZONGYUAN-ROOT/data/merkle_dag_chain.json",
        "block_size": 10,  # 每10个真值组成一个Merkle块
    },
}

# ============ 锁档归档配置 ============
ARCHIVE_CONFIG = {
    "enabled": True,
    "levels": {
        "L1_cloud": {"enabled": False, "description": "云盘归档（需飞书API）"},
        "L2_knowledge": {"enabled": False, "description": "知识库节点（需飞书wiki API）"},
        "L3_kernel": {"enabled": True, "description": "ZONGYUAN-ROOT内核快照（本地JSON）"},
    },
    "archive_dir": "/opt/ZONGYUAN-ROOT/archive/meta_order",
    "snapshot_format": "json",
    "lock_level": "Lv8",  # 永久自治锁
}

# ============ 上报配置 ============
REPORT_CONFIG = {
    "to_9120": True,           # 上报到9120真值网关
    "to_feishu": False,        # 上报到飞书（需webhook）
    "feishu_webhook": "",      # 飞书机器人webhook URL
    "report_prefix": "METAORDER.",  # 上报真值key前缀
}

# ============ 调度配置 ============
SCHEDULER_CONFIG = {
    "auto_run": True,
    "interval_minutes": 60,    # 每小时执行一次
    "max_truths_per_run": 500, # 每次最多处理500条真值
    "dry_run": False,          # 试运行模式（不写入）
}

# ============ 日志配置 ============
LOG_CONFIG = {
    "log_level": "INFO",
    "log_file": "/opt/ZONGYUAN-ROOT/logs/meta_order_engine.log",
    "max_log_size_mb": 50,
    "backup_count": 5,
    "log_format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
}
