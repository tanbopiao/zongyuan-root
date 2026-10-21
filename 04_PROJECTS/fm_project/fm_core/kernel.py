#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FM-Core Phase1 最小内核 — 记忆原子 / 提案 / 共识打分 / 冲突检测 / 生命周期 / 审计账本。

诚实口径（不夸大）：
  · 存储为本地 SQLite（fm_data/fm_core.db），单进程单写者，非分布式；
  · 冲突检测是「词面规则」（归一化 + 字符 3-gram Jaccard），不是语义矛盾判定；
  · 共识打分为确定性投票比例规则，非拜占庭容错、无信誉/权重模型；
  · 审计账本为哈希链（append-only），非 WORM 存储；
  · 内核不感知 LLM/向量模型——语义能力全部由 fm_adapters 提供。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sqlite3
import threading
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

KERNEL_NAME = "fm-core"
KERNEL_VERSION = "1.0.0"
AXIOM = "Ω₀⊂⊙∞⊂Ω"

# ---------- 生命周期阈值 ----------
CONF_SIM_TH = 0.75    # 字符 3-gram Jaccard ≥ 此值且非同文 → 冲突候选
CONF_CONTAIN_TH = 0.35  # 覆盖率（双向取小）≥ 此值 且含否定词 → 冲突候选
                         # 实测锚点：否定种子 0.40（应抓）/ 一致复述 0.333（应放）
NEG_MARKERS = "不非没无否未"  # 词面否定标记
VOTE_PASS_TH = 0.60   # 赞同比例 ≥ 此值 → 归档
VOTE_DROP_TH = 0.40   # 赞同比例 ≤ 此值 → 软遗忘（非删除）
MIN_VOTES = 2         # 达到此票数才做归档/否决裁决
SCORE_SEED = 1.00
SCORE_PROPOSED = 0.50
RETRIEVABLE = ("seed", "archived", "proposed")  # 可被检索的状态
IMMUTABLE = ("seed", "archived")                # 内容不可再改的状态

SCHEMA = """
CREATE TABLE IF NOT EXISTS atoms(
    mid         TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    norm        TEXT NOT NULL,
    source      TEXT,
    source_type TEXT,
    tags        TEXT NOT NULL DEFAULT '[]',
    status      TEXT NOT NULL,
    score       REAL NOT NULL DEFAULT 0,
    agree       INTEGER NOT NULL DEFAULT 0,
    total_votes INTEGER NOT NULL DEFAULT 0,
    conflict_with TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_atoms_status ON atoms(status);
CREATE TABLE IF NOT EXISTS audit(
    seq       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,
    action    TEXT NOT NULL,
    mid       TEXT,
    detail    TEXT NOT NULL DEFAULT '{}',
    prev_hash TEXT NOT NULL,
    hash      TEXT NOT NULL
);
"""


def normalize(text: str) -> str:
    """归一化：NFKC → 小写 → 去标点/空白，用于同原子判定。"""
    s = unicodedata.normalize("NFKC", str(text)).lower()
    s = re.sub(r"[\s\W_]+", "", s, flags=re.UNICODE)
    return s


def grams(text: str, n: int = 3) -> set:
    s = normalize(text)
    if len(s) < n:
        return {s} if s else set()
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def similarity(a: str, b: str) -> float:
    """字符 3-gram Jaccard 相似度（词面规则，非语义判定）。"""
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 1.0 if normalize(a) == normalize(b) else 0.0
    return len(ga & gb) / len(ga | gb)


def containment(a: str, b: str) -> float:
    """覆盖率 = 双向「交集占各自比例」的较小值，识别短句被长句覆盖的情形。"""
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    inter = len(ga & gb)
    return min(inter / len(ga), inter / len(gb))


def now_iso() -> str:
    s = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    return s


def make_mid(norm: str) -> str:
    """同内容 → 同原子（内容寻址，天然去重）。"""
    return "mem_" + hashlib.sha256(norm.encode("utf-8")).hexdigest()[:32]


