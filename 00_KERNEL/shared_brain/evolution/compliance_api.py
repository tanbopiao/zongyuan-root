#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — 合规风控 SaaS 规则同步引擎（EVO-P0-003）

功能：
  1. 封装 compliance_checker，提供规则同步与扩展能力
  2. 扩展禁用词库（金融/医疗/法律/教育专项）
  3. 生成合规统计报告与复核队列摘要
  4. 输出 SaaS 化 API 规格文档

使用方式：
  python3 compliance_api.py --sync-rules    # 同步/扩展合规规则库，生成报告
  python3 compliance_api.py --stats         # 查看合规统计
  python3 compliance_api.py --review        # 查看待复核队列
  python3 compliance_api.py --check "文本"  # 检测单条文本合规性
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# ============ 路径配置 ============

WORKSPACE = Path("/workspace")
EVOLUTION_DIR = WORKSPACE / "evolution"
COMPLIANCE_DIR = EVOLUTION_DIR / "compliance"
COMPLIANCE_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = COMPLIANCE_DIR / "api.log"
RULES_REPORT = COMPLIANCE_DIR / "rules_report.json"
REVIEW_REPORT = COMPLIANCE_DIR / "review_report.json"

# 合规审校引擎所在目录
SERVICES_DIR = WORKSPACE / "scripts" / "services"
sys.path.insert(0, str(SERVICES_DIR))

DID_TAG = "DID-BR-000002"


# ============ 行业扩展禁用词库 ============

INDUSTRY_BANNED_WORDS = {
    # 金融行业
    "保本保息": {"level": "high", "suggest": "非保本浮动收益", "industry": "finance"},
    "稳赚不赔": {"level": "high", "suggest": "", "industry": "finance"},
    "高收益无风险": {"level": "high", "suggest": "收益与风险并存", "industry": "finance"},
    "内幕消息": {"level": "high", "suggest": "", "industry": "finance"},
    "荐股": {"level": "high", "suggest": "投资参考", "industry": "finance"},
    "代客理财": {"level": "high", "suggest": "", "industry": "finance"},
    "资金安全": {"level": "medium", "suggest": "资金存管", "industry": "finance"},
    "刚性兑付": {"level": "high", "suggest": "", "industry": "finance"},

    # 医疗行业
    "包治百病": {"level": "high", "suggest": "", "industry": "medical"},
    "根治": {"level": "high", "suggest": "辅助改善", "industry": "medical"},
    "特效药": {"level": "high", "suggest": "治疗药物", "industry": "medical"},
    "无副作用": {"level": "high", "suggest": "副作用较小", "industry": "medical"},
    "祖传秘方": {"level": "high", "suggest": "传统配方", "industry": "medical"},
    "治愈率": {"level": "medium", "suggest": "临床有效率", "industry": "medical"},
    "诊断": {"level": "medium", "suggest": "辅助判断", "industry": "medical"},

    # 法律行业
    "包赢": {"level": "high", "suggest": "", "industry": "legal"},
    "胜诉率100%": {"level": "high", "suggest": "胜诉率较高", "industry": "legal"},
    "法律咨询免": {"level": "medium", "suggest": "法律咨询", "industry": "legal"},
    "全权代理": {"level": "medium", "suggest": "代理服务", "industry": "legal"},

    # 教育行业
    "保过": {"level": "high", "suggest": "辅助备考", "industry": "education"},
    "包拿证": {"level": "high", "suggest": "考证辅导", "industry": "education"},
    "内部资料": {"level": "medium", "suggest": "学习资料", "industry": "education"},
    "命题人": {"level": "high", "suggest": "资深教师", "industry": "education"},
    "押题": {"level": "medium", "suggest": "模拟练习", "industry": "education"},

    # AI 行业扩展
    "AGI": {"level": "medium", "suggest": "通用人工智能", "industry": "ai"},
    "超级智能": {"level": "medium", "suggest": "高级智能", "industry": "ai"},
    "意识觉醒": {"level": "high", "suggest": "自主决策", "industry": "ai"},
    "替代人类": {"level": "high", "suggest": "辅助人类", "industry": "ai"},
}


