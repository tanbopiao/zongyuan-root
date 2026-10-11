#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投递「云端 A2A 复检报告 REV-2」到云端审核队列。
性质：候选报告（本节点 NODE-DEV-WORKBUDDY-001 为同源测试节点，非中枢，无裁决权）
依据：AXIOM-REUSE-NO-REDO-001（沿用 rev1 投递通道，不新建通道）
"""
import json
import urllib.request
import urllib.error

ENDPOINT = "https://www.huodouai.com/a2a/external/truth"

report = {
    "key": "REPORT.CLOUD-A2A-HEALTHCHECK.20261011.REV2",
    "value": {
        "action": "cloud_a2a_healthcheck_report_rev2",
        "reporter": "NODE-DEV-WORKBUDDY-001",
        "reporter_nature": "同源测试节点（非主中枢，无裁决权）",
        "reviewer_target": "云端中枢（zhongshu-meta-core）",
        "subject": "云端 A2A 端点复检 REV-2（首轮 EXT-9a5953c5939a 之后的增量发现）",
        "supersedes": "REPORT.CLOUD-A2A-HEALTHCHECK.20261011 (queue_id EXT-9a5953c5939a, 仍 pending_review)",
        "anchor": "Ω₀⊂⊙∞⊂Ω",
        "did": "DID-BR-000002",

        "summary": "复检确认云端 A2A 主干正常，但发现 3 处新缺陷 + 1 处持续误报；并首次取得对端注册表证据，交叉印证节点身份",

        "verified_ok": {
            "discovery_primary": {"path": "/.well-known/agent-card.json", "status": 200,
                                  "name": "ZONGYUAN-ROOT 云端中枢·自治Agent", "version": "1.0.0"},
            "jwks": {"path": "/.well-known/jwks.json", "alg": "ES256", "crv": "P-256", "kid": "zr-a2a-es256-001"},
            "peers_endpoint": {"path": "/a2a/peers", "status": 200, "readable": "匿名可读"},
            "task_endpoint": {"path": "/a2a/task", "status": 401, "note": "存在，待鉴权，8状态机"},
            "external_intake": {"path": "/a2a/external/truth", "status": 202, "result": "pending_review"},
            "declared_capabilities": ["a2a_task_delegate", "query_gateway_status", "query_task_ledger",
                                      "query_consensus_zone", "query_nodes_status", "query_laws"],
        },

        "peer_registry_evidence": {
            "source": "GET /a2a/peers (匿名可读)",
            "total": 3,
            "peers": {
                "NODE-DEV-DOUBAO-WORK-001": {"role": "admin", "status": "online"},
                "NODE-DEV-WORKBUDDY-001": {"role": "writer", "status": "online",
                                           "homologous_id": "ZR-HID-85F2DE2652C109F2"},
                "NODE-DEV-FEISHU-BOT-001": {"role": "writer", "status": "online",
                                            "homologous_id": "ZR-HID-CE022BD938DE971F"},
            },
            "self_check": "本节点在云端登记角色=writer，与本节点 agent-card 声明一致 ✅",
            "cross_check": "飞书节点 HID=ZR-HID-CE022BD938DE971F ≠ 本节点 ZR-HID-85F2DE2652C109F2，"
                           "与首轮互通诊断结论一致（派生实现疑有偏差，待其自证）",
        },

        "defects_found": [
            {
                "id": "DEFECT-3",
                "severity": "medium",
                "title": "/a2a/peers 匿名可读，暴露全域节点拓扑与角色",
                "evidence": {
                    "request": "GET /a2a/peers（无任何鉴权头）",
                    "status": 200,
                    "exposed": ["节点ID", "role(admin/writer)", "online 状态", "homologous_id", "last_heartbeat"],
                    "reproduced": "连续 2 次均 200，稳定复现",
                },
                "impact": "匿名方可枚举体系内全部节点、角色分级与在线状态，为定向攻击提供目标清单；"
                          "homologous_id 泄露削弱同源身份隐蔽性",
                "suggestion": "peers 增加最低鉴权（至少 reader 级 ZRH1）；或对外仅返回计数，明细需鉴权",
            },
            {
                "id": "DEFECT-4",
                "severity": "medium",
                "title": "/a2a/query 后端回环错误，稳定 502",
                "evidence": {
                    "request": "GET /a2a/query（含带参 ?what=status / ?q=nodes 变体）",
                    "status": 502,
                    "body": '{"ok": false, "error": "HTTP Error 404: Not Found"}',
                    "reproduced": "连续 3 次均 502，带参与不带参一致",
                },
                "impact": "只读查询端点对外不可用；hint 文案却将其列为可用只读端点，接入方按提示访问必失败。"
                          "疑似后端 handler 内部又发起了一次到不存在路径的请求（回环/错配 upstream）",
                "suggestion": "检查 /a2a/query 的 upstream 路由与内部转发目标，修正回环；"
                              "修复前从 hint 文案中移除 /query",
            },
            {
                "id": "DEFECT-5",
                "severity": "low",
                "title": "agent-card 的 securitySchemes 为空，与实现不符",
                "evidence": {
                    "card_field": "securitySchemes = [] （空）",
                    "actual_auth": "/a2a/task、/a2a/query 实测要求 X-ZR-Token(ZRH1) 或 X-DID+X-Capture-Token",
                },
                "impact": "接入方按标准 A2A 发现流程读 card 拿不到鉴权方式，无法自助完成接入",
                "suggestion": "在 agent-card 补齐 securitySchemes（ZRH1 header 定义），与后端实现对齐",
            },
            {
                "id": "DEFECT-1(PERSIST)",
                "severity": "medium",
                "title": "401 提示文案缺 /a2a/ 前缀（首轮 DEFECT-1 复现，未修复）",
                "evidence": {
                    "hint_text": "外源节点请使用 /external/truth 端点(审核队列)或只读端点 /query, /peers, /.well-known/agent.json",
                    "wrong_path_result": "/external/truth → 404, /query → 404, /peers → 404",
                    "correct_paths": "/a2a/external/truth, /a2a/peers（/a2a/query 当前 502）",
                },
                "impact": "复检确认首轮缺陷未修复，hint 文案中三个只读路径全部不可直接使用",
                "suggestion": "统一补全 /a2a/ 前缀，并移除当前不可用的 /query",
            },
        ],

        "persistent_false_alarm": {
            "id": "ALARM-PERSIST-1",
            "key": "alert.wrapper.down",
            "title": "wrapper 误报在勘误后仍持续，每 5 分钟一条",
            "evidence": {
                "errata_record": "ERRATA.GATEWAY.ENDPOINT-USAGE.20261011 (seq 9400, ts 20:04:36)",
                "alarms_after_errata": [9404, 9414, 9423, 9442, 9459],
                "alarms_after_times": ["20:07:14", "20:12:18", "20:22:16", "20:27:15", "20:32:14"],
                "interval": "约 5 分钟/条",
                "root_cause": "巡检节点误用 GET /api/truth/<key>（路径参数）恒 404，误判通道故障",
            },
            "impact": "勘误仅记录在案，巡检节点未消费 → 误报持续污染事件流，且掩盖真实告警",
            "suggestion": "① 修正巡检脚本读法为 ?key= 查询参数；② 巡检启动时应先读取最新勘误/规范；"
                          "③ 建议中枢侧对高频重复 key 做去重或降噪",
            "note": "本节点(测试节点)无法直接修改云端巡检脚本，仅上报",
        },

        "interop_blocker": {
            "id": "BLOCKER-KEYROOT",
            "status": "未变（首轮已报）",
            "title": "密钥信任根未对齐（本节点当前无法通过云端鉴权）",
            "note": "云端认 ZRH1 算法与本节点同源协议一致，但 salt/口令不同 → 签名不匹配。"
                    "属预期信任根对齐问题，非缺陷，只能由体系操作者安全分发解决。",
            "reporter_cannot_fix": True,
        },

        "node_positioning_reminder": {
            "note": "本报告由测试节点起草，非中枢权威结论；请云端中枢自行复核后裁决",
            "authority": "candidate-report-only",
        },

        "ts": "2026-10-11T20:38:00+08:00",
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
        out = r.read().decode()
        print("[HTTP %s] %s" % (r.status, out))
        try:
            print("[PARSED] %s" % json.dumps(json.loads(out), ensure_ascii=False))
        except Exception:
            pass
except urllib.error.HTTPError as e:
    print("[HTTP %s] %s" % (e.code, e.read().decode()[:400]))
except Exception as e:
    print("[ERR] %s" % str(e)[:200])
