#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nexus 节点级令牌管理工具 v2.0（本地仿真产物）
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

用于管理 nexus_tokens.json 白名单：为本地节点签发独立令牌、列出、吊销。
安全：令牌文件 0600；令牌仅在签发瞬间 stdout 打印一次，不进日志。

用法：
  python3 nexus_token_admin.py issue --node-id LOCAL-DEV-001 [--label 记忆闭环本地节点]
  python3 nexus_token_admin.py list
  python3 nexus_token_admin.py revoke --node-id LOCAL-DEV-001
"""
import argparse
import json
import os
import secrets
import sys
import time

# 与网关一致的路径（本地仿真：可覆盖为测试目录）
BASE = os.environ.get("NEXUS_BASE", "/opt/ZONGYUAN-ROOT/engine/nexus")
TOKENS_JSON = os.path.join(BASE, "nexus_tokens.json")


def load():
    if os.path.isfile(TOKENS_JSON):
        try:
            with open(TOKENS_JSON, "r", encoding="utf-8") as f:
                d = json.load(f)
            return d.get("nodes", d)
        except Exception:
            return {}
    return {}


def save(nodes):
    os.makedirs(BASE, exist_ok=True)
    tmp = TOKENS_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"nodes": nodes, "updated_at": int(time.time())}, f, ensure_ascii=False, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, TOKENS_JSON)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_issue = sub.add_parser("issue", help="签发节点令牌")
    p_issue.add_argument("--node-id", required=True)
    p_issue.add_argument("--label", default="")

    p_list = sub.add_parser("list", help="列出节点(脱敏)")

    p_revoke = sub.add_parser("revoke", help="吊销节点令牌")
    p_revoke.add_argument("--node-id", required=True)

    args = ap.parse_args()

    nodes = load()

    if args.cmd == "issue":
        if args.node_id in nodes:
            print(f"[warn] 节点 {args.node_id} 已存在，将重新签发（旧令牌立即失效）", file=sys.stderr)
        token = secrets.token_urlsafe(48)  # 48字节随机，高熵
        nodes[args.node_id] = {"token": token, "label": args.label, "issued_at": int(time.time())}
        save(nodes)
        # 仅此一次明文输出，供受控注入本地
        print(f"ISSUED node_id={args.node_id}")
        print(f"TOKEN={token}")
        print("提示：此令牌仅显示一次，请立即注入本地受控文件(0600)或环境变量。")

    elif args.cmd == "list":
        print("节点令牌白名单（脱敏）:")
        if not nodes:
            print("  (空)")
        for nid, info in nodes.items():
            tok = info.get("token", "") if isinstance(info, dict) else str(info)
            label = info.get("label", "") if isinstance(info, dict) else ""
            print(f"  {nid} | hash={__import__('hashlib').sha256(tok.encode()).hexdigest()[:16]} | {label}")

    elif args.cmd == "revoke":
        if args.node_id in nodes:
            del nodes[args.node_id]
            save(nodes)
            print(f"REVOKED node_id={args.node_id}")
        else:
            print(f"[error] 节点 {args.node_id} 不存在", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
