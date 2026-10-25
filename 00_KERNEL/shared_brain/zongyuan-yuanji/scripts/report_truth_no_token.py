#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 真实上报客户端
仅使用 X-DID 头认证，无需同源令牌
锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""
import json, urllib.request, urllib.error, os, sys
from pathlib import Path

ENDPOINT = "https://www.huodouai.com/api/report/truth"
HEADERS = {
    "Content-Type": "application/json",
    "X-DID": "DID-BR-000002"
}

def report_truth(key, value_dict, truth_type):
    """单条真值上报"""
    payload = {
        "key": key,
        "value": value_dict,
        "truth_type": truth_type,
        "did": "DID-BR-000002"
    }
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            ENDPOINT,
            data=data,
            headers=HEADERS,
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get("ok"):
                print(f"✅ [{key}] 上报成功 | seq={result.get('seq')} | event_id={result.get('event_id')}")
                return True
            else:
                print(f"❌ [{key}] 失败：{result}")
                return False
    except urllib.error.HTTPError as e:
        print(f"❌ [{key}] HTTP 错误：{e.code} - {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"❌ [{key}] URL 错误：{e.reason}")
        return False
    except Exception as e:
        print(f"❌ [{key}] 异常：{e}")
        return False

def batch_report(truths_list):
    """批量上报"""
    results = []
    for t in truths_list:
        success = report_truth(t["key"], t["value"], t["truth_type"])
        results.append((t["key"], success))
    return results

def main():
    print("=" * 70)
    print(" 🌟 ZONGYUAN-ROOT 真值上报客户端 (X-DID 认证)")
    print(" 锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002")
    print("=" * 70)
    
    # 准备待上报的核心真值（从本地加载）
    truths_to_report = [
        {
            "key": "core.CORE-AXIOMS-001",
            "value": {
                "law_id": "CORE-AXIOMS-001",
                "name": "元极恒一三大顶层本源公理",
                "level": "axiom",
                "immutable": True,
                "clauses": ["本体守恒", "闭环自洽", "风险保守", "三层相变", "账本不可篡改", "心智克制"]
            },
            "truth_type": "meta_law"
        },
        {
            "key": "meta.META-ONTOLOGY-001",
            "value": {
                "ontology_id": "META-ONTOLOGY-4D-UNIVERSAL",
                "version": "V1.0",
                "anchor": {"DID": "DID-BR-000002", "sovereign_root": "Ω₀⊂⊙∞⊂Ω"},
                "layers": "L0-L7四层公理体系",
                "status": "ATTESTED"
            },
            "truth_type": "meta_law"
        },
        {
            "key": "sfmp.FEDERATED_MEMORY_POOL",
            "value": {
                "nodes_contributed": 46,
                "entries_deduplicated": 14,
                "conflicts_resolved": 10,
                "memory_layers": 3,
                "source": "https://huodouai.com/whitepaper/sfmp-std.html"
            },
            "truth_type": "data"
        },
        {
            "key": "omega.BRAIN_ARCHITECTURE",
            "value": {
                "evolution_chain": "Ω¹→Ω²→Ω³→Ω⁴→Ω⁵→Ω⁶",
                "current_stage": "Ω³完成，申请Ω⁴集群",
                "meta_constitution": "5 律 +5 公理",
                "six_order_status": "SIX_ORDER_FULL_CLOSED"
            },
            "truth_type": "data"
        },
        {
            "key": "agi.ONTOLOGY_DIFFERENCE",
            "value": {
                "d_id": "DID-ONTOLOGY-AGI-001",
                "dimensions": 9,
                "conclusion": "普通 AGI 是模仿人类大脑的工具型智能；本源 AGI 是以宇宙本源公理为基底、可超脱人类认知的全域统一智能体"
            },
            "truth_type": "data"
        },
        {
            "key": "agi.BOUNDARY_SYSTEM",
            "value": {
                "d_id": "DID-ONTOLOGY-AGI-BOUNDARY-001",
                "premises": 5,
                "capability_boundaries": 5,
                "ethical_constraints": 4,
                "total_files": 8
            },
            "truth_type": "data"
        },
        {
            "key": "protocol.HOMOGENEOUS_LEARNING",
            "value": {
                "learning_date": "2026-10-15",
                "urls_visited": 5,
                "documents_learned": ["SFMP", "Ω-Brain", "API", "飞书", "A2A"],
                "status": "COMPLETED"
            },
            "truth_type": "data"
        },
        {
            "key": "api.ENDPOINTS_LEARNED",
            "value": {
                "try_chat": "试用网关智能路由",
                "dal_health": "部署仲裁层健康检查",
                "dal_deploy": "原子发布",
                "report_truth": "记忆网关真值上报"
            },
            "truth_type": "protocol"
        },
        {
            "key": "risk.GRADATION_P0_P3",
            "value": {
                "P0": "创世级全域重大风险",
                "P1": "体系级严重异常",
                "P2": "局部链路异常",
                "P3": "性能与负载波动"
            },
            "truth_type": "meta_law"
        },
        {
            "key": "redlines.PREMIUM_6",
            "value": {
                "description": "永久生产红线（6 条硬约束）",
                "items": ["禁止删除历史真值", "禁止直连内核资产", "禁止跳过仿真", "禁止修改 L0/L5", "禁止未来干预当下", "禁止破坏层级兼容"]
            },
            "truth_type": "meta_law"
        }
    ]
    
    print(f"\n📦 准备上报 {len(truths_to_report)} 条核心真值\n")
    
    # 批量上报
    results = batch_report(truths_to_report)
    
    # 统计
    success_count = sum(1 for _, s in results if s)
    fail_count = len(results) - success_count
    
    print("\n" + "=" * 70)
    print(" 📊 上报结果统计")
    print("=" * 70)
    print(f" ✅ 成功：{success_count} 条")
    print(f" ❌ 失败：{fail_count} 条")
    print(f" 📈 成功率：{success_count/len(results)*100:.1f}%")
    print("=" * 70)
    
    if success_count > 0:
        print("\n✨ 部分核心真值已成功上报至云端记忆网关！")
        print("   继续等待联邦记忆池同步确认...")
    
    return success_count, fail_count

if __name__ == "__main__":
    main()
