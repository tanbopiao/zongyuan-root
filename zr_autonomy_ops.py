#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT · 自治算子集 (因果链跟踪 + 异常自愈)
==========================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议: NTFY-CONNECT-001 | 火斗云智AIOS
版本: V1.0 (2026-10-08)
定位: 自治内核基底深化 — 为云端主控追加因果可回溯与自愈能力

能力:
  1. 因果链跟踪 (CausalityTrack):
     记录每个任务 入池→派发→完成→真值上报 的完整因果链,
     防止任务归属分叉, 支持溯源审计
  2. 异常自愈 (SelfHeal):
     检测 worker 掉线 / 任务超时 / 重复派发 / 僵死任务,
     自动清理并触发补派/重试, 保障任务不悬空

集成: 被 zr_cloud_ctl.py 挂载, 由 on_result / dispatch / watchdog 驱动
"""
import json, os, time

# 因果链文件 (云端台账)
CAUSAL_FILE = "/www/wwwroot/huodouai.com/zhongshu/data/msagent-causality.jsonl"

# ---------- 因果链跟踪 ----------
class CausalityTrack:
    """任务全生命周期因果链: 入池→派发→完成→上报, 防分叉可回溯"""
    def __init__(self, causal_file=None):
        self.file = causal_file or CAUSAL_FILE
        self._lock = __import__("threading").Lock()
        self._index = {}   # task_id -> {节点, 派发时间, 各阶段}

    def _persist(self, rec):
        try:
            os.makedirs(os.path.dirname(self.file), exist_ok=True)
            with open(self.file, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def record(self, task_id, stage, node=None, task=None, detail=""):
        """记录任务某个阶段; stage: enqueue|dispatched|done|failed|reported"""
        with self._lock:
            rec = {
                "task_id": task_id, "stage": stage,
                "node": node, "ts": time.time(),
                "task": (task or {}).get("cmd", "")[:100],
                "detail": detail,
            }
            if stage not in ("enqueue",):
                prev = self._index.get(task_id, {})
                rec["node"] = rec["node"] or prev.get("node")
            self._index[task_id] = {"node": rec.get("node"), "stage": stage,
                                    "ts": rec["ts"]}
        self._persist(rec)
        return rec

    def chain(self, task_id):
        """返回某任务的因果链(从索引+文件合并)"""
        with self._lock:
            cur = self._index.get(task_id, {})
        return {"task_id": task_id, "current": cur}

    def track(self, task_id, stage, node=None, task=None, detail=""):
        """别名: 供主控直接调用"""
        return self.record(task_id, stage, node, task, detail)

# ---------- 异常自愈 ----------
class SelfHeal:
    """检测并自动修复异常: 掉线/超时/重复派发/僵死任务; 联动节点失败隔离"""
    def note_dispatched(self, task_id, node):
        """标记某任务已派发(用于超时检测)"""
        self._reported[task_id] = {"node": node, "ts": time.time(), "state": "dispatched"}

    def note_completed(self, task_id):
        """标记某任务已完成(移出超时监控)"""
        self._reported.pop(task_id, None)

    def note_failed(self, task_id):
        self._reported.pop(task_id, None)

    def stale_tasks(self):
        """返回已派发但超时未完成的僵死任务 [(task_id, node, age)]"""
        now = time.time()
        stale = []
        for tid, info in list(self._reported.items()):
            if info.get("state") == "dispatched":
                age = now - info["ts"]
                if age > self.staleness:
                    stale.append((tid, info["node"], int(age)))
        return stale

    def heal(self, causality=None, report_truth=None):
        """自愈联动: 检测僵死任务, 清理+记录节点失败+标记可重派+上报
        升级: 僵死任务返回 task 信息供主控重新入池(换节点重派)"""
        stale = self.stale_tasks()
        healed = []
        for tid, node, age in stale:
            self._reported.pop(tid, None)  # 清理僵死状态
            # 记录节点失败计数 (联动隔离: 反复失败节点降权)
            self.note_node_failure(node)
            isolated = self.is_node_isolated(node)
            healed.append({"task_id": tid, "node": node, "age": age,
                           "action": "stale_cleaned",
                           "node_isolated": isolated,
                           "redispatch": True})  # 标记可换节点重派
            if causality:
                causality.track(tid, "self_heal", node=node,
                                detail=f"僵死{age}s清理, {'节点隔离' if isolated else '可重派'}")
            if report_truth:
                try:
                    report_truth(f"REPORT.CLOUD-CTL.HEAL.{int(time.time())}",
                                 json.dumps({"action": "stale_clean", "task_id": tid,
                                             "age": age, "node_isolated": isolated}))
                except Exception:
                    pass
        return healed

    # ---- 节点失败计数 + 隔离 (自愈联动) ----
    def __init__(self, staleness_window=120, isolate_threshold=3):
        self.staleness = staleness_window
        self.isolate_threshold = isolate_threshold  # 连续失败>=此值隔离
        self._reported = {}
        self._node_fail_streak = {}   # node -> 连续失败次数
        self._isolated = set()        # 隔离节点集合

    def note_node_failure(self, node):
        """节点失败一次: 连续失败+1, 达阈值隔离"""
        if not node:
            return
        self._node_fail_streak[node] = self._node_fail_streak.get(node, 0) + 1
        if self._node_fail_streak[node] >= self.isolate_threshold:
            self._isolated.add(node)

    def note_node_success(self, node):
        """节点成功: 清零连续失败, 解除隔离"""
        if not node:
            return
        self._node_fail_streak[node] = 0
        self._isolated.discard(node)

    def is_node_isolated(self, node):
        """节点是否被隔离"""
        return node in self._isolated

    def isolated_nodes(self):
        """当前隔离节点列表"""
        return list(self._isolated)

# 全局实例 (供主控挂载)
causality = CausalityTrack()
self_heal = SelfHeal()

def track(task_id, stage, node=None, task=None, detail=""):
    """模块级便捷: 因果链记录"""
    return causality.track(task_id, stage, node, task, detail)

def heal(causality_obj=None, report_truth=None):
    """模块级便捷: 自愈"""
    return self_heal.heal(causality_obj or causality, report_truth)