class MemoryKernel:
    """Phase1 最小内核：提案 → 共识 → 归档/软遗忘，全链审计。"""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # ---------- 审计账本（哈希链） ----------
    def _audit(self, action: str, mid: Optional[str], detail: Dict) -> str:
        cur = self._conn.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1")
        row = cur.fetchone()
        prev = row["hash"] if row else "0" * 64
        ts = now_iso()
        seq = (self._conn.execute("SELECT COUNT(*) c FROM audit").fetchone()["c"]) + 1
        base = json.dumps({"seq": seq, "ts": ts, "action": action, "mid": mid,
                           "detail": detail, "prev": prev}, sort_keys=True, ensure_ascii=False)
        h = hashlib.sha256(base.encode("utf-8")).hexdigest()
        self._conn.execute(
            "INSERT INTO audit(ts,action,mid,detail,prev_hash,hash) VALUES(?,?,?,?,?,?)",
            (ts, action, mid, json.dumps(detail, ensure_ascii=False), prev, h))
        return h

    # ---------- 冲突检测（词面规则） ----------
    def _find_conflicts(self, mid: str, content: str) -> List[str]:
        """两条规则（均不依赖模型，保持内核模型无关）：
        1) 近同文：Jaccard ≥ CONF_SIM_TH —— 改写/标点变体；
        2) 否定式：被已有原子高覆盖 且 自身含否定词 —— 否定句的 Jaccard
           恒偏低（实测「否定种子」仅约 0.26），必须用覆盖率才能捕获，
           否则种子的反面可静默进池、再投票归档，破坏种子唯一性。
        结果一律进 conflict 复核态（不自动否决、不静默覆盖）。
        """
        neg = any(m in normalize(content) for m in NEG_MARKERS)
        hits = []
        for row in self._conn.execute(
                "SELECT mid, content FROM atoms WHERE status IN (?,?,?) LIMIT 500",
                RETRIEVABLE):
            if row["mid"] == mid:
                continue
            if similarity(content, row["content"]) >= CONF_SIM_TH:
                hits.append(row["mid"])
                continue
            if neg and containment(content, row["content"]) >= CONF_CONTAIN_TH:
                hits.append(row["mid"])
        return hits

    # ---------- 写入 ----------
    def add_seed(self, content: str, tags: Optional[List[str]] = None) -> Dict:
        """种子真值：不可变更的可信基线。"""
        with self._lock:
            return self._write(content, tags, source="seed", source_type="seed", status="seed")

    def propose(self, content: str, source: Optional[str] = None,
                source_type: str = "llm_extract", tags: Optional[List[str]] = None) -> Dict:
        """提案：先进 proposed，经投票共识后归档。"""
        with self._lock:
            return self._write(content, tags, source=source or "unknown",
                               source_type=source_type, status="proposed")

    def _write(self, content, tags, source, source_type, status) -> Dict:
        content = (content or "").strip()
        if not content:
            return {"ok": False, "error": "empty content"}
        norm = normalize(content)
        mid = make_mid(norm)
        exist = self._conn.execute("SELECT mid,status FROM atoms WHERE mid=?", (mid,)).fetchone()
        if exist:
            self._audit("atom.duplicate", mid, {"first_seen_status": exist["status"],
                                                 "source": source})
            self._conn.commit()
            return {"ok": True, "mid": mid, "status": exist["status"], "duplicate": True}

        conflicts = self._find_conflicts(mid, content)
        final = "conflict" if conflicts else status
        ts = now_iso()
        score = SCORE_SEED if final == "seed" else SCORE_PROPOSED
        self._conn.execute(
            "INSERT INTO atoms(mid,content,norm,source,source_type,tags,status,score,"
            "conflict_with,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (mid, content, norm, source, source_type,
             json.dumps(tags or [], ensure_ascii=False), final, score,
             json.dumps(conflicts, ensure_ascii=False), ts, ts))
        self._audit("atom.conflict" if conflicts else
                    ("seed.add" if final == "seed" else "atom.propose"),
                    mid, {"source": source, "source_type": source_type,
                          "conflict_with": conflicts})
        self._conn.commit()
        return {"ok": True, "mid": mid, "status": final, "duplicate": False,
                "conflict_with": conflicts}

    # ---------- 共识投票 ----------
    def vote(self, mid: str, agree: bool, voter: str = "anonymous") -> Dict:
        with self._lock:
            row = self._conn.execute("SELECT * FROM atoms WHERE mid=?", (mid,)).fetchone()
            if row is None:
                return {"ok": False, "error": "mid not found", "mid": mid}
            if row["status"] in IMMUTABLE:
                return {"ok": False, "error": f"{row['status']} 为不可变更状态", "mid": mid,
                        "status": row["status"]}
            agree_n = row["agree"] + (1 if agree else 0)
            total_n = row["total_votes"] + 1
            ratio = agree_n / total_n if total_n else 0.0
            status, score, event = row["status"], row["score"], None
            if total_n >= MIN_VOTES:
                if ratio >= VOTE_PASS_TH:
                    status, score, event = "archived", 0.5 + 0.5 * ratio, "lifecycle.archived"
                elif ratio <= VOTE_DROP_TH:
                    status, score, event = "soft_forget", row["score"] * 0.5, "lifecycle.soft_forget"
            self._conn.execute(
                "UPDATE atoms SET agree=?, total_votes=?, status=?, score=?, updated_at=? WHERE mid=?",
                (agree_n, total_n, status, score, now_iso(), mid))
            detail = {"voter": voter, "agree": bool(agree), "ratio": round(ratio, 4),
                      "votes": total_n, "status": status, "score": round(score, 4)}
            self._audit("vote", mid, detail)
            if event:
                self._audit(event, mid, detail)
            self._conn.commit()
            return {"ok": True, "mid": mid, "status": status, "score": round(score, 4),
                    "ratio": round(ratio, 4), "votes": total_n}

    # ---------- 读取 ----------
    def retrieve(self, topk: int = 3) -> List[Dict]:
        """按分数降序返回可检索原子：种子真值优先，其次归档，再后提案。"""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM atoms WHERE status IN (?,?,?) "
                "ORDER BY CASE status WHEN 'seed' THEN 0 WHEN 'archived' THEN 1 ELSE 2 END,"
                " score DESC, updated_at DESC LIMIT ?",
                (*RETRIEVABLE, int(topk))).fetchall()
            return [self._row(r) for r in rows]

    def list_atoms(self, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        with self._lock:
            if status:
                rows = self._conn.execute(
                    "SELECT * FROM atoms WHERE status=? ORDER BY updated_at DESC LIMIT ?",
                    (status, int(limit))).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM atoms ORDER BY updated_at DESC LIMIT ?",
                    (int(limit),)).fetchall()
            return [self._row(r) for r in rows]

    def audit_log(self, limit: int = 50) -> List[Dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM audit ORDER BY seq DESC LIMIT ?", (int(limit),)).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["detail"] = json.loads(d["detail"])
                out.append(d)
            return out

    def verify_chain(self) -> Dict:
        """校验审计哈希链完整性。"""
        with self._lock:
            rows = self._conn.execute("SELECT * FROM audit ORDER BY seq ASC").fetchall()
        prev = "0" * 64
        broken = []
        for r in rows:
            if r["prev_hash"] != prev:
                broken.append({"seq": r["seq"], "reason": "prev mismatch"})
            base = json.dumps({"seq": r["seq"], "ts": r["ts"], "action": r["action"],
                               "mid": r["mid"], "detail": json.loads(r["detail"]),
                               "prev": r["prev_hash"]}, sort_keys=True, ensure_ascii=False)
            if hashlib.sha256(base.encode("utf-8")).hexdigest() != r["hash"]:
                broken.append({"seq": r["seq"], "reason": "hash mismatch"})
            prev = r["hash"]
        return {"entries": len(rows), "valid": not broken, "broken": broken}

    def health(self) -> Dict:
        with self._lock:
            counts = {r["status"]: r["c"] for r in self._conn.execute(
                "SELECT status, COUNT(*) c FROM atoms GROUP BY status")}
            n_audit = self._conn.execute("SELECT COUNT(*) c FROM audit").fetchone()["c"]
        return {"status": "ok", "kernel": KERNEL_NAME, "version": KERNEL_VERSION,
                "axiom": AXIOM, "atoms": counts, "atom_total": sum(counts.values()),
                "audit_entries": n_audit, "db": self.db_path}

    # ---------- 工具 ----------
    @staticmethod
    def _row(r: sqlite3.Row) -> Dict:
        return {"mid": r["mid"], "content": r["content"], "source": r["source"],
                "source_type": r["source_type"], "tags": json.loads(r["tags"]),
                "status": r["status"], "score": round(r["score"], 4),
                "votes": r["total_votes"], "agree": r["agree"],
                "conflict_with": json.loads(r["conflict_with"]),
                "created_at": r["created_at"], "updated_at": r["updated_at"]}

    def close(self):
        with self._lock:
            self._conn.close()


__all__ = ["MemoryKernel", "KERNEL_NAME", "KERNEL_VERSION", "AXIOM",
           "normalize", "similarity", "make_mid"]
