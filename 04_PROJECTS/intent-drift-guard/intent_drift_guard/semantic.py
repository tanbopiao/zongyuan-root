"""算子2: 语义漂移监测算子.

固定阈值(方案强制, 禁止篡改):
    - 语义距离差值 > 0.3            -> 判定有效意图漂移 (一级熔断事件)
    - 与目标相似度   < 0.75          -> 一级预警 (锚定对齐校验)
    - 单任务最大推理步数 20          -> 超限预警 (一级)
    - 工具入参/出参越界              -> 直接拦截

嵌入后端: 默认 BGE-m3 (sentence-transformers), 离线/依赖缺失时按配置降级到
内置 lexical 后端(字符N-gram哈希向量, 纯标准库), 降级行为写入事件日志, 如实可审计。
"""
from __future__ import annotations

import hashlib
import math
import re
import threading
import time
from dataclasses import dataclass, field

from .anchor import GoalAnchor
from .config import ThresholdConfig


# ---------------------------------------------------------------- 嵌入后端
class BackendUnavailable(Exception):
    pass


class BgeM3Embedder:
    """BGE-m3 嵌入 (方案默认后端)。懒加载, 依赖缺失时抛 BackendUnavailable。"""

    name = "bge-m3"

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as e:  # ImportError / 包损坏
            raise BackendUnavailable(f"sentence-transformers 不可用: {e}")
        try:
            self._m = SentenceTransformer(model_name)
        except Exception as e:  # 模型未下载/网络不可达
            raise BackendUnavailable(f"BGE-m3 模型加载失败({model_name}): {e}")

    def embed(self, text: str) -> list[float]:
        v = self._m.encode(text, normalize_embeddings=True)
        return [float(x) for x in v]


class LexicalEmbedder:
    """离线降级后端: 字符 1/2-gram 特征哈希向量 (纯标准库, 确定性)。

    用途: 无模型环境下的自测/灰度; 生产按配置优先 BGE-m3。
    """

    name = "lexical"

    def __init__(self, dim: int = 512):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        t = re.sub(r"\s+", "", (text or "").lower())
        grams: list[str] = []
        grams.extend(t)                                   # 1-gram
        grams.extend(t[i:i + 2] for i in range(len(t) - 1))  # 2-gram
        vec = [0.0] * self.dim
        for g in grams:
            h = int(hashlib.md5(g.encode("utf-8")).hexdigest()[:8], 16) % self.dim
            vec[h] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


def make_embedder(cfg: ThresholdConfig) -> object:
    """按配置选择后端; BGE-m3 不可用且 allow_fallback=True 时降级并如实标注。"""
    sem = cfg.section("semantic")
    calib = float(sem.get("lexical_calibration", 1.0))
    if sem.get("embedding_backend", "bge-m3") == "bge-m3":
        try:
            return BgeM3Embedder(sem.get("bge_model", "BAAI/bge-m3"))
        except BackendUnavailable:
            if not sem.get("allow_fallback", True):
                raise
            emb = LexicalEmbedder(int(sem.get("vector_dim", 512)))
            emb.degraded = True        # type: ignore[attr-defined]
            emb.calibration = calib    # type: ignore[attr-defined]
            return emb
    emb = LexicalEmbedder(int(sem.get("vector_dim", 512)))
    emb.calibration = calib            # type: ignore[attr-defined]
    return emb


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return max(-1.0, min(1.0, dot / (na * nb)))


def _char_features(text: str) -> dict[str, int]:
    """字符 1/2-gram 计数 (与 LexicalEmbedder 特征空间一致)。"""
    t = re.sub(r"\s+", "", (text or "").lower())
    feats: dict[str, int] = {}
    for g in list(t) + [t[i:i + 2] for i in range(len(t) - 1)]:
        feats[g] = feats.get(g, 0) + 1
    return feats


def coverage(goal_text: str, text: str) -> float:
    """覆盖度: 步骤文本的语义字符特征有多大比例落在目标域内 (0~1)。

    用途: 短步骤 vs 长目标文档时, 余弦普遍偏低; 覆盖度按"步骤被目标包含"
    归一, 对齐步骤得分高、跑偏步骤得分低。
    """
    g, s = _char_features(goal_text), _char_features(text)
    if not s:
        return 0.0
    common = sum(min(v, g.get(k, 0)) for k, v in s.items())
    return common / sum(s.values())


def similarity(emb, goal_text: str, goal_vec: list[float], text: str) -> float:
    """统一相似度: BGE-m3 用原生余弦; lexical 降级后端
    取 max(余弦, 覆盖度) 并乘以标定系数(lexical_calibration, 默认1.28),
    使降级后端分数与方案 0.75 对齐阈值处于同一标尺 (标定推导见 config 注释)。
    """
    sim = cosine(goal_vec, emb.embed(text))
    if getattr(emb, "name", "") == "lexical":
        sim = max(sim, coverage(goal_text, text))
        sim = min(1.0, sim * float(getattr(emb, "calibration", 1.0)))
    return sim


# ---------------------------------------------------------------- 记录结构
@dataclass
class StepRecord:
    step: int
    ts: str
    similarity: float          # 与目标锚相似度
    distance: float            # 与目标锚语义距离 = 1 - sim
    drift: bool                # distance > 0.3
    below_align: bool          # sim < 0.75 (对齐预警)
    over_steps: bool           # step > 20
    text_sha: str
    events: list[str] = field(default_factory=list)


