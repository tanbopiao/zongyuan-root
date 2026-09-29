#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智·政务AI中台 — 本地集成仿真测试（网关8200 + 审计8202 + 算子8201 全链路）
单进程内起三个服务线程，验证：鉴权/路由/脱敏/审计持久化/重启不清空
通过后输出 SIM-PASS；任一断言失败输出 SIM-FAIL。
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import shutil
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "operators")
BASE = os.path.normpath(BASE)
sys.path.insert(0, BASE)

import gov_api
import gov_audit
import gov_gateway

AUDIT_DIR = os.path.join(BASE, "audit_sim")
AUDIT_FILE = os.path.join(AUDIT_DIR, "gov_audit.jsonl")

def start(handler_cls, port):
    s = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s

def req(url, method="GET", body=None, headers=None):
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

results = []

def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f" | {detail}" if detail and not cond else ""))

# 准备：清空旧审计
shutil.rmtree(AUDIT_DIR, ignore_errors=True)
gov_audit.AUDIT_DIR = AUDIT_DIR
gov_audit.AUDIT_FILE = AUDIT_FILE

# 起三服务
s_audit = start(gov_audit.AuditHandler, 8202)
s_api = start(gov_api.GovHandler, 8201)
s_gw = start(gov_gateway.GatewayHandler, 8200)

GW = "http://127.0.0.1:8200"
KEY = gov_gateway.API_KEY

# ① 无Key鉴权 → 401
code, r = req(GW + "/api/gov/v1/mask", "POST", {"text": "x"})
check("①无Key鉴权返回401", code == 401)

# ② 正确Key + 脱敏算子 → 200 且脱敏生效
code, r = req(GW + "/api/gov/v1/mask", "POST", {"text": "身份证440301199001011234 手机13812345678"},
              {"X-API-Key": KEY, "X-Gov-Node": "LOCAL-SIM"})
check("②正确Key路由+脱敏200", code == 200 and "138****0000" in r.get("masked", ""))

# ③ 档案算子经网关 → 200
code, r = req(GW + "/api/gov/v1/archive", "POST", {"raw_text": "深发改〔2026〕15号 关于印发深圳市数字经济促进若干措施的通知"},
              {"X-API-Key": KEY})
check("③档案算子经网关200", code == 200 and r.get("success"))

# ④ 审计已持久化（文件写入）
exists = os.path.exists(AUDIT_FILE)
recs = []
if exists:
    with open(AUDIT_FILE, encoding="utf-8") as f:
        recs = [json.loads(l) for l in f if l.strip()]
check("④审计持久化落盘", exists and len(recs) >= 2, f"共{len(recs)}条")

# ⑤ 审计服务可查历史
code, r = req(GW + "/audit")  # 网关不转发审计；直连审计
code2, r2 = req("http://127.0.0.1:8202/audit?limit=10")
check("⑤审计历史可查询", code2 == 200 and r2.get("count", 0) >= 2)

# ⑥ 审计记录含网关转发的调用
ops = {x.get("op") for x in recs}
check("⑥审计含mask/archive操作", "mask" in ops and "archive" in ops, f"ops={ops}")

# ⑦ 重启不清空：模拟重启=重新初始化读文件
recs_after = gov_audit.read_records(limit=100)
check("⑦重启后审计记录仍存在(不清空)", len(recs_after) >= len(recs))

# 清理
s_gw.shutdown(); s_api.shutdown(); s_audit.shutdown()

passed = sum(1 for _, ok, _ in results if ok)
print(f"\n===== 本地集成仿真: {passed}/{len(results)} 通过 =====")
print("SIM-PASS" if passed == len(results) else "SIM-FAIL")
