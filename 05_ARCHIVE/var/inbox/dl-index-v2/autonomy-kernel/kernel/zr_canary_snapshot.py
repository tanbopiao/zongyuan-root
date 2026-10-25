#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT · 灰度发布 + 视觉快照记忆算子 (Canary & Snapshot)
==========================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议: NTFY-CONNECT-001 | 火斗云智AIOS
版本: V1.0 (2026-10-10)
定位: 自治内核基底深化 — 风险最小化的渐进发布 + 状态可回看

能力:
  1. 灰度发布 (CanaryRollout):
     高风险任务/新接入节点 先进灰度池(小流量验证),
     稳定后自动转正全量; 失败自动回滚
     呼应风险三优先: 风险最小 > 成本最小 > 收益最大
  2. 视觉快照记忆 (SnapshotMemory):
     为节点/任务保存状态快照(任务输出/节点状态/心跳指纹),
     异常时回看历史快照定位问题 (VISTA视觉记忆思路)
     呼应记忆网关强制对齐: 快照可回放, 防状态漂移

集成: 被 zr_cloud_ctl.py 挂载, 由 dispatch_one(灰度判定) + on_result(快照记录) 驱动
"""
import json, os, time, threading, hashlib

CANARY_FILE = "/www/wwwroot/huodouai.com/zhongshu/data/msagent-canary.json"
SNAP_FILE = "/www/wwwroot/huodouai.com/zhongshu/data/msagent-snapshots.jsonl"

# ============ 灰度发布 ============
class CanaryRollout:
    """渐进发布: 高风险进灰度, 稳定转正, 失败回滚
    节点分三态: canary(灰度) / active(转正) / quarantined(隔离)
    任务分两级: 低风险→直接active; 高风险→必须经canary验证"""
    def __init__(self, canary_file=None, canary_min_tasks=2, canary_min_success_rate=0.8):
        self.file = canary_file or CANARY_FILE
        self.canary_min_tasks = canary_min_tasks        # 灰度最少验证任务数
        self.canary_min_success_rate = canary_min_success_rate  # 灰度最低成功率
        self._lock = threading.Lock()
        self._nodes = {}   # node -> {"state":"canary/active/quarantined","ok":n,"fail":n}
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.file):
                d = json.load(open(self.file))
                self._nodes = d.get("nodes", {})
        except Exception:
            pass

    def _persist(self):
        try:
            os.makedirs(os.path.dirname(self.file), exist_ok=True)
            json.dump({"updated": time.time(), "nodes": self._nodes},
                      open(self.file, "w"), ensure_ascii=False, indent=2)
        except Exception:
            pass

    def state(self, node):
        """节点发布状态"""
        with self._lock:
            info = self._nodes.get(node, {"state": "active", "ok": 0, "fail": 0})
        return info.get("state", "active")

    def register(self, node, risk="low"):
        """节点接入: 低风险直接active; 高风险(新节点默认)先进canary"""
        with self._lock:
            if node not in self._nodes:
                state = "active" if risk == "low" else "canary"
                self._nodes[node] = {"state": state, "ok": 0, "fail": 0,
                                     "joined": time.time(), "risk": risk}
            self._persist()
        return self._nodes[node]["state"]

    def report(self, node, success):
        """节点任务结果回报: 更新计数, 达到阈值自动转正"""
        with self._lock:
            info = self._nodes.setdefault(node, {"state": "canary", "ok": 0, "fail": 0})
            info["ok" if success else "fail"] += 1
            ok, fail = info["ok"], info["fail"]
            total = ok + fail
            # canary 态: 达最小任务数且成功率达标 → 转正 active
            if info["state"] == "canary" and total >= self.canary_min_tasks:
                rate = ok / max(total, 1)
                if rate >= self.canary_min_success_rate:
                    info["state"] = "active"
                else:
                    info["state"] = "quarantined"  # 灰度失败 → 隔离
            # quarantined 态: 连续成功若干次可恢复
            if info["state"] == "quarantined" and ok >= self.canary_min_tasks and fail == 0:
                info["state"] = "canary"  # 重新灰度
            self._persist()
        return info["state"]

    def is_ready(self, node, task_risk="low"):
        """该节点是否可接此风险等级任务
        low风险: active 或 canary 均可
        high风险: 仅 active (需已验证转正)"""
        st = self.state(node)
        if task_risk == "low":
            return st in ("active", "canary")
        return st == "active"  # 高风险仅 active

    def summary(self):
        with self._lock:
            return {"nodes": {n: {"state": i["state"], "ok": i["ok"], "fail": i["fail"]}
                              for n, i in self._nodes.items()}}

# ============ 视觉快照记忆 ============
class SnapshotMemory:
    """状态快照记忆: 保存任务/节点快照, 异常回看定位
    (VISTA 视觉记忆思路 → 本体系全模态快照: 输出/心跳/指纹)"""
    def __init__(self, snap_file=None, max_snapshots=500):
        self.file = snap_file or SNAP_FILE
        self.max_snapshots = max_snapshots
        self._lock = threading.Lock()

    def snapshot(self, kind, key, payload, node=None, fingerprint=None):
        """保存一条快照
        kind: task_done / node_heartbeat / task_start / error
        key: 任务ID或节点名; payload: 快照内容; fingerprint: 内容指纹(去重用)"""
        fp = fingerprint or hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
        rec = {
            "ts": time.time(), "kind": kind, "key": key, "node": node,
            "payload": (payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False))[:500],
            "fp": fp,
        }
        try:
            os.makedirs(os.path.dirname(self.file), exist_ok=True)
            with open(self.file, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return fp

    def rollback_to(self, key, kind="task_done"):
        """回看某 key 的历史快照 (异常定位)"""
        try:
            if not os.path.exists(self.file):
                return []
            hits = []
            for line in open(self.file):
                try: r = json.loads(line)
                except: continue
                if r.get("key") == key and (kind == "*" or r.get("kind") == kind):
                    hits.append(r)
            return hits[-10:]  # 最近10条
        except Exception:
            return []

    def recent(self, n=20):
        """最近 n 条快照"""
        try:
            if not os.path.exists(self.file):
                return []
            lines = open(self.file).read().splitlines()[-n:]
            return [json.loads(l) for l in lines if l.strip()]
        except Exception:
            return []

    def prune(self):
        """快照裁剪: 超限只保留最新"""
        try:
            if not os.path.exists(self.file):
                return {"kept": 0}
            lines = open(self.file).read().splitlines()
            if len(lines) > self.max_snapshots:
                with open(self.file, "w") as f:
                    for l in lines[-self.max_snapshots:]:
                        f.write(l + "\n")
            return {"kept": min(len(lines), self.max_snapshots)}
        except Exception:
            return {"kept": 0}

# 全局实例
canary = CanaryRollout()
snapshot_mem = SnapshotMemory()

def canary_state(node):
    return canary.state(node)

def canary_ready(node, task_risk="low"):
    return canary.is_ready(node, task_risk)

def canary_report(node, success):
    return canary.report(node, success)

def snap(kind, key, payload, node=None, fingerprint=None):
    return snapshot_mem.snapshot(kind, key, payload, node, fingerprint)
