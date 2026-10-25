"""阈值配置入口 —— 动态阈值适配层.

设计约束(全局执行准则2): 默认值与方案固定阈值逐字一致, 禁止篡改;
本文件只提供"加载/覆盖/热更新"能力, 覆盖行为全部留痕。
"""
from __future__ import annotations

import copy
import json
import os
import threading
import time

# ---- 方案固定阈值默认值 (零增删改) ----
DEFAULTS: dict = {
    # 1 目标锚定: 语义相似度 < 0.75 -> 一级预警
    "anchor": {"similarity_warn": 0.75},
    # 2 语义漂移: 距离 > 0.3 判定漂移; 单任务最大推理 20 步
    "semantic": {
        "drift_distance": 0.3,
        "max_steps": 20,
        "embedding_backend": "bge-m3",          # 默认接入 BGE-m3
        "bge_model": "BAAI/bge-m3",
        "fallback_backend": "lexical",          # 离线不可用时降级(留痕, 见 ALERTS.md)
        "allow_fallback": True,
        "vector_dim": 512,
        # lexical 降级后端分数标定系数: 0.75/0.587=1.2770 -> 1.28
        # (拟合集=对齐样本前10条下界; 留出验证=后10对齐+20漂移全过; 漂移上界0.172->0.220)
        # BGE-m3 后端原生余弦, 不标定; 系数可经 config 热更新迭代
        "lexical_calibration": 1.28,
    },
    # 3 行为风控: 连续3次重复动作=死循环; 上下文>=90% 重锚定
    "behavior": {
        "repeat_action_limit": 3,
        "token_limit": 200000,
        "api_call_limit": 100,
        "duration_limit_sec": 1800,
        "resource_warn_ratio": 0.8,             # 临近上限预警线
        "context_saturation": 0.90,
    },
    # 4 跨Agent: 父子目标相似度 < 0.6 拦截
    "collab": {"parent_child_similarity_min": 0.6},
    # 4b 扩展(补齐于积分耗尽归因分析): 平台积分/额度熔断
    #    >=0.80 一级预警; >=0.95 二级只读; budget<=0 不判定
    "quota": {
        "enable": True,
        "warn_ratio": 0.80,
        "critical_ratio": 0.95,
        "quota_file": "config/platform_quota.json",
    },
    # 5 三级熔断升级链: 2次一级->二级; 3次二级->三级
    "circuit": {"l1_to_l2_count": 2, "l2_to_l3_count": 3,
                "l1_clear_clean_steps": 3},   # 重锚定后连续3步校验通过才清"连续一级"计数
    # 运行时落盘
    "runtime": {
        "workdir": "",            # 空=使用调用方传入的运行目录
        "log_dir": "logs",
        "report_dir": "reports",
        "workorder_dir": "workorders",
        "anchor_dir": "anchor_store",
    },
}


class ThresholdConfig:
    """阈值配置对象: 点路径读取 + 受控覆盖 + 热更新.

    - load(): 从 JSON 文件加载(缺项回退默认值, 保证阈值完整)
    - override(): 显式覆盖(记录到 self.audit 供审计)
    - reload(): 热更新入口(基于历史数据迭代调参时使用)
    """

    def __init__(self, path: str | None = None, overrides: dict | None = None):
        self._path = path
        self._lock = threading.RLock()
        self.audit: list[dict] = []          # 阈值变更审计
        self._data = copy.deepcopy(DEFAULTS)
        if path and os.path.exists(path):
            self._load_file(path)
        if overrides:
            self.override(overrides, source="code")

    # -- 加载 --
    def _load_file(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self._merge(self._data, raw)
        self._path = path

    def _merge(self, base: dict, patch: dict) -> None:
        """深合并; 未知键拒绝(防止配置漂移引入未定义阈值); `_`前缀为元数据键跳过。"""
        for k, v in patch.items():
            if k.startswith("_"):
                continue                             # _comment 等元数据键
            if k not in base:
                raise KeyError(f"未知配置键(拒绝漂移): {k}")
            if isinstance(base[k], dict) and isinstance(v, dict):
                self._merge(base[k], v)
            else:
                base[k] = v

    # -- 读取 --
    def get(self, dotted: str, default=None):
        """get('semantic.drift_distance') -> 0.3"""
        node = self._data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def section(self, name: str) -> dict:
        with self._lock:
            return copy.deepcopy(self._data.get(name, {}))

    def snapshot(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._data)

    # -- 覆盖 / 热更新 --
    def override(self, patch: dict, source: str = "api") -> None:
        """受控覆盖: 只允许已定义键, 全量记录审计。"""
        with self._lock:
            before = copy.deepcopy(self._data)
            self._merge(self._data, patch)          # 未知键直接抛 KeyError
            changes = self._diff(before, self._data)
            if changes:
                self.audit.append({
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "source": source, "changes": changes,
                })

    def reload(self) -> None:
        """热更新(基于历史数据迭代阈值参数的入口)。"""
        if self._path and os.path.exists(self._path):
            with self._lock:
                self._data = copy.deepcopy(DEFAULTS)
            self._load_file(self._path)

    @staticmethod
    def _diff(a: dict, b: dict, prefix: str = "") -> list[dict]:
        out = []
        for k in b:
            p = f"{prefix}{k}"
            if isinstance(b[k], dict):
                out.extend(ThresholdConfig._diff(a.get(k, {}), b[k], p + "."))
            elif a.get(k) != b[k]:
                out.append({"key": p, "old": a.get(k), "new": b[k]})
        return out
