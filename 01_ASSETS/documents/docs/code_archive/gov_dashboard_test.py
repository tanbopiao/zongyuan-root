#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""政务AI中台大屏数据服务本地仿真：四服务全链路，验证8203聚合输出"""
import json, os, sys, threading, urllib.request
from http.server import ThreadingHTTPServer

BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "operators"))
sys.path.insert(0, BASE)
import gov_api, gov_audit, gov_gateway, gov_dashboard

AUDIT_DIR = os.path.join(BASE, "audit_sim2")
gov_audit.AUDIT_DIR = AUDIT_DIR
gov_audit.AUDIT_FILE = os.path.join(AUDIT_DIR, "gov_audit.jsonl")
import shutil; shutil.rmtree(AUDIT_DIR, ignore_errors=True)

def start(cls, port):
    s = ThreadingHTTPServer(("127.0.0.1", port), cls)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s

def req(url, method="GET", body=None, headers=None):
    h = {"Content-Type":"application/json"}
    if headers: h.update(headers)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

start(gov_audit.AuditHandler, 8202)
start(gov_api.GovHandler, 8201)
start(gov_gateway.GatewayHandler, 8200)
start(gov_dashboard.DashboardHandler, 8203)

KEY = gov_gateway.API_KEY
# 产生一些调用
req("http://127.0.0.1:8200/api/gov/v1/mask","POST",{"text":"手机13812345678"},{"X-API-Key":KEY,"X-Gov-Node":"SIM"})
req("http://127.0.0.1:8200/api/gov/v1/archive","POST",{"raw_text":"深发改〔2026〕15号"},{"X-API-Key":KEY})
req("http://127.0.0.1:8200/api/gov/v1/mask","POST",{"text":"身份证440301199001011234"},{"X-API-Key":KEY})

code, d = req("http://127.0.0.1:8203/api/dashboard/summary")
print("大屏数据服务 HTTP:", code)
print("KPI:", json.dumps(d.get("kpi"), ensure_ascii=False))
print("算子分布:", json.dumps(d.get("operator_distribution"), ensure_ascii=False))
print("服务数:", len(d.get("services",[])), "| 审计流条数:", len(d.get("recent_calls",[])))
ok = (code==200 and d["kpi"]["total_audit"]>=3 and "mask" in d["operator_distribution"]
      and any(s["port"]==8203 and s["status"]=="healthy" for s in d["services"]))
print("SIM-PASS" if ok else "SIM-FAIL")
