#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT MR-013 真值体系统一
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001

定位：统一所有真值的分类、格式、质量标准，消除分类混乱。

核心功能：
  1. 九大元类分类体系 - 公理/定理/方法/数据/案例/决策/创意/风险/协议
  2. 特殊类 - 元法则(meta_rule)/锁档(lock)/待分类(unclassified)
  3. 分类迁移工具 - 129个旧分类→统一分类，先备份再迁移
  4. 质量评分器 - 来源可信度/逻辑一致性/时效性/置信度
  5. 一致性校验服务 - 定期检查分类一致性，异常自动修正
  6. 统计报告 - 分类统一后的完整统计

技术设计：
  - 直接操作9120 SQLite数据库
  - 迁移前自动备份
  - 支持dry-run模式（只统计不修改）
  - 常驻服务模式：每小时校验一次
"""

import os
import sys
import json
import time
import sqlite3
import logging
import hashlib
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# ============================================================
# 配置
# ============================================================
CONFIG = {
    "db_path": "/opt/ZONGYUAN-ROOT/data/memory_gateway.db",
    "backup_dir": "/opt/ZONGYUAN-ROOT/data/backups",
    "log_file": "/opt/ZONGYUAN-ROOT/ops/mr013_truth_unify/mr013.log",
    "audit_log": "/opt/ZONGYUAN-ROOT/ops/mr013_truth_unify/audit.jsonl",
    "state_file": "/opt/ZONGYUAN-ROOT/ops/mr013_truth_unify/state.json",
    "check_interval": 3600,  # 一致性校验间隔（秒）
    "node_id": "mr013-truth-unify",
}

# ============================================================
# 九大元类分类体系
# ============================================================
META_CLASSES = {
    "axiom": {
        "name": "公理类",
        "name_en": "Axiom",
        "description": "不证自明的基本真理、体系基础假设、世界观、根本原则",
        "priority": 1,
    },
    "theorem": {
        "name": "定理类",
        "name_en": "Theorem",
        "description": "基于公理推导出来的结论、规律、理论、因果关系",
        "priority": 2,
    },
    "method": {
        "name": "方法类",
        "name_en": "Method",
        "description": "操作方法、流程、算法、SOP、协议实现、工具、自动化",
        "priority": 3,
    },
    "data": {
        "name": "数据类",
        "name_en": "Data",
        "description": "原始数据、统计数据、测量结果、观察快照、状态、审计",
        "priority": 4,
    },
    "case": {
        "name": "案例类",
        "name_en": "Case",
        "description": "具体案例、实例、事件记录、项目、部署、资产、成果",
        "priority": 5,
    },
    "decision": {
        "name": "决策类",
        "name_en": "Decision",
        "description": "决策记录、选择、方案、提案、策略、待办",
        "priority": 6,
    },
    "creative": {
        "name": "创意类",
        "name_en": "Creative",
        "description": "创意、想法、设计、架构、产品、白皮书、文档",
        "priority": 7,
    },
    "risk": {
        "name": "风险类",
        "name_en": "Risk",
        "description": "风险识别、威胁、问题、异常、事件、安全",
        "priority": 8,
    },
    "protocol": {
        "name": "协议类",
        "name_en": "Protocol",
        "description": "协议、规范、标准、接口定义、规则",
        "priority": 9,
    },
}

# 特殊类（优先级最高，不参与九大元类）
SPECIAL_CLASSES = {
    "meta_rule": {
        "name": "元法则",
        "name_en": "Meta Rule",
        "description": "体系运行的根本法则，优先级高于一切",
        "priority": 0,
    },
    "lock": {
        "name": "锁档",
        "name_en": "Lock",
        "description": "已锁档的不可变真值，禁止修改",
        "priority": 0,
    },
    "unclassified": {
        "name": "待分类",
        "name_en": "Unclassified",
        "description": "需要语义分类的真值，待MR-010/MR-014处理",
        "priority": 10,
    },
}

# 所有有效分类
ALL_CLASSES = {**META_CLASSES, **SPECIAL_CLASSES}

# ============================================================
# 旧分类→新分类映射规则（129个旧分类）
# ============================================================
CATEGORY_MAPPING = {
    # === M1-M9 九层架构 ===
    "M1": "creative",       # 算法架构层 → 创意类
    "M2": "theorem",        # （推断为理论层）→ 定理类
    "M3": "protocol",       # 元层协议层 → 协议类
    "M4": "theorem",        # 理论体系层 → 定理类
    "M5": "creative",       # 产品体系层 → 创意类
    "M6": "method",         # （推断为方法层）→ 方法类
    "M7": "method",         # 自动化调度层 → 方法类
    "M8": "risk",           # （推断为风险层）→ 风险类
    "M9": "meta_rule",      # 元秩序基底层 → 元法则（特殊类）

    # === 元法则相关 ===
    "meta_rule": "meta_rule",
    "metalaw": "meta_rule",
    "META_RULE": "meta_rule",
    "元规则": "meta_rule",
    "meta_law": "meta_rule",
    "meta_laws": "meta_rule",
    "constitution": "meta_rule",
    "governance": "meta_rule",
    "system_rule": "meta_rule",
    "tianyuan_law": "meta_rule",
    "meta": "meta_rule",

    # === 锁档相关 ===
    "lock": "lock",
    "global_lock": "lock",
    "meta_lock": "lock",

    # === 观察/数据/状态 ===
    "observation": "data",
    "status": "data",
    "system": "data",
    "system_snapshot": "data",
    "system.ledger": "data",
    "state": "data",
    "kernel_state": "data",
    "snapshot": "data",
    "baseline": "data",
    "audit": "data",
    "security_audit": "data",
    "stability_measure": "data",
    "classification": "data",
    "evaluation": "data",
    "benchmark": "data",
    "report": "data",
    "daily_summary": "data",
    "log_summary": "data",
    "feedback": "data",
    "health": "data",
    "info": "data",
    "ledger": "data",
    "node": "data",
    "node_onboard_scan": "data",
    "scan": "data",
    "test": "data",
    "test_result": "data",
    "integration_test": "data",
    "selftest": "data",
    "trace": "data",
    "checkpoint": "data",

    # === 方法/流程/工具 ===
    "nl2action": "method",
    "methodology": "method",
    "optimization": "method",
    "monitoring": "method",
    "ops": "method",
    "tool": "method",
    "configuration": "method",
    "config": "method",
    "CONFIG_CHANGE": "method",
    "operator": "method",
    "algorithm": "method",
    "engineering": "method",
    "mechanism": "method",
    "system.mechanism": "method",
    "sop": "method",
    "service": "method",
    "task": "method",
    "sync": "method",
    "quality_control": "method",
    "catalog": "method",
    "knowledge_graph": "method",
    "closed_loop": "method",
    "self-healing": "method",
    "self_reflection": "method",
    "evolution": "method",
    "truth_dedup": "method",

    # === 案例/项目/部署/资产 ===
    "deployment": "case",
    "deployment_trace": "case",
    "MR-007_DEPLOYMENT": "case",
    "MR008_DEPLOY": "case",
    "asset": "case",
    "artifact": "case",
    "website_asset": "case",
    "ip_asset": "case",
    "asset_provenance": "case",
    "achievement": "case",
    "milestone": "case",
    "phase": "case",
    "fix": "case",
    "project": "case",
    "local_dev": "case",
    "local.windows": "case",
    "local": "case",
    "commercial": "case",
    "lesson": "case",

    # === 决策/策略/提案 ===
    "decision": "decision",
    "strategy": "decision",
    "proposal": "decision",
    "todo": "decision",
    "meta_plan": "decision",

    # === 创意/设计/架构/产品 ===
    "architecture": "creative",
    "architecture_model": "creative",
    "cognitive_architecture": "creative",
    "arch": "creative",
    "product": "creative",
    "design": "creative",
    "whitepaper": "creative",
    "doc": "creative",
    "visualization": "creative",

    # === 风险/问题/安全 ===
    "incident": "risk",
    "issue": "risk",
    "security": "risk",
    "anomaly_detection": "risk",

    # === 定理/理论/因果 ===
    "causal": "theorem",
    "mathematics": "theorem",
    "truth": "theorem",
    "predictive": "theorem",

    # === 公理/根本 ===
    "root": "axiom",
    "sovereignty": "axiom",
    "worldview": "axiom",
    "autonomy": "axiom",

    # === 协议/标准 ===
    "protocol": "protocol",
    "standard": "protocol",
}

# ============================================================
# 日志
# ============================================================
def setup_logging():
    os.makedirs(os.path.dirname(CONFIG["log_file"]), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(CONFIG["log_file"]),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("mr013")

logger = setup_logging()

# ============================================================
# 数据库操作
# ============================================================
class TruthDatabase:
    """真值数据库操作"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def backup(self, backup_dir: str) -> str:
        """备份数据库"""
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"memory_gateway_before_mr013_{timestamp}.db")
        shutil.copy2(self.db_path, backup_path)
        logger.info(f"数据库已备份: {backup_path}")
        return backup_path

    def get_category_stats(self) -> List[Tuple[str, int]]:
        """获取分类统计"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(NULLIF(category, ''), '(无分类)') as cat, COUNT(*) as cnt
            FROM truths GROUP BY category ORDER BY cnt DESC
        """)
        stats = [(row["cat"], row["cnt"]) for row in cursor.fetchall()]
        conn.close()
        return stats

    def get_truths_by_category(self, category: str, limit: int = None) -> List[Dict]:
        """获取指定分类的真值"""
        conn = self._get_conn()
        cursor = conn.cursor()
        if category == "(无分类)":
            query = "SELECT * FROM truths WHERE category IS NULL OR category=''"
        else:
            query = "SELECT * FROM truths WHERE category=?"
        if limit:
            query += f" LIMIT {limit}"
        if category == "(无分类)":
            cursor.execute(query)
        else:
            cursor.execute(query, (category,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def migrate_category(self, old_category: str, new_category: str) -> int:
        """迁移分类"""
        conn = self._get_conn()
        cursor = conn.cursor()
        if old_category == "(无分类)":
            cursor.execute("UPDATE truths SET category=? WHERE category IS NULL OR category=''", (new_category,))
        else:
            cursor.execute("UPDATE truths SET category=? WHERE category=?", (new_category, old_category))
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count

    def get_total_count(self) -> int:
        """获取真值总数"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM truths")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_unclassified_count(self) -> int:
        """获取待分类数量"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM truths WHERE category='unclassified' OR category IS NULL OR category=''")
        count = cursor.fetchone()[0]
        conn.close()
        return count


# ============================================================
# 质量评分器
# ============================================================
class QualityScorer:
    """真值质量评分器"""

    @staticmethod
    def score_truth(truth: Dict) -> Dict:
        """对单条真值计算质量分"""
        score = 0.0
        details = {}

        # 1. 来源可信度 (25分)
        node_id = truth.get("node_id", "")
        if node_id in ["cloud-main-kernel-001", "zongyuan-cloud-001", "mr010-dual-compute-scheduler"]:
            source_score = 25
        elif node_id in ["DOUBAO-CLOUD-001", "doubao-main-agent-001"]:
            source_score = 20
        elif node_id and node_id != "unknown":
            source_score = 15
        else:
            source_score = 5
        details["source"] = source_score
        score += source_score

        # 2. 逻辑一致性 (25分)
        value = truth.get("truth_value", "")
        try:
            parsed = json.loads(value) if value else {}
            if isinstance(parsed, dict) and len(parsed) > 2:
                logic_score = 25
            elif isinstance(parsed, dict):
                logic_score = 20
            elif isinstance(parsed, list) and len(parsed) > 0:
                logic_score = 20
            else:
                logic_score = 15
        except (json.JSONDecodeError, TypeError):
            if len(str(value)) > 50:
                logic_score = 15
            else:
                logic_score = 10
        details["logic"] = logic_score
        score += logic_score

        # 3. 时效性 (25分)
        updated_at = truth.get("updated_at", 0)
        if updated_at:
            age_days = (time.time() - updated_at) / 86400
            if age_days < 1:
                time_score = 25
            elif age_days < 7:
                time_score = 20
            elif age_days < 30:
                time_score = 15
            elif age_days < 90:
                time_score = 10
            else:
                time_score = 5
        else:
            time_score = 5
        details["timeliness"] = time_score
        score += time_score

        # 4. 分类置信度 (25分)
        category = truth.get("category", "")
        if category in ALL_CLASSES:
            cat_score = 25
        elif category:
            cat_score = 15
        else:
            cat_score = 0
        details["classification"] = cat_score
        score += cat_score

        # 等级
        if score >= 90:
            grade = "A"
        elif score >= 75:
            grade = "B"
        elif score >= 60:
            grade = "C"
        elif score >= 40:
            grade = "D"
        else:
            grade = "E"

        return {
            "score": round(score, 1),
            "grade": grade,
            "details": details,
        }


# ============================================================
# 分类迁移引擎
# ============================================================
class MigrationEngine:
    """分类迁移引擎"""

    def __init__(self, db: TruthDatabase):
        self.db = db

    def plan_migration(self) -> Dict:
        """制定迁移计划（dry-run，只统计不修改）"""
        logger.info("=== 制定分类迁移计划 ===")
        stats = self.db.get_category_stats()
        total = self.db.get_total_count()

        plan = {
            "total_truths": total,
            "old_categories": len(stats),
            "migrations": [],
            "unmapped": [],
            "summary": {},
        }

        mapped_count = 0
        for old_cat, count in stats:
            if old_cat == "(无分类)":
                new_cat = "unclassified"
                plan["migrations"].append({
                    "old": old_cat, "new": new_cat, "count": count,
                    "note": "无分类→待分类"
                })
                mapped_count += count
            elif old_cat in CATEGORY_MAPPING:
                new_cat = CATEGORY_MAPPING[old_cat]
                plan["migrations"].append({
                    "old": old_cat, "new": new_cat, "count": count
                })
                mapped_count += count
            else:
                plan["unmapped"].append({"category": old_cat, "count": count})
                # 未映射的也归为待分类
                plan["migrations"].append({
                    "old": old_cat, "new": "unclassified", "count": count,
                    "note": "未映射→待分类"
                })
                mapped_count += count

        # 按新分类汇总
        new_summary = {}
        for m in plan["migrations"]:
            new_cat = m["new"]
            new_summary[new_cat] = new_summary.get(new_cat, 0) + m["count"]

        plan["summary"] = dict(sorted(new_summary.items(), key=lambda x: -x[1]))
        plan["mapped_count"] = mapped_count
        plan["unmapped_count"] = len(plan["unmapped"])

        logger.info(f"真值总数: {total}")
        logger.info(f"旧分类数: {len(stats)}")
        logger.info(f"未映射分类: {len(plan['unmapped'])}")
        logger.info(f"新分类分布: {json.dumps(plan['summary'], ensure_ascii=False)}")

        return plan

    def execute_migration(self, backup_dir: str = None) -> Dict:
        """执行迁移"""
        logger.info("=== 执行分类迁移 ===")

        # 1. 备份
        if backup_dir:
            backup_path = self.db.backup(backup_dir)
        else:
            backup_path = self.db.backup(CONFIG["backup_dir"])

        # 2. 制定计划
        plan = self.plan_migration()

        # 3. 执行迁移
        results = []
        total_migrated = 0
        for migration in plan["migrations"]:
            old = migration["old"]
            new = migration["new"]
            count = self.db.migrate_category(old, new)
            results.append({"old": old, "new": new, "count": count})
            total_migrated += count
            if count > 0:
                logger.info(f"  迁移: {old} → {new} ({count}条)")

        # 4. 验证
        new_stats = self.db.get_category_stats()
        new_total = self.db.get_total_count()

        result = {
            "backup_path": backup_path,
            "total_before": plan["total_truths"],
            "total_after": new_total,
            "total_migrated": total_migrated,
            "old_categories": plan["old_categories"],
            "new_categories": len(new_stats),
            "results": results,
            "new_distribution": dict(new_stats),
        }

        logger.info(f"迁移完成: {total_migrated}条真值, {plan['old_categories']}→{len(new_stats)}个分类")

        return result


# ============================================================
# 一致性校验服务
# ============================================================
class ConsistencyChecker:
    """分类一致性校验器"""

    def __init__(self, db: TruthDatabase):
        self.db = db

    def check(self) -> Dict:
        """执行一致性校验"""
        logger.info("=== 执行分类一致性校验 ===")
        stats = self.db.get_category_stats()
        total = self.db.get_total_count()

        issues = []

        # 1. 检查是否有无效分类
        for cat, count in stats:
            if cat not in ALL_CLASSES and cat != "(无分类)":
                issues.append({
                    "type": "invalid_category",
                    "category": cat,
                    "count": count,
                    "suggestion": f"迁移到有效分类或标记为unclassified",
                })

        # 2. 检查无分类
        unclassified = self.db.get_unclassified_count()
        if unclassified > 0:
            issues.append({
                "type": "unclassified",
                "count": unclassified,
                "suggestion": "使用MR-010进行语义分类",
            })

        # 3. 检查分类分布是否合理（某个分类超过50%可能有问题）
        for cat, count in stats:
            if total > 0 and count / total > 0.5:
                issues.append({
                    "type": "category_imbalance",
                    "category": cat,
                    "count": count,
                    "percentage": round(count / total * 100, 1),
                    "suggestion": "检查是否分类过于集中",
                })

        result = {
            "timestamp": datetime.now().isoformat(),
            "total_truths": total,
            "categories": len(stats),
            "valid_categories": len([c for c, _ in stats if c in ALL_CLASSES]),
            "issues": issues,
            "issue_count": len(issues),
            "status": "pass" if len(issues) == 0 else "warning",
        }

        logger.info(f"校验完成: {len(issues)}个问题, 状态={result['status']}")
        return result

    def auto_fix(self, check_result: Dict) -> int:
        """自动修复可修复的问题"""
        fixed = 0
        for issue in check_result.get("issues", []):
            if issue["type"] == "invalid_category":
                old = issue["category"]
                if old in CATEGORY_MAPPING:
                    new = CATEGORY_MAPPING[old]
                else:
                    new = "unclassified"
                count = self.db.migrate_category(old, new)
                fixed += count
                logger.info(f"  自动修复: {old} → {new} ({count}条)")
        return fixed


# ============================================================
# 主程序
# ============================================================
def cmd_plan():
    """命令：制定迁移计划（dry-run）"""
    db = TruthDatabase(CONFIG["db_path"])
    engine = MigrationEngine(db)
    plan = engine.plan_migration()
    print(json.dumps(plan, ensure_ascii=False, indent=2))


def cmd_execute():
    """命令：执行迁移"""
    db = TruthDatabase(CONFIG["db_path"])
    engine = MigrationEngine(db)
    result = engine.execute_migration(CONFIG["backup_dir"])
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_check():
    """命令：一致性校验"""
    db = TruthDatabase(CONFIG["db_path"])
    checker = ConsistencyChecker(db)
    result = checker.check()
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_stats():
    """命令：查看分类统计"""
    db = TruthDatabase(CONFIG["db_path"])
    stats = db.get_category_stats()
    total = db.get_total_count()
    print(f"真值总数: {total}")
    print(f"分类数: {len(stats)}")
    print()
    for cat, count in stats:
        pct = count / total * 100 if total > 0 else 0
        valid = "✓" if cat in ALL_CLASSES else "✗"
        print(f"  {valid} {cat:25s}: {count:4d} ({pct:5.1f}%)")


def cmd_daemon():
    """命令：常驻运行（每小时校验一次）"""
    db = TruthDatabase(CONFIG["db_path"])
    checker = ConsistencyChecker(db)

    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════╗")
    logger.info("║  MR-013 真值体系统一服务启动                         ║")
    logger.info("║  校验间隔: 每小时                                      ║")
    logger.info("║  功能: 分类一致性校验 + 自动修复                      ║")
    logger.info("╚══════════════════════════════════════════════════════╝")
    logger.info("")

    while True:
        try:
            result = checker.check()
            if result["issue_count"] > 0:
                fixed = checker.auto_fix(result)
                logger.info(f"自动修复了{fixed}条真值")
            time.sleep(CONFIG["check_interval"])
        except Exception as e:
            logger.error(f"校验循环异常: {e}")
            time.sleep(60)


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MR-013 真值体系统一")
    parser.add_argument("command", choices=["plan", "execute", "check", "stats", "daemon"],
                        help="plan=制定迁移计划(dry-run), execute=执行迁移, check=一致性校验, stats=查看统计, daemon=常驻运行")
    args = parser.parse_args()

    if args.command == "plan":
        cmd_plan()
    elif args.command == "execute":
        cmd_execute()
    elif args.command == "check":
        cmd_check()
    elif args.command == "stats":
        cmd_stats()
    elif args.command == "daemon":
        cmd_daemon()
