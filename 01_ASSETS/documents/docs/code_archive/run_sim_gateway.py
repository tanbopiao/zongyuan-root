#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地端到端仿真·Nexus v2 网关启动器
把 v2 网关的云端路径常量重定向到本地仿真目录，在本机 9443 起真实 TLS 服务。
用法: python3 run_sim_gateway.py
"""
import importlib.util, json, os, sys

SIM = "/home/user/Doubao/chats/38438306874426882/.sim_nexus"
spec = importlib.util.spec_from_file_location(
    "nexus_v2_sim", "/home/user/Doubao/chats/38438306874426882/nexus_gateway_v2_multitoken.py")
nv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nv)

# 重定向路径常量到本地仿真目录
nv.BASE = os.path.join(SIM, "engine", "nexus")
nv.TOKEN_FILE = os.path.join(nv.BASE, "nexus_token")
nv.TOKENS_JSON = os.path.join(nv.BASE, "nexus_tokens.json")
nv.CERT_FILE = os.path.join(nv.BASE, "nexus_cert.pem")
nv.KEY_FILE = os.path.join(nv.BASE, "nexus_key.pem")
nv.DB_PATH = os.path.join(SIM, "data", "memory_gateway.db")
nv.PORT = 9443

# 预置：legacy 单令牌 + 节点白名单（模拟云端签发）
legacy = "legacy_sim_token_0001"
os.makedirs(nv.BASE, exist_ok=True)
with open(nv.TOKEN_FILE, "w") as f: f.write(legacy)
os.chmod(nv.TOKEN_FILE, 0o600)

# 由 token_admin 预签发节点令牌（模拟云端 issue），此处用固定仿真令牌
nodes = {
    "nodes": {
        "LOCAL-DEV-001": {"token": "sim_node_token_LOCALDEV001", "label": "记忆闭环本地节点", "issued_at": 0},
        "LOCAL-DEV-002": {"token": "sim_node_token_LOCALDEV002", "label": "备用本地节点", "issued_at": 0},
    }
}
with open(nv.TOKENS_JSON, "w") as f: json.dump(nodes, f)
os.chmod(nv.TOKENS_JSON, 0o600)

import json
nv.load_legacy_token()
nv.load_node_tokens()
print(f"[sim] legacy_token={'已加载' if nv.LEGACY_TOKEN else '空'}")
print(f"[sim] node_tokens={list(nv.NODE_TOKENS.keys())}")
print(f"[sim] 启动 Nexus v2 TLS 网关 0.0.0.0:9443 (本地仿真)")
nv.main()
