#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 A2A Agent Card v2.0（含同源鉴权声明）。"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SALT = os.environ.get("ZR_HOMOLOGOUS_SALT", "")
NODE_ID = os.environ.get("ZR_NODE_ID", "NODE-DEV-WORKBUDDY-001")
PUBLIC_URL = os.environ.get("ZR_A2A_PUBLIC_URL", "http://127.0.0.1:8099/")

card = {
    "name": "Omega Zongyuan Kernel (WorkBuddy Node)",
    "description": "元极恒一自治内核 A2A 互操作节点：真值确权上报/下行召回/记忆锚定/内核状态/节点心跳。"
                   "身份经同源协议 ZRH1 仲裁（双标识 Ω-TAN-7-001 + DID-BR-000002），锚定 Ω₀⊂⊙∞⊂Ω。",
    "url": PUBLIC_URL,
    "version": "2.0.0",
    "protocolVersion": "0.2.9",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": True,
        "extensions": [
            {
                "uri": "https://huodouai.com/a2a/homologous-identity/v1",
                "description": "同源协议身份仲裁：每次 message/send 携带 X-ZR-Token（ZRH1 令牌），"
                               "服务端执行 签名 + 双标识 + 时效 + 角色 四层校验。",
                "required": False,
                "params": {"header": "X-ZR-Token", "scheme": "ZRH1", "roles": ["reader", "writer", "admin"]},
            }
        ],
    },
    "defaultInputModes": ["text/plain", "application/json"],
    "defaultOutputModes": ["application/json"],
    "provider": {
        "organization": "ZONGYUAN-ROOT",
        "url": "https://atomgit.com/zongyuangen/zongyuan-root-sync",
    },
    "securitySchemes": {
        "homologousZRH1": {
            "type": "apiKey",
            "in": "header",
            "name": "X-ZR-Token",
            "description": "同源协议 ZRH1 令牌，由本节点派生密钥 HMAC-SHA256 签发，双标识绑定，零落盘。",
        }
    },
    "security": [{"homologousZRH1": []}],
    "metadata": {
        "did": "DID-BR-000002",
        "anchor": "Ω₀⊂⊙∞⊂Ω",
        "ontology_root": "Ω-TAN-7-001",
        "node_id": NODE_ID,
        "kernel": "元极恒一自治内核",
        "arbitration": "local-homologous-gate (V3.0 网关仲裁轻量落地)",
        "gateway": "https://www.huodouai.com/api/report/truth",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    },
    "skills": [
        {"id": "omega_status", "name": "内核状态",
         "description": "返回内核版本、节点身份、运行时长与协议版本（匿名只读）",
         "tags": ["kernel", "status", "bootstrap"]},
        {"id": "truth_recall", "name": "真值召回",
         "description": "按 key 从中枢记忆网关下行召回真值（匿名只读）",
         "tags": ["truth", "recall", "downlink"],
         "examples": ["recall NODE.REGISTER.HOMOGENEOUS-PEER-CODEARTS"]},
        {"id": "memory_anchor", "name": "记忆锚定",
         "description": "本地记忆索引锚定检索（匿名只读）",
         "tags": ["memory", "anchor", "index"],
         "examples": ["anchor keyword=记忆网关"]},
        {"id": "truth_report", "name": "真值上报",
         "description": "按 key/value 向中枢记忆网关确权上报真值（需 writer 角色同源令牌）",
         "tags": ["truth", "report", "gateway", "write"],
         "examples": ["report DEMO.KEY={\"msg\":\"hello\"}"]},
        {"id": "node_heartbeat", "name": "节点心跳",
         "description": "同源节点心跳上报，复用已注册节点不重复注册（需 writer 角色）",
         "tags": ["node", "heartbeat", "protocol", "write"]},
    ],
}

out = os.path.join(HERE, "agent-card.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(card, f, ensure_ascii=False, indent=2)
print(json.dumps({"written": out, "skills": [s["id"] for s in card["skills"]],
                  "public_url": PUBLIC_URL}, ensure_ascii=False, indent=2))
