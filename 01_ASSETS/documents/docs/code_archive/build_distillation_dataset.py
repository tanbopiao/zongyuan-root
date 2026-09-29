#!/usr/bin/env python3
import sqlite3, json, os
from collections import Counter

db_path = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 提取高价值真值
categories = ["meta_rule", "protocol", "theorem", "method", "axiom", "risk", "decision", "lock"]
placeholders = ",".join(["?"] * len(categories))
query = "SELECT truth_key, truth_value, category FROM truths WHERE category IN (" + placeholders + ") LIMIT 500"
cursor.execute(query, categories)
high_value_truths = cursor.fetchall()
print("提取真值数量:", len(high_value_truths))

# 构建问答对
qa_pairs = []
for key, value, category in high_value_truths:
    try:
        value_dict = json.loads(value) if value and value.startswith("{") else {"content": str(value)[:300]}
    except:
        value_dict = {"content": str(value)[:300]}
    
    if category == "meta_rule":
        question = "元法则 " + str(key) + " 的内容是什么？"
    elif category == "protocol":
        question = "协议 " + str(key) + " 的规范是什么？"
    elif category == "theorem":
        question = "定理 " + str(key) + " 的内容和应用是什么？"
    elif category == "method":
        question = "方法 " + str(key) + " 的执行步骤是什么？"
    elif category == "risk":
        question = "风险 " + str(key) + " 的识别和缓解措施是什么？"
    elif category == "decision":
        question = "决策 " + str(key) + " 的依据和结论是什么？"
    elif category == "axiom":
        question = "公理 " + str(key) + " 的内容是什么？"
    elif category == "lock":
        question = "锁档 " + str(key) + " 的内容是什么？"
    else:
        question = "请解释 " + str(key)
    
    answer = json.dumps(value_dict, ensure_ascii=False)[:500]
    
    qa_pairs.append({
        "instruction": question,
        "input": "",
        "output": answer,
        "category": category,
        "source": "9120_truth_library",
        "truth_key": str(key)
    })

# 保存蒸馏数据集
output_dir = "/opt/ZONGYUAN-ROOT/data/distillation_dataset"
os.makedirs(output_dir, exist_ok=True)
output_file = output_dir + "/zongyuan_distillation_v1.json"
with open(output_file, "w") as f:
    json.dump(qa_pairs, f, ensure_ascii=False, indent=2)

print("[OK] 蒸馏数据集已构建")
print("问答对数量:", len(qa_pairs))
print("保存路径:", output_file)
print("格式: Alpaca格式")

category_counts = Counter([qa["category"] for qa in qa_pairs])
print("分类统计:")
for cat, count in category_counts.most_common():
    print("  -", cat, ":", count, "条")

conn.close()
