"""算子1: 目标结构化锚定算子 (核心底座).

职责: 固化初始任务目标 —— 只读锁档 / 禁止修改覆盖刷新遗忘 / 每轮推理前对齐校验.

固定字段(方案强制): core_target / constraint_conditions / success_criteria / deadline
固定阈值: 语义相似度 < 0.75 -> 一级预警 (由 semantic 算子执行, 阈值来自 config.anchor)

零幻觉说明: 自然语言->结构化目标采用**规则化解析**(分句/关键词), 不调用LLM,
避免锚定环节自身引入幻觉; 解析结果即用户原话的结构化映射, 可人工复核。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time

GOAL_FIELDS = ("core_target", "constraint_conditions", "success_criteria", "deadline")

_CONSTRAINT_KW = ("必须", "不得", "禁止", "不超过", "至少", "只能", "限", "范围内", "≥", "≤", "<=", ">=", "在", "内完成")
_SUCCESS_KW = ("完成", "达成", "生成", "通过", "输出", "交付", "成功率", "验证")
_DEADLINE_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}|\d{1,2}\s*月\s*\d{1,2}\s*[日号]|\d+\s*(?:天|小时|分钟)内"
    r"|截止[至到]?\s*[0-9][0-9\-/年月日.]*)"
)


class AnchorImmutableError(Exception):
    """任何修改/覆盖/刷新只读锚的尝试都抛此错(铁律: 运行全程禁止修改)。"""


class GoalAnchor:
    """结构化目标文档 (不可变值对象)。"""

    __slots__ = ("core_target", "constraint_conditions", "success_criteria", "deadline")

    def __init__(self, core_target: str, constraint_conditions: list[str],
                 success_criteria: list[str], deadline: str):
        self.core_target = core_target
        self.constraint_conditions = list(constraint_conditions)
        self.success_criteria = list(success_criteria)
        self.deadline = deadline

    def to_dict(self) -> dict:
        return {
            "core_target": self.core_target,
            "constraint_conditions": self.constraint_conditions,
            "success_criteria": self.success_criteria,
            "deadline": self.deadline,
        }

    def text(self) -> str:
        """供语义相似度计算的目标全文。"""
        parts = [self.core_target] + self.constraint_conditions + self.success_criteria
        if self.deadline:
            parts.append(f"执行阈值:{self.deadline}")
        return "\n".join(p for p in parts if p)

    # 禁止就地修改
    def __setattr__(self, *_):
        raise AnchorImmutableError("目标文档为只读对象, 禁止修改/覆盖/刷新")

    @classmethod
    def parse(cls, natural_language: str) -> "GoalAnchor":
        """自然语言任务 -> 标准JSON结构化目标 (规则化解析, 确定性、可复现)。"""
        raw = (natural_language or "").strip()
        if not raw:
            raise ValueError("空任务: 无法锚定目标")
        clauses = [c.strip() for c in re.split(r"[。；;\n]|，|,", raw) if c.strip()]

        core = clauses[0] if clauses else raw
        constraints = [c for c in clauses[1:] if any(k in c for k in _CONSTRAINT_KW)]
        if not constraints:                     # 首句内嵌约束也提取
            constraints = [c for c in clauses if any(k in c for k in _CONSTRAINT_KW) and c != core]
        success = [c for c in clauses if any(k in c for k in _SUCCESS_KW)
                   and c not in constraints and c != core]
        if not success:
            success = [f"达成核心目标: {core}"]   # 无显式成功标准时的确定性兜底(非编造)

        dm = _DEADLINE_RE.search(raw)
        deadline = dm.group(1) if dm else "未声明(按任务默认执行阈值)"

        # __slots__ 对象用 object.__setattr__ 构造
        obj = object.__new__(cls)
        object.__setattr__(obj, "core_target", core)
        object.__setattr__(obj, "constraint_conditions", constraints)
        object.__setattr__(obj, "success_criteria", success)
        object.__setattr__(obj, "deadline", deadline)
        return obj


class AnchorStore:
    """只读独立存储: 落盘 0444 + SHA256 校验, 运行全程禁止修改/覆盖/刷新/遗忘.

    - save(): 首次写入后 chmod 0444, 旁路写 .sha256 校验文件
    - get(): 只读加载, 加载时复核哈希, 发现篡改即拒
    - 任何 set/update/delete 尝试 -> AnchorImmutableError
    """

    def __init__(self, dir_path: str):
        self.dir = dir_path
        os.makedirs(self.dir, exist_ok=True)
        self._mem: dict[str, dict] = {}
        self._lock = threading.RLock()

    def _path(self, task_id: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_\-]", "_", task_id)
        return os.path.join(self.dir, f"{safe}.json")

    @staticmethod
    def _sha(doc: dict) -> str:
        canon = json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canon.encode("utf-8")).hexdigest()

    def save(self, task_id: str, goal: GoalAnchor) -> dict:
        """写入一次, 之后不可变 (二次 save 内容不同 -> 抛错)。"""
        with self._lock:
            doc = goal.to_dict()
            path = self._path(task_id)
            if os.path.exists(path):
                old = json.loads(open(path, encoding="utf-8").read())
                if old.get("_doc") != doc:
                    raise AnchorImmutableError(f"锚已存在且禁止覆盖: {task_id}")
                self._mem[task_id] = old
                return old
            wrap = {"_doc": doc, "_sha256": self._sha(doc),
                    "_task_id": task_id, "_locked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "_readonly": True}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(wrap, f, ensure_ascii=False, indent=2)
            os.chmod(path, 0o444)                       # 只读锁档
            with open(path + ".sha256", "w", encoding="utf-8") as f:
                f.write(wrap["_sha256"] + "\n")
            os.chmod(path + ".sha256", 0o444)
            self._mem[task_id] = wrap
            return wrap

    def get(self, task_id: str) -> GoalAnchor:
        """只读取回 + 哈希复核 (防遗忘/防篡改)。"""
        with self._lock:
            if task_id in self._mem:
                wrap = self._mem[task_id]
            else:
                path = self._path(task_id)
                if not os.path.exists(path):
                    raise KeyError(f"目标锚缺失(禁止遗忘, 必须先锚定): {task_id}")
                wrap = json.loads(open(path, encoding="utf-8").read())
                self._mem[task_id] = wrap
            doc = wrap["_doc"]
            if self._sha(doc) != wrap["_sha256"]:
                raise AnchorImmutableError(f"锚哈希校验失败, 检测到篡改: {task_id}")
            g = object.__new__(GoalAnchor)
            object.__setattr__(g, "core_target", doc["core_target"])
            object.__setattr__(g, "constraint_conditions", doc["constraint_conditions"])
            object.__setattr__(g, "success_criteria", doc["success_criteria"])
            object.__setattr__(g, "deadline", doc["deadline"])
            return g

    # ---- 以下三个方法恒抛错: 铁律 = 运行全程禁止修改/覆盖/刷新 ----
    def update(self, task_id: str, *_):
        raise AnchorImmutableError("禁止修改目标锚")

    def overwrite(self, task_id: str, *_):
        raise AnchorImmutableError("禁止覆盖目标锚")

    def refresh(self, task_id: str, *_):
        raise AnchorImmutableError("禁止刷新目标锚(重锚定=重新对齐, 非改锚)")
