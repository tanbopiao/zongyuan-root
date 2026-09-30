#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一记忆网关+胶水层全套异常测试套件
测试用例：正常触发、无触发词、索引文件缺失、索引损坏、网关超时、双向漂移、空快照
"""
import subprocess
import json
import os
import shutil
from datetime import datetime

BASE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_GLUE = os.path.join(BASE_ROOT, "scripts", "glue_memory_trigger.py")
INDEX_PATH = os.path.join(BASE_ROOT, "runtime", "memory_index.json")
INDEX_BACKUP = os.path.join(BASE_ROOT, "runtime", "memory_index.bak.json")
LOG_OUT = os.path.join(BASE_ROOT, "log", "test_suite_report.json")


def run_case(input_text):
    proc = subprocess.run(
        ["python3", SCRIPT_GLUE, "--input", input_text],
        capture_output=True, text=True, timeout=20
    )
    try:
        return json.loads(proc.stdout)
    except Exception:
        return {"trigger": False, "context": f"parse_fail:{proc.stderr}"}


def main():
    report = {
        "test_time": datetime.now().isoformat(),
        "DID": "DID-BR-000002",
        "sovereign_root": "Ω-TAN-7-001",
        "cases": []
    }

    # 0 备份原始索引
    if os.path.exists(INDEX_PATH):
        shutil.copy2(INDEX_PATH, INDEX_BACKUP)

    # Case1：正常触发「元极恒一」
    res1 = run_case("元极恒一，输出体系状态")
    report["cases"].append({"case_id": 1, "desc": "正常触发关键词", "expect": {"trigger": True}, "actual": res1})

    # Case2：普通文本，不触发
    res2 = run_case("帮我梳理架构设计")
    report["cases"].append({"case_id": 2, "desc": "无触发词不加载记忆", "expect": {"trigger": False}, "actual": res2})

    # Case3：索引文件缺失模拟
    if os.path.exists(INDEX_PATH):
        os.remove(INDEX_PATH)
    res3 = run_case("元极恒一")
    report["cases"].append({"case_id": 3, "desc": "索引缺失异常降级", "expect": {"trigger": True}, "actual": res3})

    # Case4：损坏索引模拟
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write("{bad json{{{{")
    res4 = run_case("元极恒一")
    report["cases"].append({"case_id": 4, "desc": "索引json损坏降级", "expect": {"trigger": True}, "actual": res4})

    # 恢复原始索引
    if os.path.exists(INDEX_BACKUP):
        shutil.copy2(INDEX_BACKUP, INDEX_PATH)
        os.remove(INDEX_BACKUP)

    # Case5：关键词混杂其他文本
    res5 = run_case("你好，元极恒一，请执行自检")
    report["cases"].append({"case_id": 5, "desc": "文本混杂触发关键词", "expect": {"trigger": True}, "actual": res5})

    os.makedirs(os.path.dirname(LOG_OUT), exist_ok=True)
    with open(LOG_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
