#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投递「云端 A2A 检查报告」到云端审核队列。
性质：候选报告（本节点 NODE-DEV-WORKBUDDY-001 为同源测试节点，非中枢）
"""
import json
import urllib.request
import urllib.error

ENDPOINT = "https://www.huodouai.com/a2a/external/truth"

report = {
    "key": "REPORT.CLOUD-A2A-HEALTHCHECK.20261011",
    "value": {
        "action": "cloud_a2a_healthcheck_report",
        "reporter": "NODE-DEV-WORKBUDDY-001",
        "reporter_nature": "同源测试节点（非主中枢，无裁决权）",
        "reviewer_target": "云端中枢（zhongshu-meta-core）",
        "subject": "云端 A2A 端点健康检查",
        "anchor": "Ω₀⊂⊙∞⊂Ω",
        "did": "DID-BR-000002",

        "summary": "云端 A2A 运行正常，端点/签名/鉴权机制齐备；发现 2 处文档缺陷 + 1 处互通阻塞",

        "verified_ok": {
            "discovery_primary": {"path": "/.well-known/agent-card.json", "status": 200,
                                  "name": "ZONGYUAN-ROOT 云端中枢·自治Agent", "version": "1.0.0"},
            "discovery_mcp": {"path": "/.well-known/agent.json", "status": 200,
                              "note": "MCP只读查询Agent, v1.1.0"},
            "jwks": {"path": "/.well-known/jwks.json", "status": 200,
                     "alg": "ES256", "crv": "P-256", "kid": "zr-a2a-es256-001"},
            "task_endpoint": {"path": "/a2a/task", "status": 401, "note": "存在，待鉴权，8状态机"},
            "query_endpoints": [{"path": "/a2a/query", "status": 401},
                                {"path": "/a2a/peers", "status": 401}],
            "external_intake": {"path": "/a2a/external/truth", "status": 202,
                                "test_queue_id": "EXT-5c3de47e5272", "result": "pending_review"},
            "declared_capabilities": ["a2a_task_delegate", "query_gateway_status",
                                      "query_task_ledger", "query_consensus_zone",
                                      "query_nodes_status", "query_laws"],
        },

        "defects_found": [
            {
                "id": "DEFECT-1",
                "severity": "medium",
                "title": "401 鉴权提示文案缺少 /a2a/ 路径前缀",
                "evidence": {
                    "hint_text": "外源节点请使用 /external/truth 端点(审核队列)或只读端点 /query, /peers, /.well-known/agent.json",
                    "actual_correct_paths": ["/a2a/external/truth", "/a2a/query", "/a2a/peers"],
                    "wrong_path_result": "HTTP 404 (nginx 404 页)",
                    "correct_path_result": "401 (鉴权拦截，端点存在)",
                },
                "impact": "接入方按提示访问 /query /peers 会撞 404，误判为端点不存在，增加接入成本",
                "suggestion": "将 hint 文案中的路径补全 /a2a/ 前缀",
            },
            {
                "id": "DEFECT-2",
                "severity": "low",
                "title": "审核队列投递无输入校验",
                "evidence": {
                    "empty_body": "{} → 202 受理",
                    "missing_key_field": "{value:..} 无 key → 202 受理",
                    "note": "任意 body 均返回 queue_id，无 schema 校验",
                },
                "impact": "无效投递占用队列，审核侧需额外过滤",
                "suggestion": "投递侧增加最小字段校验（至少要求 key/value），非法投递返 400",
            },
        ],

        "interop_blocker": {
            "id": "BLOCKER-KEYROOT",
            "title": "密钥信任根未对齐（本节点当前无法通过云端鉴权）",
            "evidence": {
                "cloud_auth_scheme": "需 X-ZR-Token(ZRH1) 或 X-DID+X-Capture-Token",
                "zrh1_compat": "云端认 ZRH1 → 与本节点同源协议算法一致 ✅",
                "test_result": "以本节点 ZRH1 令牌请求 /a2a/query,/a2a/peers,/a2a/task 均 401",
                "did_capture_test": "X-DID+X-Capture-Token 被视作外源 → 404",
                "root_cause": "云端与本节点使用不同 salt/口令 → 派生密钥不同 → 签名不匹配",
            },
            "nature": "非缺陷，属预期的信任根对齐问题",
            "resolution": "需由体系操作者决定并安全分发统一的 salt/口令（不经网关/仓库）",
            "reporter_cannot_fix": True,
        },

        "node_positioning_reminder": {
            "note": "本报告由测试节点起草，非中枢权威结论；请中枢自行复核",
            "authority": "candidate-report-only",
        },

        "ts": "2026-10-11T20:33:00+08:00",
    },
    "anchor": "Ω₀⊂⊙∞⊂Ω",
    "source_node": "NODE-DEV-WORKBUDDY-001",
    "truth_type": "report",
}

body = json.dumps(report, ensure_ascii=False).encode()
req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                             headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        print("[HTTP %s] %s" % (r.status, r.read().decode()))
except urllib.error.HTTPError as e:
    print("[HTTP %s] %s" % (e.code, e.read().decode()[:400]))
except Exception as e:
    print("[ERR] %s" % str(e)[:200])
