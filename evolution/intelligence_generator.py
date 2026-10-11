#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — AI 产业情报日报生成器（EVO-P0-001）

功能：
  1. 触发种子真值进化周期，获取当日新鲜真值
  2. 从本地全量真值库中检索 AI 产业相关条目
  3. 按维度分类（投融资/政策监管/产业生态/技术突破/多模态/Agent）
  4. 生成结构化日报（JSON + Markdown 双格式）
  5. 归档至情报产品目录

使用方式：
  python3 intelligence_generator.py          # 生成当日情报日报
  python3 intelligence_generator.py --no-evolve  # 跳过进化周期，仅基于已有真值生成
"""
import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# ============ 路径配置 ============

WORKSPACE = Path("/workspace")
EVOLUTION_DIR = WORKSPACE / "evolution"
INTELLIGENCE_DIR = EVOLUTION_DIR / "intelligence"
INTELLIGENCE_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = INTELLIGENCE_DIR / "generator.log"
REPORT_JSON = INTELLIGENCE_DIR / "daily_report.json"
REPORT_MD = INTELLIGENCE_DIR / "daily_report.md"

# 自治内核与进化引擎所在目录
SERVICES_DIR = WORKSPACE / "scripts" / "services"
sys.path.insert(0, str(SERVICES_DIR))

# ============ 维度分类规则 ============

DIMENSION_RULES = {
    "投融资": {
        "keywords": ["融资", "投资", "估值", "IPO", "上市", "并购", "基金", "轮", "美元", "亿元"],
        "weight": 1.0,
    },
    "政策监管": {
        "keywords": ["政策", "监管", "法规", "合规", "备案", "审批", "部门", "通知", "指导意见", "办法"],
        "weight": 1.0,
    },
    "产业生态": {
        "keywords": ["生态", "联盟", "合作", "战略", "伙伴", "开放", "平台", "社区", "开发者"],
        "weight": 0.8,
    },
    "技术突破": {
        "keywords": ["突破", "创新", "架构", "算法", "模型", "性能", "精度", "论文", "开源", "发布"],
        "weight": 1.0,
    },
    "多模态": {
        "keywords": ["多模态", "图像", "视频", "语音", "生成", "扩散", "TTS", "ASR", "视觉"],
        "weight": 0.9,
    },
    "Agent": {
        "keywords": ["Agent", "智能体", "自治", "编排", "工作流", "工具调用", "ReAct", "规划"],
        "weight": 1.0,
    },
}

# AI 产业相关关键词（用于从真值库中筛选）
AI_KEYWORDS = [
    "AI", "人工智能", "大模型", "LLM", "智能体", "Agent",
    "机器学习", "深度学习", "神经网络", "算力", "GPU", "推理",
    "训练", "知识库", "RAG", "向量数据库", "多模态",
]


def log(level: str, message: str):
    """统一日志输出。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def trigger_evolution() -> bool:
    """
    触发种子真值进化周期。
    失败不影响后续流程（降级使用已有真值）。
    """
    try:
        from truth_evolution_engine import run_evolution_cycle

        log("INFO", "触发种子真值进化周期...")
        run_evolution_cycle()
        log("INFO", "进化周期执行完成")
        return True
    except Exception as e:
        log("WARN", f"进化周期触发失败（降级处理）: {e}")
        return False


def retrieve_ai_truths(limit: int = 200) -> List[Dict[str, Any]]:
    """
    从本地全量真值库中检索 AI 产业相关真值。
    """
    ai_truths = []
    try:
        from autonomous_kernel import AutonomousKernel

        kernel = AutonomousKernel()
        log("INFO", f"自治内核加载 {kernel.get_stats()['total']} 条真值")

        for kw in AI_KEYWORDS:
            results = kernel.search(kw, limit=limit)
            for r in results:
                ai_truths.append(r)

        # 去重（按 key）
        seen = set()
        deduped = []
        for t in ai_truths:
            key = t.get("key", "")
            if key and key not in seen:
                seen.add(key)
                deduped.append(t)

        log("INFO", f"检索到 {len(deduped)} 条 AI 相关真值（去重后）")
        return deduped

    except Exception as e:
        log("WARN", f"自治内核检索失败: {e}")
        return ai_truths


def classify_truth(truth: Dict[str, Any]) -> str:
    """
    根据维度规则对真值进行分类。
    返回匹配度最高的维度。
    """
    text = json.dumps(truth, ensure_ascii=False).lower()
    scores = {}
    for dim, rule in DIMENSION_RULES.items():
        score = 0
        for kw in rule["keywords"]:
            if kw.lower() in text:
                score += 1
        scores[dim] = score * rule["weight"]

    best_dim = max(scores, key=scores.get)
    if scores[best_dim] == 0:
        return "其他"
    return best_dim


