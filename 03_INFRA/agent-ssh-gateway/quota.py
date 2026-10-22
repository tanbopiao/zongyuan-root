#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quota.py — Agent SSH 受控网关 · 多级熔断配额控制器 (模块7)
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

三级熔断:
  L1 会话指令数超限      -> freeze_session (冻结该 Agent 会话)
  L2 磁盘写入/出站带宽超限 -> freeze_session
  L3 单条扰动得分超阈值    -> kill_link (切断链路, 需人工解冻)

状态持久化: state/quota_state.json (原子写, 进程安全)
解冻口令:   reset_session(agent_id) 需人工调用 (高危操作强制人工审批)
"""
import json
import os
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(HERE, "state")
STATE_PATH = os.path.join(STATE_DIR, "quota_state.json")

DEFAULT_LIMITS = {
    "session_max_cmds": 100,
    "session_max_mutations": 20,
    "session_max_disk_mb": 512,
    "session_max_net_mb": 200,
    "session_max_disturbance": 100.0,   # 会话累计扰动
    "per_cmd_max_disturbance": 10.0,    # 单条扰动阈值 -> kill_link
    "session_window_sec": 3600,
}


def _load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"sessions": {}}


def _save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)


def _session(state, agent_id, limits):
    s = state["sessions"].get(agent_id)
    now = time.time()
    if s is None or now - s.get("window_start", 0) > limits["session_window_sec"]:
        # 新窗口: 计数清零, 但 frozen 标志保留(冻结不随窗口自动解除)
        s = {"window_start": now, "cmds": 0, "mutations": 0, "disk_mb": 0.0,
             "net_mb": 0.0, "disturbance_total": 0.0, "frozen": None}
        state["sessions"][agent_id] = s
    return s


class QuotaController:
    def __init__(self, limits=None):
        self.limits = dict(DEFAULT_LIMITS)
        if limits:
            self.limits.update(limits)

    def check(self, agent_id, is_mutation=False, disturbance=0.0):
        """
        事前校验. 返回 {"allowed": bool, "fuse": None|L1|L2|L3, "reason": str, "usage": {...}}
        """
        state = _load_state()
        s = _session(state, agent_id, self.limits)

        if s["frozen"]:
            _save_state(state)
            return {"allowed": False, "fuse": s["frozen"].get("level"),
                    "reason": "session_frozen:%s" % s["frozen"].get("reason"),
                    "usage": self._usage(s)}

        # L3: 单条扰动超阈 -> kill_link
        if disturbance > self.limits["per_cmd_max_disturbance"]:
            s["frozen"] = {"level": "L3", "reason": "per_cmd_disturbance:%.2f" % disturbance,
                           "at": time.time()}
            _save_state(state)
            return {"allowed": False, "fuse": "L3", "reason": "kill_link_disturbance",
                    "usage": self._usage(s)}

        # L1: 会话指令数
        if s["cmds"] >= self.limits["session_max_cmds"]:
            s["frozen"] = {"level": "L1", "reason": "session_max_cmds", "at": time.time()}
            _save_state(state)
            return {"allowed": False, "fuse": "L1", "reason": "session_max_cmds_exceeded",
                    "usage": self._usage(s)}
        if is_mutation and s["mutations"] >= self.limits["session_max_mutations"]:
            s["frozen"] = {"level": "L1", "reason": "session_max_mutations", "at": time.time()}
            _save_state(state)
            return {"allowed": False, "fuse": "L1", "reason": "session_max_mutations_exceeded",
                    "usage": self._usage(s)}

        # L2: 磁盘/带宽
        if s["disk_mb"] >= self.limits["session_max_disk_mb"]:
            s["frozen"] = {"level": "L2", "reason": "session_max_disk_mb", "at": time.time()}
            _save_state(state)
            return {"allowed": False, "fuse": "L2", "reason": "disk_quota_exceeded",
                    "usage": self._usage(s)}
        if s["net_mb"] >= self.limits["session_max_net_mb"]:
            s["frozen"] = {"level": "L2", "reason": "session_max_net_mb", "at": time.time()}
            _save_state(state)
            return {"allowed": False, "fuse": "L2", "reason": "net_quota_exceeded",
                    "usage": self._usage(s)}

        _save_state(state)
        return {"allowed": True, "fuse": None, "reason": "ok", "usage": self._usage(s)}

    def record(self, agent_id, is_mutation=False, disk_mb=0.0, net_mb=0.0, disturbance=0.0):
        """事后计量"""
        state = _load_state()
        s = _session(state, agent_id, self.limits)
        s["cmds"] += 1
        if is_mutation:
            s["mutations"] += 1
        s["disk_mb"] = round(s["disk_mb"] + disk_mb, 3)
        s["net_mb"] = round(s["net_mb"] + net_mb, 3)
        s["disturbance_total"] = round(s["disturbance_total"] + disturbance, 3)
        _save_state(state)
        return self._usage(s)

    def force_freeze(self, agent_id, level="L1", reason="manual"):
        state = _load_state()
        s = _session(state, agent_id, self.limits)
        s["frozen"] = {"level": level, "reason": reason, "at": time.time()}
        _save_state(state)

    def reset_session(self, agent_id, operator="human"):
        """人工解冻 (高危: 仅允许人工调用, 不提供 Agent 侧入口)"""
        state = _load_state()
        s = state["sessions"].get(agent_id)
        if s is None:
            return {"ok": False, "reason": "no_session"}
        prev = s.get("frozen")
        now = time.time()
        s.update({"window_start": now, "cmds": 0, "mutations": 0, "disk_mb": 0.0,
                  "net_mb": 0.0, "disturbance_total": 0.0, "frozen": None})
        _save_state(state)
        return {"ok": True, "unfroze": prev, "operator": operator, "at": now}

    @staticmethod
    def _usage(s):
        return {k: s[k] for k in ("cmds", "mutations", "disk_mb", "net_mb",
                                  "disturbance_total", "frozen")}


if __name__ == "__main__":
    import sys
    qc = QuotaController()
    if len(sys.argv) >= 3 and sys.argv[1] == "reset":
        print(json.dumps(qc.reset_session(sys.argv[2]), ensure_ascii=False))
    elif len(sys.argv) >= 3 and sys.argv[1] == "check":
        print(json.dumps(qc.check(sys.argv[2]), ensure_ascii=False, indent=2))
    else:
        print("usage: quota.py check|reset <agent_id>")
