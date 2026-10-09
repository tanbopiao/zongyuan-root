#!/usr/bin/env python3
"""
真值遗忘机制 v1.0
功能: 评估真值价值，低价值自动归档到cold storage，防止真值通货膨胀
"""

import json
import sqlite3
import os
from datetime import datetime

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
COLD_DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway_cold.db"
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/truth_forgetting.log"

COLD_THRESHOLD_DAYS = 90
MIN_CORE_TRUTHS = 1000


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[" + timestamp + "] " + msg
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def init_cold_db():
    conn = sqlite3.connect(COLD_DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS cold_truths (
            id INTEGER PRIMARY KEY,
            truth_key TEXT UNIQUE,
            truth_value TEXT,
            truth_hash TEXT,
            category TEXT,
            node_id TEXT,
            original_created_at TEXT,
            archived_at TEXT,
            archive_reason TEXT,
            value_score REAL
        )
    """)
    conn.commit()
    conn.close()


def evaluate_truth(truth, current_time):
    score = 50.0
    key = truth.get("truth_key", "")
    category = truth.get("category", "")

    # 高价值类别加分
    if category in ["meta_rule", "axiom", "protocol", "theorem"]:
        score += 30
    if key.startswith("MR-") or key.startswith("meta_rule"):
        score += 40
    if key.startswith("SOP.") or key.startswith("BASELINE"):
        score += 20

    # 低价值减分
    if key.startswith("test.") or key.startswith("HEALTH_SAMPLE") or key.startswith("tmp_"):
        score -= 40

    # 时效性
    created_at = truth.get("created_at", "")
    if created_at:
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "").replace("+00:00", ""))
            age_days = (current_time - created).days
            if age_days > COLD_THRESHOLD_DAYS:
                score -= 30
            elif age_days > 30:
                score -= 10
        except Exception:
            pass

    return max(0, min(100, score))


def run_forgetting():
    log("=" * 60)
    log("真值遗忘机制启动")

    if not os.path.exists(DB_PATH):
        log("主数据库不存在")
        return

    init_cold_db()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM truths ORDER BY id")
    truths = [dict(row) for row in c.fetchall()]
    total = len(truths)
    log("当前真值总数: " + str(total))

    current_time = datetime.now()
    to_archive = []
    core_count = 0

    for truth in truths:
        score = evaluate_truth(truth, current_time)
        if score < 30:
            to_archive.append((truth, score))
        else:
            core_count += 1

    log("评估完成: 核心 " + str(core_count) + ", 候选归档 " + str(len(to_archive)))

    if core_count < MIN_CORE_TRUTHS:
        can_archive = max(0, total - MIN_CORE_TRUTHS)
        to_archive = to_archive[:can_archive]
        log("保护核心库: 最多归档 " + str(can_archive) + " 条")

    if not to_archive:
        log("无需归档，核心库已精炼")
        conn.close()
        return

    cold_conn = sqlite3.connect(COLD_DB_PATH)
    cold_c = cold_conn.cursor()
    archived = 0

    for truth, score in to_archive:
        try:
            cold_c.execute("""
                INSERT OR REPLACE INTO cold_truths
                (truth_key, truth_value, truth_hash, category, node_id,
                 original_created_at, archived_at, archive_reason, value_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                truth.get("truth_key"),
                truth.get("truth_value"),
                truth.get("truth_hash"),
                truth.get("category"),
                truth.get("node_id"),
                truth.get("created_at"),
                current_time.isoformat(),
                "价值分" + str(round(score, 1)) + "低于阈值，自动冷归档",
                score
            ))
            c.execute("DELETE FROM truths WHERE id = ?", (truth.get("id"),))
            archived += 1
        except Exception as e:
            log("归档失败 " + str(truth.get("truth_key")) + ": " + str(e))

    conn.commit()
    cold_conn.commit()

    c.execute("SELECT COUNT(*) FROM truths")
    remaining = c.fetchone()[0]
    cold_c.execute("SELECT COUNT(*) FROM cold_truths")
    cold_total = cold_c.fetchone()[0]

    log("归档完成: 归档" + str(archived) + "条, 主库剩余" + str(remaining) + "条, 冷存储" + str(cold_total) + "条")
    conn.close()
    cold_conn.close()
    log("=" * 60)


if __name__ == "__main__":
    run_forgetting()
