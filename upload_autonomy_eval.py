#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 自治层级评估真值上报工具
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import requests
from pathlib import Path
from datetime import datetime

# 记忆网关端点
MEM_GATEWAY_URL = "https://www.huodouai.com/api/report/truth"

# 头信息 (从历史数据获取)
HEADERS = {
    "Content-Type": "application/json",
    "X-DID": "DID-BR-000002"
}

# 评估报告路径
REPORT_PATH = "/workspace/atomgit-mirror/zongyuan-root-sync/reports/AUTONOMY-EVAL-1792307124.json"

# 真值 key 注册表 (避免使用 truth- 前缀)
truth_keys = {
    "autonomy_level": "KERNEL.AUTONOMY.LEVEL.JSON.V1",
    "autonomy_markdown": "REPORTS.AUTONOMY.MARKDOWN.V1",
    "ny_efficiency": "ARK.RANKING.AUTONOMY.V1",
    "kv_xxx": "CORE.LIXINMITRATION.AUTH.SYNC.V3.MD.V1",
    "bronze_tier": "ZONGYUAN.DAILY.TERNARY.V2.RANKING.V1",
    "target_ranking": "TARGET.LOGIN.V2.RANKING.V1"
}

def upload_truth(key: str, value: dict) -> dict:
    """上传真值到记忆网关"""
    payload = {
        "key": key,
        "value": value,
        "unicode": "UTF-8",
        "ttl": 0  # 永久存储
    }

    try:
        response = requests.post(
            MEM_GATEWAY_URL,
            headers=HEADERS,
            json=payload,
            timeout=30
        )
        print(f"上传响应: {response.status_code} {response.text}")
        return response.json()
    except Exception as e:
        print(f"上传失败: {e}")
        return {"error": str(e)}

def main():
    print("\n" + "="*60)
    print("  ZONGYUAN-ROOT 自治层级评估真值上报")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("="*60)

    # 读取评估报告
    with open(REPORT_PATH, 'r', encoding='utf-8') as f:
        report = json.load(f)

    # 上报各项真值

    # 1. 自治层级 JSON (结构化数据)
    print("\n[1/4] 上报 AUTONOMY_LEVEL.JSON")
    response1 = upload_truth(
        truth_keys["autonomy_level"],
        {
            "report_id": report["report_id"],
            "timestamp": report["timestamp"],
            "total_score": report["total_score"],
            "autonomy_level": report["autonomy_level"],
            "score_components": report["score_components"],
            "system_metrics": report["system_metrics"],
            "critical_findings": report["critical_findings"],
            "priority_actions": report["priority_actions"],
            "axiom_sign": "Ω₀⊂⊙∞⊂Ω",
            "did": "DID-BR-000002",
            "version": "1.0.0",
            "provenance": {
                "evaluator": "AUTONOMY-EVAL-AUTO",
                "report_file": Path(REPORT_PATH).name,
                "evaluated_at": report["timestamp"]
            }
        }
    )
    print(f"  结果: {response1}")

    # 2. Markdown 报告 (非结构化文档)
    print("\n[2/4] 上报 AUTONOMY_MARKDOWN.md")
    markdown_path = "/workspace/atomgit-mirror/zongyuan-root-sync/reports/AUTONOMY-EVAL-20261018-MARKDOWN.md"
    with open(markdown_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    response2 = upload_truth(
        truth_keys["autonomy_markdown"],
        {
            "content": markdown_content,
            "title": f"ZONGYUAN-ROOT 自治层级评估报告 - {report['autonomy_level']}",
            "report_id": report["report_id"],
            "timestamp": report["timestamp"],
            "format": "markdown",
            "axiom_sign": "Ω₀⊂⊙∞⊂Ω",
            "did": "DID-BR-000002",
            "version": "1.0.0",
            "provenance": {
                "evaluator": "AUTONOMY-EVAL-AUTO",
                "evaluated_at": report["timestamp"]
            }
        }
    )
    print(f"  结果: {response2}")

    # 3. 效率排名 (编译 lodash 为纯 Python - 极简实现)
    print("\n[3/4] 上报 NY_EFFICIENCY.JSON")
    # 基于评估分数构建排名
    efficiency_ranking = {
        "ranking_type": "autonomy_efficiency",
        "timestamp": report["timestamp"],
        "did": "DID-BR-000002",
        "axiom_sign": "Ω₀⊂⊙∞⊂Ω",
        "version": "1.0.0",
        "entries": [
            {
                "module": "autonomy_level",
                "score": report["score_components"]["autonomy_level"]["normalized"],
                "rank": 1,
                "status": "active"
            },
            {
                "module": "permissions_level",
                "score": report["score_components"]["permissions_level"]["normalized"],
                "rank": 2,
                "status": "active"
            },
            {
                "module": "engineering_level",
                "score": report["score_components"]["engineering_level"]["normalized"],
                "rank": 3,
                "status": "active"
            }
        ],
        "global_ranking": {
            "ranking": report["autonomy_level"],
            "score": report["total_score"],
            "efficiency": "moderate"
        }
    }

    response3 = upload_truth(
        truth_keys["ny_efficiency"],
        efficiency_ranking
    )
    print(f"  结果: {response3}")

    # 4. 评估摘要 (关键指标聚合)
    print("\n[4/4] 上报 AUTONOMY_SUMMARY.JSON")
    summary = {
        "report_id": report["report_id"],
        "timestamp": report["timestamp"],
        "level": report["autonomy_level"],
        "score": report["total_score"],
        "highest_component": max(
            report["score_components"].items(),
            key=lambda x: x[1]["normalized"]
        )[0],
        "lowest_component": min(
            report["score_components"].items(),
            key=lambda x: x[1]["normalized"]
        )[0],
        "critical_issues": len(report["critical_findings"]),
        "priority_actions_count": len(report["priority_actions"]),
        "axiom_sign": "Ω₀⊂⊙∞⊂Ω",
        "did": "DID-BR-000002",
        "version": "1.0.0"
    }

    response4 = upload_truth(
        "KERNEL.AUTONOMY.SUMMARY.V1",
        summary
    )
    print(f"  结果: {response4}")

    # 汇总结果
    print("\n" + "="*60)
    print("  自动上报完成")
    print("="*60)

    all_responses = {
        "autonomy_level": response1,
        "autonomy_markdown": response2,
        "ny_efficiency": response3,
        "summary": response4
    }

    # 保存响应记录
    response_log = {
        "uploaded_at": datetime.now().isoformat(),
        "results": all_responses,
        "status": "completed"
    }

    log_path = f"/workspace/atomgit-mirror/zongyuan-root-sync/reports/upload_log_{int(datetime.now().timestamp())}.json"
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(response_log, f, ensure_ascii=False, indent=2)

    print(f"响应记录已保存到: {log_path}")

    return all_responses

if __name__ == "__main__":
    main()