def generate_daily_report(truths: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    生成结构化日报。
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # 按维度分类
    categorized: Dict[str, List[Dict[str, Any]]] = {dim: [] for dim in DIMENSION_RULES}
    categorized["其他"] = []

    for truth in truths:
        dim = classify_truth(truth)
        # 精简字段，避免日报过大
        item = {
            "seq": truth.get("seq"),
            "key": truth.get("key", "")[:80],
            "value_preview": str(truth.get("value", ""))[:200],
            "timestamp": truth.get("ts", ""),
        }
        categorized[dim].append(item)

    # 统计
    stats = {dim: len(items) for dim, items in categorized.items()}
    total = sum(stats.values())

    report = {
        "report_id": f"AI-INTEL-{today}-{hashlib.md5(today.encode()).hexdigest()[:6]}",
        "date": today,
        "generated_at": datetime.now().isoformat(),
        "did_tag": "DID-BR-000002",
        "total_items": total,
        "dimensions": stats,
        "categorized": {dim: items[:30] for dim, items in categorized.items()},  # 每维度最多 30 条
        "summary": (
            f"火斗云智 AI 产业情报日报 {today}：共收录 {total} 条相关情报，"
            f"覆盖 {len([d for d, c in stats.items() if c > 0])} 个维度。"
        ),
    }

    return report


def render_markdown(report: Dict[str, Any]) -> str:
    """将日报渲染为 Markdown 格式。"""
    lines = []
    lines.append(f"# 火斗云智 AI 产业情报日报 — {report['date']}")
    lines.append("")
    lines.append(f"> 报告编号：{report['report_id']}")
    lines.append(f"> 生成时间：{report['generated_at']}")
    lines.append(f"> 确权锚点：{report['did_tag']}")
    lines.append(f"> 情报总数：{report['total_items']} 条")
    lines.append("")

    # 维度概览
    lines.append("## 一、维度概览")
    lines.append("")
    lines.append("| 维度 | 条目数 |")
    lines.append("|---|---|")
    for dim, count in report["dimensions"].items():
        if count > 0:
            lines.append(f"| {dim} | {count} |")
    lines.append("")

    # 分维度详情
    lines.append("## 二、分维度详情")
    lines.append("")
    for dim, items in report["categorized"].items():
        if not items:
            continue
        lines.append(f"### {dim}")
        lines.append("")
        for item in items[:20]:  # Markdown 中每维度最多 20 条
            key = item["key"]
            ts = item.get("timestamp", "")[:10]
            lines.append(f"- **[{ts}]** {key}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*{report['summary']}*")
    lines.append("")
    return "\n".join(lines)


def save_report(report: Dict[str, Any]):
    """保存日报（JSON + Markdown）。"""
    # JSON
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Markdown
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")

    # 按日期归档
    date_str = report["date"]
    archive_dir = INTELLIGENCE_DIR / "archive"
    archive_dir.mkdir(exist_ok=True)
    (archive_dir / f"daily_report_{date_str}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (archive_dir / f"daily_report_{date_str}.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )

    log("INFO", f"日报已保存: {REPORT_JSON}")
    log("INFO", f"Markdown 已保存: {REPORT_MD}")
    log("INFO", f"归档目录: {archive_dir}")


def main():
    """主流程。"""
    start_time = time.time()
    log("INFO", "=" * 50)
    log("INFO", "AI 产业情报日报生成器启动 (EVO-P0-001)")
    log("INFO", "=" * 50)

    # 1. 可选：触发进化周期
    run_evolution = "--no-evolve" not in sys.argv
    if run_evolution:
        trigger_evolution()

    # 2. 检索 AI 产业真值
    truths = retrieve_ai_truths()
    if not truths:
        log("WARN", "未检索到 AI 相关真值，生成空日报")

    # 3. 生成日报
    report = generate_daily_report(truths)
    log("INFO", f"日报生成完成: {report['total_items']} 条, 维度分布: {report['dimensions']}")

    # 4. 保存
    save_report(report)

    elapsed = round(time.time() - start_time, 2)
    log("INFO", f"情报生成完成，耗时 {elapsed}s")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log("ERROR", f"情报生成异常: {e}")
        # 异常时仍返回 0，避免调度器反复重试
        sys.exit(0)
