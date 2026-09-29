#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智AIOS · 商业化API服务网关 (Local Simulation)
====================================================
版本: V1.0 (本地仿真态, 未部署)
协议: ZONGYUAN-ROOT | DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω

功能:
  1. /api/v1/decision       三维稳态决策引擎 (利益40%/风险35%/成本25%)
  2. /api/v1/memory/truth   记忆网关真值查询 (代理云端9120)
  3. /api/v1/memory/upsert  记忆网关真值写入 (代理云端9120)
  4. /api/v1/health         服务健康状态
  5. /api/v1/products       商业化产品矩阵查询

本地仿真: python3 api_gateway.py --port 9099
验证:     curl http://127.0.0.1:9099/api/v1/health
"""
import argparse
import json
import time
import urllib.request
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============ 配置 ============
CLOUD_MEMORY_GATEWAY = "http://127.0.0.1:9120"   # 云端唯一握手点
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

# 三维稳态决策权重 (元法则固化)
WEIGHT_BENEFIT = 0.40
WEIGHT_RISK = 0.35
WEIGHT_COST = 0.25

# 商业化产品矩阵 (同步自 strategy.product.matrix)
PRODUCT_MATRIX = {
    "matrix_name": "火斗云智AIOS数字资产产品矩阵",
    "version": "V1.1",
    "tagline": "架构真值+流程真值+方法论真值+机制真值+能力真值+规则真值 = 可商业化数字资产产品",
    "tiers": [
        {"name": "免费版", "price": "免费", "target": "个人开发者/小团队", "nodes": "≤3",
         "assets": ["基础记忆网关", "基础熔断自愈", "标准7步SOP", "决策计算器"]},
        {"name": "专业版", "price": "¥999/月", "target": "中小企业/成长型团队", "nodes": "≤50",
         "assets": ["完整记忆网关", "熔断自愈双机制", "审批自动化", "元进化引擎", "根因分析"]},
        {"name": "企业版", "price": "¥50,000/年起", "target": "中大型企业", "nodes": "无限",
         "assets": ["无限节点", "全部机制+能力真值", "API无限", "私有化部署", "专属支持"]},
        {"name": "旗舰版", "price": "¥200,000+/年", "target": "大型企业/政府/战略伙伴", "nodes": "无限",
         "assets": ["企业版全部", "全维度定制", "驻场支持", "联合开发", "知识产权共享"]}
    ],
    "standalone": [
        {"name": "飞书审批自动化", "price": "¥299/月起", "category": "A2流程+A5能力"},
        {"name": "记忆网关对账中心", "price": "¥499/月起", "category": "A5能力"},
        {"name": "熔断自愈监控", "price": "¥399/月起", "category": "A4机制"},
        {"name": "三维稳态决策引擎", "price": "¥199/月起", "category": "A3方法论+A5能力"},
        {"name": "元进化规则引擎", "price": "¥599/月起", "category": "A5能力+A6规则"}
    ]
}


def sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def call_cloud_memory(path: str, method: str = "GET", payload: dict = None, timeout: int = 8):
    """代理调用云端记忆网关 (唯一握手点9120)"""
    url = f"{CLOUD_MEMORY_GATEWAY}{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode()), resp.status
    except Exception as e:
        return {"error": str(e)}, 502


def decision_engine(params: dict) -> dict:
    """三维稳态决策: 利益40% / 风险35% / 成本25%
    params: {options: [{name, benefit(0-100), risk(0-100, 越低越好), cost(0-100, 越低越好)}]}
    """
    options = params.get("options", [])
    if not options:
        return {"error": "options required"}
    results = []
    for opt in options:
        b = float(opt.get("benefit", 0))
        r = float(opt.get("risk", 100))
        c = float(opt.get("cost", 100))
        # 风险/成本为负向指标, 转为正向分
        score = WEIGHT_BENEFIT * b + WEIGHT_RISK * (100 - r) + WEIGHT_COST * (100 - c)
        results.append({
            "name": opt.get("name", ""),
            "benefit": b, "risk": r, "cost": c,
            "score": round(score, 2),
            "weight": {"benefit": WEIGHT_BENEFIT, "risk": WEIGHT_RISK, "cost": WEIGHT_COST}
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return {
        "decision": results,
        "recommended": results[0]["name"] if results else None,
        "formula": "score = 0.40*benefit + 0.35*(100-risk) + 0.25*(100-cost)",
        "DID": DID, "trace": TRACE
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-DID", DID)
        # HTTP头仅支持latin-1, 溯源符号以Unicode转义形式发送
        trace_ascii = TRACE.encode("unicode_escape").decode("ascii")
        self.send_header("X-Trace", trace_ascii)
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode())

    def do_GET(self):
        if self.path.startswith("/api/v1/health"):
            self._send(200, {"status": "healthy", "service": "huodouai-commercial-gateway",
                             "version": "V1.0-sim", "DID": DID, "trace": TRACE})
        elif self.path.startswith("/api/v1/memory/truth"):
            key = self.path.split("/api/v1/memory/truth/")[-1] if "/api/v1/memory/truth/" in self.path else ""
            if not key:
                self._send(400, {"error": "truth key required"})
                return
            data, status = call_cloud_memory(f"/api/truth/{key}")
            self._send(200 if status == 200 else 502, {"status": "ok" if status == 200 else "error",
                                                       "key": key, "data": data})
        elif self.path.startswith("/api/v1/products"):
            self._send(200, {"status": "ok", "matrix": PRODUCT_MATRIX, "DID": DID, "trace": TRACE})
        else:
            self._send(404, {"error": "not found", "endpoints": ["/api/v1/health", "/api/v1/decision",
                                                                 "/api/v1/memory/truth/{key}",
                                                                 "/api/v1/memory/upsert", "/api/v1/products"]})

    def do_POST(self):
        try:
            body = self._read_body()
        except Exception:
            self._send(400, {"error": "invalid json"})
            return
        if self.path.startswith("/api/v1/decision"):
            result = decision_engine(body)
            self._send(200 if "error" not in result else 400, result)
        elif self.path.startswith("/api/v1/memory/upsert"):
            key = body.get("key", "")
            value = body.get("truth_value", body.get("value", {}))
            if not key:
                self._send(400, {"error": "key required"})
                return
            data, status = call_cloud_memory("/api/truth/upsert", "POST",
                                             {"key": key, "truth_value": value})
            self._send(200 if status == 200 else 502, {"status": "ok" if status == 200 else "error",
                                                       "key": key, "data": data})
        else:
            self._send(404, {"error": "not found"})


def main():
    parser = argparse.ArgumentParser(description="火斗云智AIOS商业化API网关(本地仿真)")
    parser.add_argument("--port", type=int, default=9099)
    args = parser.parse_args()
    print(f"火斗云智AIOS商业化API网关 本地仿真启动 http://127.0.0.1:{args.port}")
    print(f"DID: {DID} | 溯源: {TRACE} | 云端握手: {CLOUD_MEMORY_GATEWAY}")
    HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
