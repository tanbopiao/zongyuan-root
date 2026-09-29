#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Key 密钥管理面板 · 独立管理服务
=========================================
火斗云智AIOS / ZONGYUAN-ROOT 元极恒一自治体系
DID: DID-BR-000002 | 本源根: Ω-TAN-7-001 | 溯源: Ω₀⊂⊙∞⊂Ω

独立于 api_key_auth_server.py(认证服务,8120)，在 8121 提供密钥管理能力。
零侵入认证服务：通过 KeyManager 增强类读写同一 keys_store.json，
新增管理方法(list/revoke/enable/disable/set_quota/delete)，不改认证服务本体。

端点（仅本机监听，零公网暴露）：
  GET  /keys             密钥列表(脱敏)
  GET  /keys/<id>        单个密钥详情
  POST /keys             创建密钥 {owner, quota, expires_in, group} → 返回一次原始值
  POST /keys/<id>/revoke       吊销(disable)
  POST /keys/<id>/enable       启用
  POST /keys/<id>/quota        设配额 {quota}
  GET  /audit            审计日志
  GET  /health           健康检查

安全约束：管理面板自身仅本机监听；无鉴权时禁止外网访问(nginx不代理)。
"""

import os
import sys
import json
import time
import hashlib
import secrets
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

DID_ANCHOR = "DID-BR-000002"
ROOT_OMEGA_ANCHOR = "Ω-TAN-7-001"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"


class KeyManager:
    """密钥管理增强：读写同一 keys_store.json，不依赖认证服务进程"""
    def __init__(self, store_path: str):
        self.path = store_path
        self._ensure()

    def _ensure(self):
        if not os.path.exists(self.path):
            self._write({"version": 1, "keys": {}, "audit": []})

    def _read(self):
        self._ensure()
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _audit(self, data, action, owner):
        data.setdefault("audit", []).append({
            "ts": time.time(), "action": action, "owner": owner
        })
        if len(data["audit"]) > 500:
            data["audit"] = data["audit"][-200:]

    def list_keys(self, mask=True):
        """密钥列表，mask=True 时隐藏配额/原始值外的敏感信息"""
        data = self._read()
        out = []
        for kid, rec in data.get("keys", {}).items():
            item = {
                "key_id": kid,
                "owner": rec.get("owner"),
                "enabled": rec.get("enabled", True),
                "quota": rec.get("quota"),
                "calls": rec.get("calls", 0),
                "group": rec.get("group", "default"),
                "created": rec.get("created"),
                "expires_at": rec.get("expires_at"),
                "last_call": rec.get("last_call"),
            }
            out.append(item)
        return out

    def get_key(self, kid):
        data = self._read()
        rec = data.get("keys", {}).get(kid)
        if not rec:
            return None
        return {**rec, "key_id": kid}

    def create(self, owner, quota=None, expires_in=None, group=None):
        """创建密钥，返回 (key_id, raw) 原始值仅此一次"""
        raw = secrets.token_hex(24)
        key_id = "zk_" + hashlib.sha256(raw.encode()).hexdigest()[:16]
        data = self._read()
        data["keys"][key_id] = {
            "owner": owner, "enabled": True,
            "quota": quota, "calls": 0,
            "group": group or "default",
            "created": time.time(),
            "expires_at": (time.time() + expires_in) if expires_in else None,
        }
        self._audit(data, "create", owner)
        self._write(data)
        return key_id, raw

    def revoke(self, kid, reason="admin"):
        """吊销密钥(disable)，保持记录可追溯"""
        data = self._read()
        if kid not in data.get("keys", {}):
            return False, "not_found"
        data["keys"][kid]["enabled"] = False
        self._audit(data, "revoke", data["keys"][kid].get("owner"))
        self._write(data)
        return True, "revoked"

    def enable(self, kid):
        data = self._read()
        if kid not in data.get("keys", {}):
            return False, "not_found"
        data["keys"][kid]["enabled"] = True
        self._audit(data, "enable", data["keys"][kid].get("owner"))
        self._write(data)
        return True, "enabled"

    def set_quota(self, kid, quota):
        data = self._read()
        if kid not in data.get("keys", {}):
            return False, "not_found"
        data["keys"][kid]["quota"] = quota
        self._audit(data, "set_quota", data["keys"][kid].get("owner"))
        self._write(data)
        return True, "quota_set"

    def get_audit(self, limit=50):
        data = self._read()
        return data.get("audit", [])[-limit:]


class ManagerHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _path_parts(self):
        return [p for p in self.path.split("?")[0].split("/") if p]

    def do_GET(self):
        parts = self._path_parts()
        try:
            if not parts or parts[0] == "health":
                self._json(200, {"status": "healthy", "service": "key-manager",
                                 "did": DID_ANCHOR, "trace": TRACE_MARK,
                                 "time": datetime.now().isoformat()})
            elif parts[0] == "keys" and len(parts) == 1:
                self._json(200, {"status": "ok", "keys": ManagerHandler.manager.list_keys(),
                                 "count": len(ManagerHandler.manager.list_keys()), "trace": TRACE_MARK})
            elif parts[0] == "keys" and len(parts) == 2:
                rec = ManagerHandler.manager.get_key(parts[1])
                if rec:
                    self._json(200, {"status": "ok", "key": rec, "trace": TRACE_MARK})
                else:
                    self._json(404, {"status": "not_found"})
            elif parts[0] == "audit":
                self._json(200, {"status": "ok", "audit": ManagerHandler.manager.get_audit(),
                                 "trace": TRACE_MARK})
            else:
                self._json(404, {"status": "not_found"})
        except Exception as e:
            self._json(500, {"status": "error", "reason": str(e)})

    def do_POST(self):
        parts = self._path_parts()
        length = int(self.headers.get("Content-Length", 0))
        data = {}
        if length:
            try:
                data = json.loads(self.rfile.read(length)) if length else {}
            except Exception:
                data = {}
        try:
            # 创建
            if parts and parts[0] == "keys" and len(parts) == 1:
                owner = data.get("owner")
                if not owner:
                    self._json(400, {"status": "error", "reason": "缺owner"})
                    return
                # 同源校验
                if data.get("did") != DID_ANCHOR or data.get("root_omega") != ROOT_OMEGA_ANCHOR:
                    self._json(403, {"status": "denied", "reason": "同源校验失败"})
                    return
                kid, raw = ManagerHandler.manager.create(
                    owner, quota=data.get("quota"),
                    expires_in=data.get("expires_in"), group=data.get("group"))
                self._json(200, {"status": "ok", "key_id": kid, "raw_key": raw,
                                 "warning": "原始值仅返回一次，请立即保存", "trace": TRACE_MARK})
            # 操作
            elif parts and parts[0] == "keys" and len(parts) == 3:
                kid, action = parts[1], parts[2]
                if action == "revoke":
                    ok, msg = ManagerHandler.manager.revoke(kid)
                elif action == "enable":
                    ok, msg = ManagerHandler.manager.enable(kid)
                elif action == "quota":
                    ok, msg = ManagerHandler.manager.set_quota(kid, data.get("quota"))
                else:
                    ok, msg = False, "unknown_action"
                code = 200 if ok else 404
                self._json(code, {"status": "ok" if ok else "error",
                                  "message": msg, "trace": TRACE_MARK})
            else:
                self._json(404, {"status": "not_found"})
        except Exception as e:
            self._json(500, {"status": "error", "reason": str(e)})


def main():
    parser = argparse.ArgumentParser(description="API Key 密钥管理面板")
    parser.add_argument("--port", type=int, default=8121)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--store", default="/opt/ZONGYUAN-ROOT/services/api_gateway/keys_store.json")
    args = parser.parse_args()

    ManagerHandler.manager = KeyManager(args.store)
    server = HTTPServer((args.host, args.port), ManagerHandler)
    print("=" * 54)
    print("  API Key 密钥管理面板")
    print(f"  DID: {DID_ANCHOR} | 本源根: {ROOT_OMEGA_ANCHOR}")
    print(f"  监听: {args.host}:{args.port} (仅本机)")
    print(f"  存储: {args.store}")
    print(f"  列表: http://localhost:{args.port}/keys")
    print(f"  审计: http://localhost:{args.port}/audit")
    print("=" * 54)
    server.serve_forever()


if __name__ == "__main__":
    main()
