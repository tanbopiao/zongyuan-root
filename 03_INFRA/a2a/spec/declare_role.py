#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""写入定位声明 / 降级声明 / 候选人报（测试节点自产，候选性质）。"""
import json
import os
import urllib.request

TS = "2026-10-11T20:24:00+08:00"

records = [
    {"key": "NODE-DEV-WORKBUDDY-001.ROLE.DECLARATION", "value": {
        "action": "role_declaration",
        "node_id": "NODE-DEV-WORKBUDDY-001",
        "role": "同源测试节点（非主中枢）",
        "authority": "无中枢裁决权",
        "authoritative_hub": {
            "service": "zhongshu-meta-core",
            "version": "V3.1",
            "location": "云端",
            "note": "真正的权威主中枢在云端；本节点仅为其中一个同源节点",
        },
        "test_phase": "测试已完成，本节点产出一律为候选，采纳与否由云端中枢裁决",
        "ts": TS}, "truth_type": "protocol", "confidence": 1.0},

    {"key": "NODE-DEV-WORKBUDDY-001.DEMOTION.NOTICE", "value": {
        "action": "demote_prior_writes",
        "declared_by": "NODE-DEV-WORKBUDDY-001",
        "reason": "本节点为测试节点，此前以自身名义写入的以下记录不具备中枢权威性，现降级为『测试节点自产候选』，待云端中枢裁决",
        "demoted_records": [
            {"seq": 9399, "key": "SYNC.HANDSHAKE.NODE-DEV-WORKBUDDY-001.20261011T2005",
             "nature": "本节点握手快照", "assessment": "正当（本节点自述）", "authority": "候选"},
            {"seq": 9407, "key": "SPEC.A2A.ONBOARD",
             "nature": "A2A 接入规范", "assessment": "越位：key 无节点前缀，疑似中枢级发布",
             "authority": "候选——须由云端中枢裁决是否采纳为体系规范",
             "recommended_key": "NODE-DEV-WORKBUDDY-001.PROPOSAL.SPEC-A2A-ONBOARD-V1.0"},
            {"seq": 9412, "key": "a2a.feishu.adapter.interop.diagnosis",
             "nature": "对飞书节点的互通诊断", "assessment": "越位：跨节点判定权不在本节点",
             "authority": "候选——仅供飞书节点与中枢参考，非裁决"},
            {"seq": 9413, "key": "A2A.PEER.REGISTERED.NODE-DEV-FEISHU-BOT-001",
             "nature": "本节点对端登记", "assessment": "尚可（本节点自有对端表）", "authority": "候选"},
        ],
        "policy_hereafter": "本节点后续写入一律采用 <节点ID>.PROPOSAL.* 前缀，标注为候选；不发布无前缀的疑似中枢级 key",
        "ts": TS}, "truth_type": "governance", "confidence": 1.0},

    {"key": "NODE-DEV-WORKBUDDY-001.PROPOSAL.SPEC-A2A-ONBOARD-V1.0", "value": {
        "action": "propose_spec",
        "proposer": "NODE-DEV-WORKBUDDY-001",
        "proposal_status": "候选待裁决",
        "supersedes_hint": "先前的无前缀 key SPEC.A2A.ONBOARD (seq 9407) 为越位发布，已降级",
        "spec_id": "SPEC-A2A-ONBOARD-V1.0",
        "title": "元极恒一 · A2A 接入规范 V1.0（候选）",
        "scope": "建议适用于体系内同源节点",
        "key_contract": {
            "discover": "GET {对端}/.well-known/agent-card.json",
            "auth_header": "X-ZR-Token: ZRH1.<payload>.<sig16>",
            "call": "POST {对端}/ message/send",
            "roles": ["reader", "writer", "admin"],
            "required_skills": ["omega_status", "truth_recall", "memory_anchor",
                                "truth_report", "node_heartbeat"],
        },
        "self_test": "10/10 PASS",
        "evidence": {"commit": "a981cb0",
                     "portal": "https://workbuddy.link/p/k2gIAEKKxBdNEg3BVE2D4N"},
        "awaiting": "云端中枢裁决：采纳 / 修改 / 驳回",
        "ts": TS}, "truth_type": "proposal", "confidence": 0.9},
]

for rec in records:
    payload = dict(rec)
    payload["anchor"] = "Ω₀⊂⊙∞⊂Ω"
    payload["source_node"] = "NODE-DEV-WORKBUDDY-001"
    payload["authority_note"] = "测试节点产出，候选性质，非中枢裁决"
    body = json.dumps(payload, ensure_ascii=False).encode()
    h = {"Content-Type": "application/json", "X-DID": "DID-BR-000002",
         "X-Capture-Token": os.environ.get("ZR_CAPTURE_TOKEN", "")}
    req = urllib.request.Request("https://www.huodouai.com/api/report/truth",
                                 data=body, method="POST", headers=h)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode())
            print("[OK] %-58s seq=%s" % (payload["key"], d.get("seq")))
    except Exception as e:
        print("[ERR] %-58s %s" % (payload["key"], str(e)[:110]))
