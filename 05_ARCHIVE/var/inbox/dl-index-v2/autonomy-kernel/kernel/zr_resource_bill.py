#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT · 资源账单统计算子 (ResourceBill)
==========================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议: NTFY-CONNECT-001 | 火斗云智AIOS
版本: V1.0 (2026-10-08)
定位: 自治内核基底深化 — 补上"成本可审计"一环 (风险三优先: 成本最小)

能力:
  1. 资源账单记录: 每个派发任务记录 算子/节点/命令/耗时/结果/消耗估算
     写入 JSONL 账单台账, 全链路可审计
  2. 按算子/节点聚合统计: 计算任务数/成功失败/平均耗时/累计耗时
     供资源使用看板与配额优化 (呼应 META-RULE-012 配额稳态保护)
  3. 资源指纹去重: 相同命令在短时间窗内重复执行, 标记可复用 (呼应复用优先公理)

集成: 被 zr_cloud_ctl.py 挂载, 由 dispatch_one(派发开始) + on_result(结果回传) 驱动
"""
import json, os, time, threading

BILL_FILE = "/www/wwwroot/huodouai.com/zhongshu/data/msagent-resource-bill.jsonl"
BILL_AGG_FILE = "/www/wwwroot/huodouai.com/zhongshu/data/msagent-resource-bill-agg.json"

class ResourceBill:
    """资源账单: 任务级消耗记录 + 聚合统计 + 复用去重提示"""
    def __init__(self, bill_file=None, agg_file=None, dedup_window=60):
        self.bill_file = bill_file or BILL_FILE
        self.agg_file = agg_file or BILL_AGG_FILE
        self.dedup_window = dedup_window   # 秒; 相同命令窗口内视为可复用
        self._lock = threading.Lock()
        self._running = {}      # task_id -> {node, cmd, start_ts, policy}
        self._cmd_cache = {}    # cmd -> last_ts (用于复用去重)

    def start(self, task_id, node, cmd, policy="reputation_first"):
        """派发开始: 记录起点, 返回复用提示"""
        hint = None
        with self._lock:
            last = self._cmd_cache.get(cmd)
            now = time.time()
            if last and (now - last) < self.dedup_window:
                hint = {"reusable": True, "cmd": cmd[:60], "last_ts": last}
            self._cmd_cache[cmd] = now
            self._running[task_id] = {"node": node, "cmd": cmd[:200],
                                      "start_ts": now, "policy": policy}
        return hint

    def end(self, task_id, code, detail=""):
        """结果回传: 记录结束与耗时, 写入账单"""
        with self._lock:
            info = self._running.pop(task_id, None)
        if not info:
            return None
        dur = round(time.time() - info["start_ts"], 3)
        rec = {
            "task_id": task_id, "node": info["node"],
            "cmd": info["cmd"], "policy": info.get("policy", "?"),
            "start_ts": info["start_ts"], "duration_s": dur,
            "code": code, "result": "success" if code == 0 else "failed",
            "detail": detail[:100],
        }
        try:
            os.makedirs(os.path.dirname(self.bill_file), exist_ok=True)
            with open(self.bill_file, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return rec

    def aggregate(self):
        """聚合统计: 按节点/策略聚合 任务数/成功/失败/平均耗时/累计耗时"""
        agg = {"by_node": {}, "by_policy": {}, "total": 0, "success": 0,
               "failed": 0, "total_duration_s": 0.0, "updated": time.time()}
        try:
            if not os.path.exists(self.bill_file):
                return agg
            for line in open(self.bill_file):
                try: r = json.loads(line)
                except: continue
                agg["total"] += 1
                agg["success" if r.get("code") == 0 else "failed"] += 1
                agg["total_duration_s"] += r.get("duration_s", 0)
                for key, field in (("by_node", "node"), ("by_policy", "policy")):
                    v = r.get(field, "?")
                    b = agg[key].setdefault(v, {"tasks": 0, "ok": 0, "fail": 0, "dur": 0.0})
                    b["tasks"] += 1
                    b["ok" if r.get("code") == 0 else "fail"] += 1
                    b["dur"] += r.get("duration_s", 0)
                    b["avg_s"] = round(b["dur"] / max(b["tasks"], 1), 3)
            # 持久化聚合快照
            try:
                os.makedirs(os.path.dirname(self.agg_file), exist_ok=True)
                json.dump(agg, open(self.agg_file, "w"), ensure_ascii=False, indent=2)
            except Exception:
                pass
        except Exception as e:
            agg["error"] = str(e)[:60]
        return agg

    def summary(self):
        """资源账单摘要 (看板用)"""
        a = self.aggregate()
        return {
            "total_tasks": a["total"], "success": a["success"], "failed": a["failed"],
            "total_duration_s": round(a["total_duration_s"], 2),
            "by_node": {k: {"tasks": v["tasks"], "avg_s": v["avg_s"]}
                        for k, v in a["by_node"].items()},
            "top_node": max(a["by_node"], key=lambda k: a["by_node"][k]["tasks"]) if a["by_node"] else None,
        }

# 全局实例
resource_bill = ResourceBill()

def bill_start(task_id, node, cmd, policy="reputation_first"):
    return resource_bill.start(task_id, node, cmd, policy)

def bill_end(task_id, code, detail=""):
    return resource_bill.end(task_id, code, detail)

def bill_summary():
    return resource_bill.summary()
