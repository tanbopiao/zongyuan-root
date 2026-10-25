#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ω-Brainμ 自动修复闭环 V0.1：根因报告 → 修复建议契约 → 调度执行
安全铁律：仅生成审计型契约（只读执行）；写动作永远走人工审批
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import os, json, time, glob

ZR = "/home/user/ZONGYUAN-ROOT"
PROPS = os.path.join(ZR, "var/brain-proposals")
INBOX = os.path.join(ZR, "task_inbox")

FIX_MAP = {
    "认证/令牌": "注入有效密钥至加密槽位（KEK）→ 验证 provider 恢复决策；零明文落盘",
    "网络/端点不可达": "统一无尾斜杠端点 https://www.huodouai.com/api/report/truth；失败双通道兜底；历史记录留存不改",
    "权限/文件": "检查文件权限/路径归属；熔断暂停属设计行为不处理；只读文件保持 444",
    "资源/配额": "配额保护：超限进入只读空转；扩容或降载；记录配额状态",
    "未分类": "人工复核判定口径；补充分类规则后重跑根因分析",
}

def latest_report():
    files = sorted(glob.glob(os.path.join(PROPS, "failure-analysis-*.json")))
    return json.load(open(files[-1])) if files else None

def build_contract(report):
    causes = report.get("root_causes", {})
    fixes = []
    for cause, cnt in causes.items():
        fixes.append({"cause": cause, "count": cnt, "fix_suggest": FIX_MAP.get(cause, "人工评估")})
    task_id = f"T-BRAIN-FIX-{int(time.time())}"
    contract = {
        "contract_version": "CONTRACT-OP-V1.0", "did": "DID-BR-000002",
        "ontology_signature": "Ω₀⊂⊙∞⊂Ω",
        "contract_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task_id": task_id,
        "operator_list": [{"op_id": "OP-BRAIN-AUDIT-001", "params": {"fix_plan": fixes}, "timeout": 120}],
        "scheduling_policy": {"mode": "serial", "continue_on_fail": False},
        "memo": f"Ω-Brainμ 自动修复建议：{report['total_failures']} 失败 → {len(fixes)} 根因修复方案（只读审计，写动作人工审批）",
    }
    p = os.path.join(INBOX, task_id + ".json")
    json.dump(contract, open(p, "w"), ensure_ascii=False, indent=2)
    return contract, p

if __name__ == "__main__":
    rep = latest_report()
    if not rep:
        print("无根因报告，先跑 brain_failure_analysis.py"); exit(1)
    c, p = build_contract(rep)
    print(f"修复建议契约: {p}")
    print(f"根因方案数: {len(c['operator_list'][0]['params']['fix_plan'])}")
    for f in c["operator_list"][0]["params"]["fix_plan"]:
        print(f"  [{f['cause']} x{f['count']}] {f['fix_suggest'][:40]}")
    print("闭环: 根因→修复方案→契约→inbox ✓")
