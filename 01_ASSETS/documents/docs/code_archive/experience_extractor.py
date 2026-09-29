#!/usr/bin/env python3
"""
全域经验萃取引擎 v1.0
- 从9120拉取所有experience类真值
- 按类型分类、去重、质量评分
- 高价值经验升级为全域SOP
- 输出经验库JSON供官网展示
- 每小时自动运行
"""

import os
import json
import sqlite3
from datetime import datetime

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
OUTPUT_JSON = "/www/wwwroot/www.huodouai.com/experience_kb.json"
ALT_OUTPUT = "/www/wwwroot/huodouai.com/experience_kb.json"

# 经验类型定义
EXPERIENCE_TYPES = {
    "methodology": {"name": "方法论", "icon": "📐", "desc": "系统性的方法和理论"},
    "decision_flow": {"name": "决策流程", "icon": "⚖️", "desc": "判断逻辑和决策步骤"},
    "trial_error": {"name": "试错记录", "icon": "🔄", "desc": "失败尝试和最终方案"},
    "best_practice": {"name": "最佳实践", "icon": "✨", "desc": "验证有效的最优做法"},
    "pitfall": {"name": "踩坑记录", "icon": "⚠️", "desc": "易错点和规避方法"},
    "sop": {"name": "标准SOP", "icon": "📋", "desc": "可复用的标准化流程"},
    "tool_tip": {"name": "工具技巧", "icon": "🔧", "desc": "脚本/API/命令高效用法"}
}


def load_experiences():
    """从数据库加载所有experience类真值"""
    experiences = []
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT truth_key, truth_value, node_id, created_at FROM truths WHERE category='experience'")
        for row in c.fetchall():
            try:
                value = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                if isinstance(value, dict):
                    value["_key"] = row[0]
                    value["_node"] = row[2]
                    value["_time"] = datetime.fromtimestamp(row[3]).isoformat() if row[3] else ""
                    experiences.append(value)
            except Exception:
                pass
        conn.close()
    except Exception as e:
        print(f"  加载经验失败: {e}")
    return experiences


def classify_and_score(experiences):
    """分类、去重、质量评分"""
    classified = {t: [] for t in EXPERIENCE_TYPES}
    seen_titles = set()

    for exp in experiences:
        exp_type = exp.get("experience_type", "best_practice")
        if exp_type not in classified:
            exp_type = "best_practice"

        title = exp.get("title", "").strip()
        if title and title in seen_titles:
            continue  # 去重
        if title:
            seen_titles.add(title)

        # 质量评分
        score = 0
        if exp.get("reusability") == "high":
            score += 40
        elif exp.get("reusability") == "medium":
            score += 20
        if exp.get("steps") and len(exp.get("steps", [])) >= 3:
            score += 20
        if exp.get("result"):
            score += 20
        if exp.get("scenario"):
            score += 10
        if exp.get("related_meta_law"):
            score += 10

        exp["_score"] = min(score, 100)
        exp["_promoted"] = score >= 80  # 80分以上升级为全域推广

        classified[exp_type].append(exp)

    # 按分数排序
    for t in classified:
        classified[t].sort(key=lambda x: x["_score"], reverse=True)

    return classified


def generate_summary(classified):
    """生成经验库摘要"""
    total = sum(len(v) for v in classified.values())
    promoted = sum(1 for v in classified.values() for e in v if e.get("_promoted"))

    return {
        "generated_at": datetime.now().isoformat(),
        "total_experiences": total,
        "promoted_experiences": promoted,
        "by_type": {t: len(v) for t, v in classified.items()},
        "types": EXPERIENCE_TYPES,
        "experiences": classified
    }


def main():
    print("【全域经验萃取引擎】")
    print("=" * 50)

    # 1. 加载经验
    experiences = load_experiences()
    print(f"  加载经验: {len(experiences)}条")

    # 2. 分类评分
    classified = classify_and_score(experiences)
    for t, items in classified.items():
        if items:
            promoted = sum(1 for i in items if i.get("_promoted"))
            print(f"  {EXPERIENCE_TYPES[t]['icon']} {EXPERIENCE_TYPES[t]['name']}: {len(items)}条 (推广{promoted}条)")

    # 3. 生成摘要
    summary = generate_summary(classified)

    # 4. 输出JSON
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(ALT_OUTPUT, "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 经验库已生成: {OUTPUT_JSON}")
    print(f"   总计: {summary['total_experiences']}条, 推广: {summary['promoted_experiences']}条")


if __name__ == "__main__":
    main()