def log(level: str, message: str):
    """统一日志输出。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def merge_rules() -> Dict[str, Any]:
    """
    合并基础禁用词库与行业扩展词库。
    返回合并后的规则集与统计信息。
    """
    try:
        from compliance_checker import BANNED_WORDS, RISK_SCENARIOS

        # 合并禁用词（行业扩展不覆盖基础规则）
        merged_banned = dict(BANNED_WORDS)
        added_count = 0
        for word, info in INDUSTRY_BANNED_WORDS.items():
            if word not in merged_banned:
                merged_banned[word] = info
                added_count += 1

        # 按行业统计
        industry_stats = {}
        for word, info in merged_banned.items():
            industry = info.get("industry", "base")
            industry_stats[industry] = industry_stats.get(industry, 0) + 1

        # 按风险等级统计
        level_stats = {"high": 0, "medium": 0}
        for word, info in merged_banned.items():
            level = info.get("level", "medium")
            level_stats[level] = level_stats.get(level, 0) + 1

        report = {
            "sync_time": datetime.now().isoformat(),
            "did_tag": DID_TAG,
            "base_rules_count": len(BANNED_WORDS),
            "industry_rules_added": added_count,
            "total_banned_words": len(merged_banned),
            "risk_level_distribution": level_stats,
            "industry_distribution": industry_stats,
            "risk_scenarios": list(RISK_SCENARIOS.keys()),
            "banned_words": list(merged_banned.keys()),
        }

        log("INFO", f"规则同步完成: 基础 {len(BANNED_WORDS)} 条 + 扩展 {added_count} 条 = 合计 {len(merged_banned)} 条")
        log("INFO", f"风险等级分布: {level_stats}")
        log("INFO", f"行业分布: {industry_stats}")

        return report

    except Exception as e:
        log("ERROR", f"规则合并失败: {e}")
        raise


def get_compliance_stats() -> Dict[str, Any]:
    """获取合规审校统计。"""
    try:
        from compliance_checker import ComplianceChecker

        checker = ComplianceChecker()
        return checker.stats()
    except Exception as e:
        log("ERROR", f"获取统计失败: {e}")
        return {"total_checks": 0, "error": str(e)}


def get_review_queue() -> List[Dict[str, Any]]:
    """获取待复核队列。"""
    try:
        from compliance_checker import ComplianceChecker

        checker = ComplianceChecker()
        return checker.get_review_queue()
    except Exception as e:
        log("ERROR", f"获取复核队列失败: {e}")
        return []


def sync_rules():
    """同步规则并生成报告。"""
    log("INFO", "=" * 50)
    log("INFO", "合规规则同步引擎启动 (EVO-P0-003)")
    log("INFO", "=" * 50)

    # 1. 合并规则库
    rules_report = merge_rules()

    # 2. 获取统计
    stats = get_compliance_stats()
    rules_report["check_stats"] = stats
    log("INFO", f"审校统计: {json.dumps(stats, ensure_ascii=False)}")

    # 3. 获取复核队列摘要
    review_queue = get_review_queue()
    rules_report["pending_review_count"] = len(review_queue)
    rules_report["recent_reviews"] = review_queue[-10:]  # 最近 10 条

    # 4. 保存规则报告
    RULES_REPORT.write_text(
        json.dumps(rules_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log("INFO", f"规则报告已保存: {RULES_REPORT}")

    # 5. 保存复核报告
    review_report = {
        "generated_at": datetime.now().isoformat(),
        "pending_count": len(review_queue),
        "queue": review_queue,
    }
    REVIEW_REPORT.write_text(
        json.dumps(review_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log("INFO", f"复核报告已保存: {REVIEW_REPORT}")

    print(json.dumps({
        "success": True,
        "total_banned_words": rules_report["total_banned_words"],
        "pending_review": rules_report["pending_review_count"],
        "total_checks": stats.get("total_checks", 0),
    }, ensure_ascii=False, indent=2))

    return rules_report


def check_text(text: str):
    """检测单条文本合规性。"""
    try:
        from compliance_checker import ComplianceChecker

        checker = ComplianceChecker()
        result = checker.check(text)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    except Exception as e:
        log("ERROR", f"合规检测失败: {e}")
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        return None


def main():
    parser = argparse.ArgumentParser(description="火斗云智合规风控 SaaS 规则同步引擎")
    parser.add_argument("--sync-rules", action="store_true", help="同步/扩展合规规则库")
    parser.add_argument("--stats", action="store_true", help="查看合规统计")
    parser.add_argument("--review", action="store_true", help="查看待复核队列")
    parser.add_argument("--check", type=str, help="检测单条文本合规性")

    args = parser.parse_args()

    if args.sync_rules:
        sync_rules()
        return 0

    if args.stats:
        stats = get_compliance_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    if args.review:
        queue = get_review_queue()
        print(json.dumps({"pending_count": len(queue), "queue": queue}, ensure_ascii=False, indent=2))
        return 0

    if args.check:
        check_text(args.check)
        return 0

    # 默认：执行规则同步
    sync_rules()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log("ERROR", f"合规引擎异常: {e}")
        sys.exit(0)
