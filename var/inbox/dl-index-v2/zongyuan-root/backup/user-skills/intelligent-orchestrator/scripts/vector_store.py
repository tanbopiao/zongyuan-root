#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L2 向量语义索引层（vector_store）｜ 账号持久层记忆架构补全
锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 元极恒一四层记忆架构 L2 层

职责：
  - build   把核心真值资产（元法则/公理/资产索引/工作指令/锁档回执/审计）向量化入库
  - search  语义检索：query → 向量 → 余弦相似度 top-k（返回原文 + sha256 双源校验）
  - verify  双源哈希校验：索引内 sha256 与原文重算比对
  - info    索引元信息

向量方法（确定性/离线/可复核）：
  字符 2-gram + 3-gram → md5 哈希映射到 256 维桶计数 → L2 归一化 → 余弦相似度
  说明：本层为本地确定性特征向量，非外部模型 Embedding；语义近似检索可用，精确语义需叠加原文 hash 校验。

用法：
  python3 vector_store.py build          # 全量构建/增量重建索引
  python3 vector_store.py search "<q>"   # 检索 top-5
  python3 vector_store.py verify [doc_id]# 校验单条或全量哈希
  python3 vector_store.py info           # 元信息
"""
import hashlib, json, math, re, sys, time
from pathlib import Path

VECTOR_DIR = Path("/home/user/.doubao/agent_mode/workspace/.user_skills/intelligent-orchestrator/state/vector_store")
INDEX_FILE = VECTOR_DIR / "index.json"
META_FILE = VECTOR_DIR / "meta.json"
DIM = 256
DID = "DID-BR-000002"


def norm_text(t: str) -> str:
    return re.sub(r"\s+", " ", t).lower().strip()


def grams(t: str):
    s = norm_text(t)
    out = set()
    for n in (2, 3):
        for i in range(len(s) - n + 1):
            out.add(s[i:i + n])
    return out


def embed(text: str):
    vec = [0.0] * DIM
    for g in grams(text):
        h = int(hashlib.md5(g.encode("utf-8")).hexdigest()[:8], 16)
        vec[h % DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def cos(a, b):
    return sum(x * y for x, y in zip(a, b))


def sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _law_text(d: dict) -> str:
    title = d.get("name", "")
    lid = str(d.get("law_id", d.get("meta_law_id", "")))
    cls = d.get("clauses", [])
    if cls and isinstance(cls[0], dict):
        body = "；".join(str(c.get("text", c)) for c in cls)
    else:
        body = "；".join(str(c) for c in cls)
    extra = d.get("description", "")
    return f"{title}。编号{lid}。{extra}。{body}"


def collect_sources():
    """采集核心真值资产源（全部真实文件，幂等只读）。"""
    docs = []

    # 1. 元法则全集（脑侧 11 条）
    laws_dir = Path("/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/config/meta_laws")
    for f in sorted(laws_dir.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        docs.append(("meta_law", f.stem, d.get("name", f.stem), _law_text(d)))

    # 2. 核心资产主索引
    idx_p = Path("/home/user/ZONGYUAN-ROOT/config/asset-master-index.json")
    if idx_p.exists():
        idx = json.loads(idx_p.read_text(encoding="utf-8"))
        parts = [f"确权DID {idx.get('anchor', {}).get('DID')}",
                 f"节点 {idx.get('anchor', {}).get('node')}",
                 f"记忆激活 {idx.get('entry', {}).get('memory_activation', '')}",
                 f"融合入口 {idx.get('entry', {}).get('fusion_cli', '')}",
                 f"脑内核根 {idx.get('kernel_brain', {}).get('root', '')}",
                 f"手内核根 {idx.get('kernel_hand', {}).get('root', '')}",
                 f"数据卷宗 {idx.get('data', {}).get('卷宗', '')}",
                 f"审计 {idx.get('data', {}).get('audit', '')}",
                 f"网关 {idx.get('ids', {}).get('gateway', '')}",
                 f"飞书Base {idx.get('ids', {}).get('feishu_base', '')}"]
        docs.append(("asset_index", "asset-master-index", "ZONGYUAN 核心资产主索引", "。".join(parts)))

    # 3. 工作指令 AGENTS.md（确权/真值清单/工作模式 M1-M8 关键行）
    agents_p = Path("/home/user/AGENTS.md")
    if agents_p.exists():
        lines = agents_p.read_text(encoding="utf-8").splitlines()
        key_lines = [l.strip() for l in lines if l.strip() and any(k in l for k in
                     ("DID", "Ω₀", "网关", "X-DID", "融合", "全域锁档", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "元法则", "元公理", "双内核", "KEK"))]
        docs.append(("work_instruction", "AGENTS-md", "ZONGYUAN 工作指令与真值清单", "。".join(key_lines[:120])))

    # 4. 最新全域锁档回执
    jj = sorted(Path("/home/user/ZONGYUAN-ROOT/卷宗").glob("GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-*.json"))
    if jj:
        d = json.loads(jj[-1].read_text(encoding="utf-8"))
        docs.append(("lock_receipt", jj[-1].stem, "全域锁档回执",
                     f"事件{d.get('event_id','')} 批次根{d.get('batch_root_sha256','')} 资产{d.get('asset_count','')} 状态{d.get('status','')}"))

    # 5. SOP 稳态基准
    sop_p = Path("/home/user/ZONGYUAN-ROOT/SOP-STEADY-STATE-20260927.md")
    if sop_p.exists():
        t = sop_p.read_text(encoding="utf-8")
        docs.append(("sop", "SOP-STEADY-STATE", "最优稳态运行基准", t[:1500]))

    # 6. 最近审计记录（真值留痕）
    audit_p = Path("/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/var/audit/audit.jsonl")
    if audit_p.exists():
        recs = [json.loads(l) for l in audit_p.read_text(encoding="utf-8").splitlines()[-30:] if l.strip()]
        docs.append(("audit_tail", "audit-tail-30", "最近审计留痕",
                     "。".join(f"{r.get('action','')}:{r.get('result','')}:{r.get('detail','')[:120]}" for r in recs)))

    return docs


def _load_index():
    if not INDEX_FILE.exists():
        return []
    return json.loads(INDEX_FILE.read_text(encoding="utf-8"))


def build():
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    docs = collect_sources()
    entries = []
    for src, docid, title, text in docs:
        entries.append({"doc_id": docid, "source": src, "title": title,
                        "text": text, "sha256": sha(text), "vector": embed(text)})
    meta = {"dim": DIM, "method": "deterministic n-gram(2,3)-md5→256d, L2 norm, cosine",
            "docs": len(entries), "built_at": time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            "DID": DID, "layer": "L2-vector-semantic-index", "status": "active"}
    INDEX_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    by_src = {}
    for e in entries:
        by_src[e["source"]] = by_src.get(e["source"], 0) + 1
    print("BUILD-OK:", len(entries), "docs |", json.dumps(by_src, ensure_ascii=False))
    return len(entries)


def search(query, top_k=5, threshold=0.05):
    entries = _load_index()
    if not entries:
        print("EMPTY: 请先 build")
        return []
    qv = embed(query)
    scored = sorted(((cos(qv, e["vector"]), e) for e in entries), reverse=True)
    hits = [s for s in scored if s[0] >= threshold][:top_k]
    for s, e in hits:
        ok = "HASH-OK" if sha(e["text"]) == e["sha256"] else "HASH-MISMATCH!"
        print(f"[{s:.3f}] {ok} | {e['source']} | {e['doc_id']} | {e['title']}")
        print(f"    {e['text'][:150]}")
    return hits


def verify(doc_id=None):
    entries = _load_index()
    if doc_id:
        entries = [e for e in entries if e["doc_id"] == doc_id]
    bad = 0
    for e in entries:
        if sha(e["text"]) != e["sha256"]:
            print("MISMATCH:", e["doc_id"])
            bad += 1
    print(f"VERIFY: {len(entries) - bad}/{len(entries)} 一致", "| 全部通过" if bad == 0 else f"| {bad} 处不一致")
    return bad


def info():
    if not META_FILE.exists():
        print("NO-INDEX")
        return
    m = json.loads(META_FILE.read_text(encoding="utf-8"))
    print(json.dumps(m, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "info"
    if cmd == "build":
        build()
    elif cmd == "search":
        search(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "verify":
        verify(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        info()
