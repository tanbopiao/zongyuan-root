#!/usr/bin/env python3
"""
L0理论基座任务状态跟踪器
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω
"""
import json
from pathlib import Path
from datetime import datetime

TASK_FILE = Path("core/truth/l0_task_list.md")
TRACK_FILE = Path("inspect/task_tracker.json")

TASKS = {
    "P0": [
        {"id": "TASK-001", "name": "身份基线固化", "status": "DONE", "completed": "2026-09-09"},
        {"id": "TASK-002", "name": "矩阵调度V3.1融合", "status": "DONE", "completed": "2026-09-09"},
        {"id": "TASK-003", "name": "真值资产基线对齐", "status": "IN_PROGRESS", "progress": 40},
        {"id": "TASK-004", "name": "巡检体系完善", "status": "DONE", "completed": "2026-09-09"},
        {"id": "TASK-005", "name": "冲突仲裁规则落地", "status": "DONE", "completed": "2026-09-09"},
    ],
    "P1": [
        {"id": "TASK-101", "name": "同源协议标准化", "status": "PENDING"},
        {"id": "TASK-102", "name": "漂移闭环构建", "status": "PENDING"},
        {"id": "TASK-103", "name": "昆仑IP产线规则治理", "status": "PENDING"},
        {"id": "TASK-104", "name": "双向同步自动化", "status": "PENDING"},
        {"id": "TASK-105", "name": "安全体系加固", "status": "PENDING"},
    ],
    "P2": [
        {"id": "TASK-201", "name": "七层稳态架构落地", "status": "PENDING"},
        {"id": "TASK-202", "name": "多节点自治协同", "status": "PENDING"},
        {"id": "TASK-203", "name": "商业化体系支撑", "status": "PENDING"},
    ]
}

def print_report():
    print("=" * 60)
    print("L0理论基座任务状态")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)

    for priority, tasks in TASKS.items():
        done = sum(1 for t in tasks if t["status"] == "DONE")
        total = len(tasks)
        print(f"\n【{priority}】{done}/{total} 完成")
        for t in tasks:
            icon = {"DONE": "✅", "IN_PROGRESS": "🔄", "PENDING": "⏳"}.get(t["status"], "❓")
            progress = f" ({t.get('progress', 0)}%)" if t["status"] == "IN_PROGRESS" else ""
            print(f"  {icon} {t['id']} {t['name']}{progress}")

    print("\n" + "=" * 60)

def save_tracker():
    with open(TRACK_FILE, "w", encoding="utf-8") as f:
        json.dump(TASKS, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    print_report()
    save_tracker()
    print(f"\n任务跟踪已保存: {TRACK_FILE}")