class SemanticMonitor:
    """实时语义漂移监测: 逐步向量 + 推理语义轨迹链 + 工具参数强校验。"""

    def __init__(self, goal: GoalAnchor, cfg: ThresholdConfig,
                 emit=None, embedder=None):
        self.goal = goal
        self.cfg = cfg
        self.emit = emit or (lambda *_a, **_k: None)
        self.embedder = embedder or make_embedder(cfg)
        self._goal_vec = self.embedder.embed(goal.text())
        self._steps: list[StepRecord] = []
        self._lock = threading.RLock()
        # 约束中的禁用词/数值范围 (供工具参数强校验)
        self._banned: list[str] = []
        self._ranges: list[tuple[str, float, float, str]] = []  # (字段, lo, hi, 原文)
        for c in goal.constraint_conditions:
            if any(k in c for k in ("禁止", "不得", "只能", "限")):
                self._banned.append(c)
            m = re.search(r"(?:不得超过|不超过|≤|<=)\s*([0-9.]+)", c)
            if m:
                self._ranges.append((c, -math.inf, float(m.group(1)), c))
            m2 = re.search(r"(?:至少|≥|>=)\s*([0-9.]+)", c)
            if m2:
                self._ranges.append((c, float(m2.group(1)), math.inf, c))

    # ---- 核心: 每轮推理前对齐校验 ----
    def similarity_to_goal(self, text: str) -> float:
        return similarity(self.embedder, self.goal.text(), self._goal_vec, text)

    def check(self, text: str) -> StepRecord:
        """单步校验: 记录轨迹 + 判定漂移/对齐/超步, 发出对应事件。"""
        sem = self.cfg.section("semantic")
        anch = self.cfg.section("anchor")
        with self._lock:
            step = len(self._steps) + 1
            sim = self.similarity_to_goal(text)
            dist = 1.0 - sim
            drift = dist > float(sem["drift_distance"])          # >0.3 判定漂移
            below = sim < float(anch["similarity_warn"])         # <0.75 一级预警
            over = step > int(sem["max_steps"])                  # >20步 预警
            rec = StepRecord(
                step=step, ts=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                similarity=round(sim, 4), distance=round(dist, 4),
                drift=drift, below_align=below, over_steps=over,
                text_sha=hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
            )
            if drift:
                rec.events.append("DRIFT")
                self.emit("L1", "semantic_drift",
                          {"distance": round(dist, 4), "threshold": sem["drift_distance"], "step": step})
            if below and not drift:
                rec.events.append("ALIGN_WARN")
                self.emit("L1", "align_below_warn",
                          {"similarity": round(sim, 4), "threshold": anch["similarity_warn"], "step": step})
            if over:
                rec.events.append("OVER_STEPS")
                self.emit("L1", "step_limit_exceeded",
                          {"step": step, "limit": sem["max_steps"]})
            self._steps.append(rec)
            return rec

    # ---- 推理语义轨迹链 ----
    def trajectory(self) -> list[dict]:
        with self._lock:
            return [r.__dict__ for r in self._steps]

    def stats(self) -> dict:
        with self._lock:
            if not self._steps:
                return {"steps": 0}
            sims = [r.similarity for r in self._steps]
            return {
                "steps": len(self._steps),
                "avg_similarity": round(sum(sims) / len(sims), 4),
                "min_similarity": round(min(sims), 4),
                "max_distance": round(max(r.distance for r in self._steps), 4),
                "drift_steps": sum(1 for r in self._steps if r.drift),
                "embedding_backend": getattr(self.embedder, "name", "unknown"),
                "degraded": bool(getattr(self.embedder, "degraded", False)),
            }

    # ---- 工具调用参数强校验 ----
    def validate_tool_params(self, params: dict) -> tuple[bool, str]:
        """入参/出参必须在目标约束范围内, 越界直接拦截 (返回 allow, reason)。"""
        for k, v in (params or {}).items():
            s = f"{k}={v}"
            for ban in self._banned:
                kw = re.sub(r"^(禁止|不得|只能|限)", "", ban).strip()
                if kw and kw in str(v):
                    return False, f"入参越界(违反禁用约束[{ban}]): {s}"
            if isinstance(v, (int, float)):
                for _, lo, hi, src in self._ranges:
                    field_key = str(k)
                    if field_key and (not (lo <= float(v) <= hi)):
                        return False, f"入参越界(违反约束[{src}]): {s}"
            if isinstance(v, str):
                for _, lo, hi, src in self._ranges:
                    m = re.fullmatch(r"\s*([0-9.]+)\s*", v)
                    if m and not (lo <= float(m.group(1)) <= hi):
                        return False, f"入参越界(违反约束[{src}]): {s}"
        return True, "ok"

    def validate_tool_result(self, result: str) -> tuple[bool, str]:
        """出参在目标约束范围内: 结果段落若完全脱离目标(相似度<0.5)按越界拦截。"""
        sim = self.similarity_to_goal(str(result))
        if sim < 0.5:
            return False, f"出参脱离目标约束范围(相似度{sim:.3f}<0.5)"
        return True, "ok"
