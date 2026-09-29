#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政务AI中台算子仿真验收测试
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../operators")
from operator_registry import run_operator, AUDIT_LOG, REGISTRY

passed = failed = 0
def check(name, cond, detail=""):
    global passed, failed
    if cond: passed += 1; print(f"  ✅ {name}")
    else: failed += 1; print(f"  ❌ {name} {detail}")

print("=" * 50)
print("政务AI中台算子仿真验收 V1.0")
print("=" * 50)

# 1. gov-rag-v1 公文检索
print("\n[1] gov-rag-v1 政务公文RAG检索")
doc_pool = [
    {"title": "深圳市政务数据管理办法", "text": "政务数据应当分级分类管理。敏感数据不得对外提供。数据共享应当遵循最小必要原则。", "source": "深圳市2026年33号文"},
    {"title": "政务服务事项管理办法", "text": "政务服务事项应当实行清单管理。办理时限应当向社会公布。", "source": "广东省2025年12号文"},
]
r = run_operator("gov-rag-v1", "数据共享", doc_pool)
check("命中敏感数据/最小必要条款", r["success"] and r["result"]["hit_count"] >= 1, str(r))

# 2. gov-doc-check-v1 材料预审
print("\n[2] gov-doc-check-v1 政务材料预审")
good = {"单位名称": "深圳市XX科技公司", "统一社会信用代码": "91440300MA5XX1234A", "联系人": "张三", "联系电话": "13812345678", "申请事项": "数据开放申请"}
bad = {"单位名称": "深圳市XX科技公司", "统一社会信用代码": "BAD", "联系人": "", "联系电话": "12345", "申请事项": ""}
r1 = run_operator("gov-doc-check-v1", good)
r2 = run_operator("gov-doc-check-v1", bad)
check("合格材料判定pass", r1["success"] and r1["result"]["result"] == "pass")
check("缺陷材料判定reject且含缺项", r2["success"] and r2["result"]["result"] == "reject" and len(r2["result"]["issues"]) >= 4)

# 3. gov-archive-v1 档案结构化
print("\n[3] gov-archive-v1 档案OCR结构化")
raw = "深圳市发展和改革委员会文件\n深发改〔2026〕15号\n关于印发深圳市数字经济促进若干措施的通知\n2026年3月10日"
r = run_operator("gov-archive-v1", raw)
check("抽取文号/机关/标题/日期", r["success"] and r["result"]["文号"] and r["result"]["标题"], str(r["result"]))

# 4. gov-data-mask-v1 敏感脱敏
print("\n[4] gov-data-mask-v1 敏感数据脱敏")
sample = "申请人身份证440301199001011234，手机13812345678，银行卡6222021234567890123"
r = run_operator("gov-data-mask-v1", sample)
check("脱敏3类敏感信息", r["success"] and r["result"]["masked_count"] >= 3, str(r["result"]))
check("原始号码不在脱敏输出中", "13812345678" not in r["result"]["masked"])

# 5. 审计留痕
print("\n[5] 审计留痕验证")
check("审计日志已记录全部调用", len(AUDIT_LOG) == 5, f"实际{len(AUDIT_LOG)}")

print("=" * 50)
print(f"验收结果: {passed} 通过 / {failed} 失败")
print(f"注册算子: {len(REGISTRY)} 个")
sys.exit(1 if failed else 0)
