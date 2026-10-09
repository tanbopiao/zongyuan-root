#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT · 记忆蒸馏 + A/B 策略实验算子
==========================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议: NTFY-CONNECT-001 | 火斗云智AIOS
版本: V1.0 (2026-10-08)
定位: 自治内核基底深化 — 记忆自净化 + 派发策略自动寻优

能力:
  1. 记忆蒸馏 (MemoryDistiller):
     从历史任务/节点结果中蒸馏高价值经验真值,
     低价值/陈旧记忆自动淘汰, 防记忆库膨胀越堆越乱
  2. A/B 策略实验 (PolicyBandit, epsilon-greedy):
     在多个派发策略间灰度实验(信誉优先/能力优先/均衡),
     按成功率自动选最优策略, 持续寻优
"""
import json, os, time, math, random

# 经验记忆文件
MEMORY_FILE = "/www/wwwroot/huodouai.com/zhongshu/data/msagent-memory.jsonl"
# 策略实验状态文件
BANDIT_FILE = "/www/wwwroot/huodouai.com/zhongshu/data/msagent-bandit.json"

# ============ 记忆蒸馏 ============
class MemoryDistiller:
    """从历史结果蒸馏高价值经验, 淘汰低价值陈旧记忆 (SFMP 联邦记忆池思路)"""
    def __init__(self, memory_file=None, max_kept=500, stale_days=7):
        self.file = memory_file or MEMORY_FILE
        self.max_kept = max_kept           # 最多保留经验条数
        self.stale_age = stale_days * 86400  # 超过此秒数视为陈旧
        self._lock = __import__("threading").Lock()

    def distill(self, event_type, payload, value_score=1.0):
        """蒸馏一条经验: 高价值事件沉淀为记忆真值
        event_type: node_success/node_fail/cmd_pattern/strategy_result
        value_score: 价值分(0~2), 高价值才沉淀
        """
        if value_score < 0.5:
            return None  # 低价值不沉淀
        rec = {
            "ts": time.time(), "type": event_type,
            "payload": (payload or {})[:200] if isinstance(payload, str) else payload,
            "value": value_score,
        }
        try:
            os.makedirs(os.path.dirname(self.file), exist_ok=True)
            with open(self.file, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return rec

    def prune(self):
        """记忆净化: 淘汰陈旧 + 超限裁剪(保留高价值/新近)"""
        try:
            if not os.path.exists(self.file):
                return {"kept": 0, "pruned": 0}
            lines = open(self.file).read().splitlines()
            now = time.time()
            kept = []
            pruned = 0
            for line in lines:
                try: r = json.loads(line)
                except: continue
                age = now - r.get("ts", 0)
                # 陈旧且低价值 → 淘汰
                if age > self.stale_age and r.get("value", 1.0) < 1.0:
                    pruned += 1; continue
                kept.append(r)
            # 超限裁剪: 按价值+新近排序保留前 max_kept
            if len(kept) > self.max_kept:
                kept.sort(key=lambda r: (r.get("value", 1.0), r.get("ts", 0)),
                          reverse=True)
                pruned += len(kept) - self.max_kept
                kept = kept[:self.max_kept]
            with open(self.file, "w") as f:
                for r in kept:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            return {"kept": len(kept), "pruned": pruned}
        except Exception as e:
            return {"kept": 0, "pruned": 0, "error": str(e)[:60]}

    def summary(self):
        """记忆库摘要"""
        try:
            if not os.path.exists(self.file):
                return {"total": 0}
            lines = open(self.file).read().splitlines()
            types = {}
            for line in lines:
                try: r = json.loads(line); t = r.get("type", "?")
                except: continue
                types[t] = types.get(t, 0) + 1
            return {"total": len(lines), "by_type": types}
        except Exception:
            return {"total": 0}

# ============ A/B 策略实验 (epsilon-greedy) ============
POLICIES = ["reputation_first", "capability_first", "balanced"]

class PolicyBandit:
    """派发策略多臂老虎机: epsilon-greedy 自动寻优
    - reputation_first: 优先高信誉节点
    - capability_first: 优先能力匹配度高
    - balanced: 均衡轮询
    每轮记录各策略成功率, 自动偏向最优策略(探索+利用)
    """
    def __init__(self, bandit_file=None, epsilon=0.2):
        self.file = bandit_file or BANDIT_FILE
        self.epsilon = epsilon  # 探索概率
        self.stats = {p: {"plays": 0, "wins": 0, "value": 0.5} for p in POLICIES}
        self._lock = __import__("threading").Lock()
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.file):
                d = json.load(open(self.file))
                self.stats = d.get("stats", self.stats)
        except Exception:
            pass

    def _persist(self):
        try:
            os.makedirs(os.path.dirname(self.file), exist_ok=True)
            json.dump({"updated": time.time(), "stats": self.stats},
                      open(self.file, "w"), ensure_ascii=False, indent=2)
        except Exception:
            pass

    def choose_policy(self):
        """选策略: epsilon 概率探索(随机), 否则利用(当前 value 最高)"""
        with self._lock:
            if random.random() < self.epsilon:
                return random.choice(POLICIES)
            # 利用: 选 value 最高
            return max(POLICIES, key=lambda p: self.stats[p].get("value", 0.5))

    def report(self, policy, success):
        """回报某策略结果: 更新 value (成功率滑动平均)"""
        with self._lock:
            s = self.stats[policy]
            s["plays"] += 1
            if success:
                s["wins"] += 1
            # value = 成功率 (指数滑动, 近期更敏感)
            rate = s["wins"] / max(s["plays"], 1)
            s["value"] = round(rate, 3)
        self._persist()

    def best_policy(self):
        """当前最优策略"""
        with self._lock:
            return max(POLICIES, key=lambda p: self.stats[p].get("value", 0.5))

    def summary(self):
        with self._lock:
            return {"policies": dict(self.stats),
                    "best": self.best_policy(),
                    "epsilon": self.epsilon}

# 全局实例
memory_distiller = MemoryDistiller()
policy_bandit = PolicyBandit()

def distill(event_type, payload, value_score=1.0):
    return memory_distiller.distill(event_type, payload, value_score)

def prune_memory():
    return memory_distiller.prune()

def choose_policy():
    return policy_bandit.choose_policy()

def report_policy(policy, success):
    return policy_bandit.report(policy, success)

def best_policy():
    return policy_bandit.best_policy()
