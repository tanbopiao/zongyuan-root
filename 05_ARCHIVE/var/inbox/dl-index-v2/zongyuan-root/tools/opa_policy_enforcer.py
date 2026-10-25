#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OPA 策略护栏执行器 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
语义对齐 policy/zongyuan_root_policy.rego（rego 为策略单一来源，非硬编码）：
  allow：契约信封（CONTRACT-OP-V1.0 + DID + Ω 签名）+ op_id 全部在 rego 白名单
  layer_lock：逻辑态直连（kind=logic_layer_direct）→ 越层拦截，触发轻锁档
fail-closed：rego 缺失/解析失败 → 拒绝放行
"""
import re, json, os

POLICY_PATH = "/home/user/ZONGYUAN-ROOT/policy/zongyuan_root_policy.rego"
REQ_ENV = ("CONTRACT-OP-V1.0", "DID-BR-000002", "Ω₀⊂⊙∞⊂Ω")

def load_policy(path=POLICY_PATH):
    if not os.path.exists(path):
        return None, "policy file missing"
    try:
        return open(path, encoding="utf-8").read(), None
    except Exception as e:
        return None, str(e)

def extract_op_whitelist(text):
    """从 rego 提取 op_whitelisted 子句中的 op_id 字面量"""
    pat = re.compile(r'ops\[_\]\.op_id\s*==\s*"([^"]+)"')
    return set(pat.findall(text))

def enforce(contract, policy_text=None):
    text = policy_text
    if text is None:
        text, err = load_policy()
        if err or text is None:
            return {"allow": False, "layer_lock": False, "reasons": [f"opa:{err}"]}
    whitelist = extract_op_whitelist(text)
    if not whitelist:
        return {"allow": False, "layer_lock": False, "reasons": ["opa:rego op_whitelist empty"]}
    reasons = []
    # 越层拦截：逻辑态直连
    if contract.get("kind") == "logic_layer_direct":
        return {"allow": False, "layer_lock": True,
                "reasons": ["layer_lock:逻辑态绕过契约直接操作执行层，触发轻锁档"]}
    # 信封校验
    if contract.get("contract_version") != REQ_ENV[0]:
        reasons.append("contract_version mismatch")
    if contract.get("did") != REQ_ENV[1]:
        reasons.append("did mismatch")
    if contract.get("ontology_signature") != REQ_ENV[2]:
        reasons.append("ontology_signature mismatch")
    # op_id 白名单（全部在 rego 白名单）
    ops = contract.get("operator_list", [])
    bad = [o.get("op_id") for o in ops if o.get("op_id") not in whitelist]
    if bad:
        reasons.append(f"op_id not in rego whitelist: {bad}")
    return {"allow": not reasons, "layer_lock": False, "reasons": reasons,
            "whitelist": sorted(whitelist)}

if __name__ == "__main__":
    import sys
    c = json.load(open(sys.argv[1], encoding="utf-8"))
    print(json.dumps(enforce(c), ensure_ascii=False, indent=2))
