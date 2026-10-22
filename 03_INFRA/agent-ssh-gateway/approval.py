#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
approval.py — Agent SSH 受控网关 · 变更审批门队列 (Phase2)
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

pending_approval 指令落盘 state/approval_queue.json, 仅人工口令放行:
  enqueue(cmd_record)          网关写入待审批项
  approve(causal_id, operator) 人工批准 -> 返回原指令供网关重放
  reject(causal_id, operator)  人工驳回
  list_pending()               查询队列

铁律: 队列只增状态、不自动放行; Agent 无审批入口 (无 agent 侧 API)。
"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE_PATH = os.path.join(HERE, "state", "approval_queue.json")


def _load():
    if os.path.exists(QUEUE_PATH):
        try:
            with open(QUEUE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"pending": {}, "decided": {}}


def _save(q):
    os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
    tmp = QUEUE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)
    os.replace(tmp, QUEUE_PATH)


def enqueue(agent_id, causal_id, command, risk, reasons):
    q = _load()
    if causal_id in q["pending"]:
        return {"ok": True, "dup": True}
    q["pending"][causal_id] = {
        "agent_id": agent_id, "command": command, "risk": risk,
        "reasons": reasons[:8], "enqueued_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    _save(q)
    return {"ok": True, "queued": True, "pending_count": len(q["pending"])}


def approve(causal_id, operator="human"):
    q = _load()
    item = q["pending"].pop(causal_id, None)
    if item is None:
        return {"ok": False, "reason": "not_pending:%s" % causal_id}
    item.update({"decision": "approved", "operator": operator,
                 "decided_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    q["decided"][causal_id] = item
    _save(q)
    return {"ok": True, "item": item}


def reject(causal_id, operator="human"):
    q = _load()
    item = q["pending"].pop(causal_id, None)
    if item is None:
        return {"ok": False, "reason": "not_pending:%s" % causal_id}
    item.update({"decision": "rejected", "operator": operator,
                 "decided_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    q["decided"][causal_id] = item
    _save(q)
    return {"ok": True, "item": item}


def list_pending():
    q = _load()
    return {"pending": q["pending"], "pending_count": len(q["pending"]),
            "decided_count": len(q["decided"])}


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "approve":
        print(json.dumps(approve(sys.argv[2]), ensure_ascii=False, indent=2))
    elif len(sys.argv) >= 3 and sys.argv[1] == "reject":
        print(json.dumps(reject(sys.argv[2]), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(list_pending(), ensure_ascii=False, indent=2))
