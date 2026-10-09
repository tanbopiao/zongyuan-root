#!/usr/bin/env python3
"""
真值分类优化脚本
批量重新分类1093条待分类真值（空+unclassified）
按内容关键词自动归类到九大元类
"""
import sqlite3
import json
import re
from datetime import datetime

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"

# 九大元类分类规则
CLASSIFY_RULES = {
    "axiom": ["公理", "axiom", "基础假设", "第一性原理", "元规则", "meta_rule", "MR-"],
    "theorem": ["定理", "theorem", "推论", "证明", "推导", "lemma", "命题"],
    "method": ["方法", "method", "流程", "步骤", "算法", "algorithm", "SOP", "操作", "技巧", "protocol"],
    "data": ["数据", "data", "统计", "指标", "数值", "测量", "采样", "dataset", "metrics"],
    "case": ["案例", "case", "实例", "示例", "example", "实战", "应用场景"],
    "decision": ["决策", "decision", "方案", "选择", "裁决", "评估", "推荐", "最优", "稳态"],
    "creative": ["创意", "creative", "设计", "构想", "灵感", "创新", "idea", "概念"],
    "risk": ["风险", "risk", "威胁", "隐患", "漏洞", "安全", "攻击", "防御", "告警", "异常"],
    "protocol": ["协议", "protocol", "规范", "标准", "接口", "契约", "约定", "确权", "DID"],
    "meta_law": ["元法则", "meta_law", "元法", "锁档", "MR-0", "MR-1"],
    "lock": ["锁档", "lock", "封存", "固化", "锚定", "anchor", "Merkle"],
    "observation": ["观察", "observation", "现象", "发现", "记录", "日志", "log", "监控"],
    "compute_injection": ["算力", "compute", "注入", "推理", "inference", "模型", "model", "LLM"],
    "guardian_report": ["守护", "guardian", "自愈", "healing", "巡检", "inspection", "健康检查"],
    "system_report": ["系统", "system", "报告", "report", "总结", "汇总", "状态", "status"],
    "evolution_record": ["进化", "evolution", "迭代", "优化", "improvement", "升级", "演化"],
    "stability_measure": ["稳态", "stability", "平衡", "均衡", "GEO", "晶格", "lattice"],
}

def classify_truth(key, value):
    """根据真值key和value内容分类"""
    text = (key + " " + str(value)).lower()
    
    # 先按key前缀匹配
    for cat, keywords in CLASSIFY_RULES.items():
        for kw in keywords:
            if kw.lower() in key.lower():
                return cat
    
    # 再按内容匹配
    scores = {}
    for cat, keywords in CLASSIFY_RULES.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > 0:
            scores[cat] = score
    
    if scores:
        return max(scores, key=scores.get)
    
    return "data"  # 默认归为data类

def main():
    print("=" * 60)
    print("  真值分类优化 - 批量重新分类")
    print("=" * 60)
    print()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 统计待分类真值
    c.execute("SELECT COUNT(*) FROM truths WHERE category IS NULL OR category = '' OR category = 'unclassified'")
    total = c.fetchone()[0]
    print(f"  待分类真值总数: {total}条")
    print()
    
    if total == 0:
        print("  ✅ 无待分类真值，无需优化")
        conn.close()
        return
    
    # 备份当前分类
    backup_file = f"/opt/ZONGYUAN-ROOT/data/truth_category_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    c.execute("SELECT id, truth_key, category FROM truths WHERE category IS NULL OR category = '' OR category = 'unclassified'")
    backup_data = [{"id": r[0], "truth_key": r[1], "old_category": r[2]} for r in c.fetchall()]
    with open(backup_file, "w") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 已备份到: {backup_file}")
    print()
    
    # 批量重新分类
    print("  开始批量重新分类...")
    c.execute("SELECT id, truth_key, truth_value FROM truths WHERE category IS NULL OR category = '' OR category = 'unclassified'")
    rows = c.fetchall()
    
    classify_result = {}
    updated = 0
    for row_id, key, value in rows:
        new_cat = classify_truth(key, value)
        classify_result[new_cat] = classify_result.get(new_cat, 0) + 1
        c.execute("UPDATE truths SET category = ? WHERE id = ?", (new_cat, row_id))
        updated += 1
        
        if updated % 100 == 0:
            print(f"    已处理: {updated}/{total}")
    
    conn.commit()
    
    print()
    print(f"  ✅ 分类完成: 共更新{updated}条真值")
    print()
    print("  分类结果统计:")
    for cat, count in sorted(classify_result.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}条")
    
    # 验证最终分类
    print()
    print("  最终全部分类统计:")
    c.execute("SELECT category, COUNT(*) FROM truths GROUP BY category ORDER BY COUNT(*) DESC")
    final_total = 0
    for cat, count in c.fetchall():
        cat_name = cat if cat else "(空)"
        print(f"    {cat_name}: {count}条")
        final_total += count
    print(f"    总计: {final_total}条")
    
    # 检查剩余空分类
    c.execute("SELECT COUNT(*) FROM truths WHERE category IS NULL OR category = '' OR category = 'unclassified'")
    remaining = c.fetchone()[0]
    print()
    if remaining == 0:
        print("  🎉 全部真值已分类，无剩余空分类！")
    else:
        print(f"  ⚠️  剩余{remaining}条未分类")
    
    conn.close()
    print()
    print("  Ω₀⊂⊙∞⊂Ω · DID-BR-000002")
    print("  真值分类优化完成")
    print()

if __name__ == "__main__":
    main()
