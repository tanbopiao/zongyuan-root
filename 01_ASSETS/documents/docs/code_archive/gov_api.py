#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智·政务AI中台 — 生产级算子API服务 V1.1（标准库版）
统一入口：4类政务算子 + 全链路审计 + 健康检查
零第三方依赖（仅标准库），适配精简版Python环境
启动：python3 gov_api.py （默认0.0.0.0:8201）
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT
"""
import hashlib
import json
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TRACE = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"
AUDIT_LOG = []


def audit(op, node, payload, ok):
    AUDIT_LOG.append({
        "op": op, "node": node or "unknown", "time": datetime.now().isoformat(),
        "trace": TRACE, "did": DID, "payload": payload, "result_status": "ok" if ok else "error",
    })


def gov_rag(query, docs):
    results = []
    for doc in docs:
        for para in re.split(r"[。\n]", doc.get("text", "")):
            if query in para:
                results.append({"doc": doc.get("title"), "para": para.strip(), "source": doc.get("source")})
    return {"success": True, "query": query, "hits": results[:5], "hit_count": len(results)}


def gov_doc_check(fields):
    issues = []
    for item in ["单位名称", "统一社会信用代码", "联系人", "联系电话", "申请事项"]:
        if not fields.get(item):
            issues.append({"level": "error", "item": item, "msg": f"缺少必填项: {item}"})
    if fields.get("联系电话") and not re.fullmatch(r"1[3-9]\d{9}", fields.get("联系电话", "")):
        issues.append({"level": "error", "item": "联系电话", "msg": "手机号格式不正确"})
    if fields.get("统一社会信用代码") and not re.fullmatch(r"[0-9A-Z]{18}", fields.get("统一社会信用代码", "")):
        issues.append({"level": "error", "item": "统一社会信用代码", "msg": "信用代码格式不正确(18位)"})
    if not issues:
        issues.append({"level": "pass", "item": "整体", "msg": "材料预审通过"})
    return {"success": True, "result": "pass" if all(i["level"] != "error" for i in issues) else "reject", "issues": issues}


def gov_archive(raw_text):
    meta = {}
    for key, pat in [("文号", r"[^号\s]+号"), ("成文日期", r"20\d{2}年\d{1,2}月\d{1,2}日"),
                     ("发文机关", r"^[\u4e00-\u9fa5]{2,20}(?:局|厅|部|委|办|政府)"),
                     ("标题", r"(?:关于|印发|发布).{2,40}?(?:方案|通知|意见|办法|规定|批复|措施)")]:
        m = re.search(pat, raw_text)
        meta[key] = m.group(0) if m else ""
    meta["字数"] = len(raw_text)
    meta["哈希"] = hashlib.sha256(raw_text.encode()).hexdigest()[:16]
    return {"success": True, "meta": meta}


def gov_mask(text):
    masked = re.sub(r"\d{17}[\dXx]", "***************X", text)
    masked = re.sub(r"1[3-9]\d{9}", "138****0000", masked)
    masked = re.sub(r"(\d{4})\d{10}(\d{4})", r"\1**********\2", masked)
    hits = {"身份证": len(re.findall(r"\d{17}[\dXx]", text)),
            "手机号": len(re.findall(r"1[3-9]\d{9}", text)),
            "银行卡": len(re.findall(r"\d{4}\d{10}\d{4}", text))}
    return {"success": True, "masked": masked, "masked_count": sum(hits.values()), "hits": hits}


ROUTES = {
    "/api/gov/v1/rag": gov_rag,
    "/api/gov/v1/doc-check": gov_doc_check,
    "/api/gov/v1/archive": gov_archive,
    "/api/gov/v1/mask": gov_mask,
}


class GovHandler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "healthy", "service": "gov-operator-cluster",
                             "version": "1.1.0", "trace": TRACE, "did": DID})
        elif self.path.startswith("/api/gov/v1/audit"):
            limit = 20
            try:
                limit = int(self.path.split("limit=")[1].split("&")[0])
            except Exception:
                pass
            self._send(200, {"success": True, "audit_count": len(AUDIT_LOG), "records": AUDIT_LOG[-limit:]})
        else:
            self._send(404, {"success": False, "error": "not found"})

    def do_POST(self):
        fn = ROUTES.get(self.path)
        if not fn:
            self._send(404, {"success": False, "error": "unknown endpoint"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length).decode() or "{}")
        except Exception:
            self._send(400, {"success": False, "error": "invalid json"})
            return
        node = self.headers.get("X-Gov-Node")
        try:
            if self.path.endswith("/rag"):
                result = fn(data.get("query", ""), data.get("docs", []))
            elif self.path.endswith("/doc-check"):
                result = fn(data.get("fields", {}))
            elif self.path.endswith("/archive"):
                result = fn(data.get("raw_text", ""))
            else:
                result = fn(data.get("text", ""))
            audit(self.path.split("/")[-1], node, data, result.get("success", False))
            self._send(200, result)
        except Exception as e:
            audit(self.path.split("/")[-1], node, data, False)
            self._send(500, {"success": False, "error": str(e)})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    import os
    port = int(os.environ.get("GOV_PORT", "8201"))
    server = ThreadingHTTPServer(("0.0.0.0", port), GovHandler)
    print(f"火斗云智·政务AI中台算子服务 V1.1 启动于 :{port} | {TRACE} | {DID}")
    server.serve_forever()
