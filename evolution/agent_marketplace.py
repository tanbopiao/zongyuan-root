#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — 智能体自动化服务市场（EVO-P2-002）

功能：
  1. Agent 模板管理（基于自治内核 + 进化引擎）
  2. 交付流程标准化
  3. 模板目录与定价
  4. 能力评估与推荐

使用方式：
  python3 agent_marketplace.py             # 生成/更新 Agent 模板目录
  python3 agent_marketplace.py --list      # 列出所有模板
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# ============ 路径配置 ============

WORKSPACE = Path("/workspace")
EVOLUTION_DIR = WORKSPACE / "evolution"
AGENT_DIR = EVOLUTION_DIR / "agent_marketplace"
AGENT_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = AGENT_DIR / "marketplace.log"
CATALOG_FILE = AGENT_DIR / "catalog.json"

SERVICES_DIR = WORKSPACE / "scripts" / "services"
sys.path.insert(0, str(SERVICES_DIR))

DID_TAG = "DID-BR-000002"

# Agent 模板库
AGENT_TEMPLATES = [
    {
        "id": "AGENT-KNOWLEDGE-001",
        "name": "企业知识库构建 Agent",
        "category": "knowledge",
        "description": "基于 RAG 的企业知识库自动构建与问答",
        "capabilities": ["文档解析", "向量化", "语义检索", "问答生成"],
        "delivery_days": 3,
        "base_price": 9800,
        "dependencies": ["autonomous_kernel", "truth_evolution_engine"],
    },
    {
        "id": "AGENT-COMPLIANCE-001",
        "name": "内容合规审校 Agent",
        "category": "compliance",
        "description": "AI 内容合规检测与自动改写",
        "capabilities": ["禁用词检测", "风险分级", "自动改写", "复核队列"],
        "delivery_days": 2,
        "base_price": 6800,
        "dependencies": ["compliance_checker", "compliance_api"],
    },
    {
        "id": "AGENT-DRAMA-001",
        "name": "短剧内容生产 Agent",
        "category": "content",
        "description": "八段式短剧自动化生产流水线",
        "capabilities": ["剧本创作", "分镜设计", "画面生成", "配音合成", "剪辑发布"],
        "delivery_days": 5,
        "base_price": 19800,
        "dependencies": ["drama_pipeline"],
    },
    {
        "id": "AGENT-INTELLIGENCE-001",
        "name": "行业情报分析 Agent",
        "category": "intelligence",
        "description": "AI 产业情报自动采集与日报生成",
        "capabilities": ["全网抓取", "真值提炼", "维度分类", "日报生成"],
        "delivery_days": 2,
        "base_price": 7800,
        "dependencies": ["intelligence_generator", "truth_evolution_engine"],
    },
    {
        "id": "AGENT-FEDERATION-001",
        "name": "联邦智能调度 Agent",
        "category": "infrastructure",
        "description": "跨节点联邦任务分发与结果聚合",
        "capabilities": ["节点注册", "任务分片", "结果聚合", "信誉评分"],
        "delivery_days": 7,
        "base_price": 29800,
        "dependencies": ["federation_engine", "node_handshake_engine"],
    },
]


def log(level: str, message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def evaluate_template(template: Dict[str, Any], stats: Dict[str, Any]) -> Dict[str, Any]:
    """评估模板能力成熟度。"""
    score = 50.0
    # 依赖组件可用性加分
    for dep in template.get("dependencies", []):
        dep_file = SERVICES_DIR / f"{dep}.py"
        if dep_file.exists():
            score += 10
    # 交付周期越短分越高
    score += max(0, 10 - template.get("delivery_days", 5))
    # 能力数量加分
    score += len(template.get("capabilities", [])) * 2
    template["maturity_score"] = round(min(100, score), 1)
    template["maturity_level"] = "成熟" if score >= 80 else "成长中" if score >= 60 else "孵化中"
    return template


def main():
    list_only = "--list" in sys.argv

    if list_only:
        if CATALOG_FILE.exists():
            print(CATALOG_FILE.read_text(encoding="utf-8"))
        else:
            print("暂无模板，请先运行构建")
        return 0

    log("INFO", "=" * 50)
    log("INFO", "Agent 服务市场引擎启动 (EVO-P2-002)")
    log("INFO", "=" * 50)

    # 获取内核统计
    try:
        from autonomous_kernel import AutonomousKernel
        kernel = AutonomousKernel()
        stats = kernel.get_stats()
    except Exception:
        stats = {}

    evaluated = [evaluate_template(t, stats) for t in AGENT_TEMPLATES]

    catalog = {
        "generated_at": datetime.now().isoformat(),
        "did_tag": DID_TAG,
        "total_templates": len(evaluated),
        "templates": evaluated,
    }
    CATALOG_FILE.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    log("INFO", f"生成 {len(evaluated)} 个 Agent 模板")
    for t in evaluated:
        log("INFO", f"  {t['id']}: {t['name']} | 成熟度: {t['maturity_score']} ({t['maturity_level']}) | ¥{t['base_price']}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(0)
