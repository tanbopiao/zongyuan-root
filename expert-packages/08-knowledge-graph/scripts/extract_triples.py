#!/usr/bin/env python3
"""知识图谱三元组抽取 v1.0 —— 从 txt/md 非结构化文本抽取 (实体, 关系, 实体) 三元组。

基于规则词典 + 正则模式，纯 Python 标准库，零模型依赖。
支持自定义实体类型词典与自定义关系正则模式；同一实体的别名/缩写统一归一到规范名。

用法:
  python3 scripts/extract_triples.py --docs <目录或文件> --dict <dict.json> --out <triples.jsonl> [--did <DID>]
"""
import os, sys, json, re, time, hashlib, argparse
from pathlib import Path
from typing import List, Dict, Tuple

# 内置兜底关系模式：(正则, 归一化谓语)。捕获组1=主体, 捕获组2=客体。
BUILTIN_PATTERNS = [
    (r"([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{2,30}?)(隶属于|属于|归属|总部位于)([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{2,30}?)[。，,；;：:]", "隶属于"),
    (r"([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{2,30}?)(开发了|研发了|出品了|生产了)([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{2,30}?)[。，,；;：:]", "开发"),
    (r"([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{2,30}?)(的)([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{2,30}?)(是|为)([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{2,30}?)[。，,；;：:]", "属性"),
    (r"([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{2,30}?)(合作|与|联手)([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{2,30}?)(共同|联合)?", "合作"),
]

DOC_EXTS = {".txt", ".md", ".markdown"}


def load_dict(path: Path) -> Dict:
    """加载实体词典。结构: {entities:[{name,type,aliases[]}], relation_patterns:[[regex,pred],...] or {regex,pred}[]}"""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    entities = d.get("entities", [])
    alias2canon = {}
    canon2type = {}
    for e in entities:
        canon = e["name"]
        canon2type[canon] = e.get("type", "未分类")
        alias2canon[canon] = canon
        for a in e.get("aliases", []):
            alias2canon[a] = canon
    patterns = []
    for p in d.get("relation_patterns", []):
        if isinstance(p, dict):
            patterns.append((p["regex"], p["predicate"]))
        else:
            patterns.append((p[0], p[1]))
    if not patterns:
        patterns = BUILTIN_PATTERNS
    return {"alias2canon": alias2canon, "canon2type": canon2type, "patterns": patterns}


def find_mentions(text: str, alias2canon: Dict[str, str]) -> Dict[str, int]:
    """扫描文本中出现的实体别名/规范名，返回 {canonical: 出现次数}"""
    counts: Dict[str, int] = {}
    # 按别名长度降序，避免短别名先命中遮蔽长名
    for alias in sorted(alias2canon, key=len, reverse=True):
        if not alias:
            continue
        n = text.count(alias)
        if n > 0:
            canon = alias2canon[alias]
            counts[canon] = counts.get(canon, 0) + n
    return counts


def resolve_entity(raw: str, alias2canon: Dict[str, str]) -> str:
    """把正则捕获到的原始短语归一到规范名：先精确命中，再取短语内最长别名子串命中。"""
    raw = raw.strip()
    if raw in alias2canon:
        return alias2canon[raw]
    best = ""
    for alias in alias2canon:
        if alias and alias in raw and len(alias) > len(best):
            best = alias
    return alias2canon.get(best, "")


def extract_triples(text: str, fname: str, kb: Dict) -> List[Dict]:
    """按正则模式在句级切片中抽取三元组；两端必须命中已知实体词典才收录。"""
    triples = []
    seen = set()
    for regex, pred in kb["patterns"]:
        try:
            rx = re.compile(regex)
        except re.error:
            continue
        for m in rx.finditer(text):
            groups = [g for g in m.groups() if g]
            if pred == "属性" and len(groups) >= 4:
                subj_raw, attr, obj_raw = groups[0], groups[2], groups[3]
                pred_norm = f"属性:{attr.strip()}"
            elif pred == "负责":
                subj_raw, obj_raw = groups[0], groups[2]
                pred_norm = pred
            elif pred == "合作":
                subj_raw, obj_raw = groups[0], groups[1] if len(groups) > 1 else ""
                pred_norm = pred
            else:
                subj_raw, obj_raw = groups[0], groups[-1]
                pred_norm = pred
            if not subj_raw or not obj_raw:
                continue
            subj = resolve_entity(subj_raw, kb["alias2canon"])
            obj = resolve_entity(obj_raw, kb["alias2canon"])
            if not subj or not obj or subj == obj:
                continue
            key = (subj, pred_norm, obj)
            if key in seen:
                continue
            seen.add(key)
            triples.append({
                "subject": subj,
                "predicate": pred_norm,
                "object": obj,
                "subj_type": kb["canon2type"].get(subj, "未分类"),
                "obj_type": kb["canon2type"].get(obj, "未分类"),
                "source_file": fname,
                "evidence": m.group(0).strip()[:120],
            })
    return triples


def iter_docs(target: Path):
    if target.is_file():
        yield target
    else:
        for root, _, files in os.walk(target):
            for fn in sorted(files):
                if Path(fn).suffix.lower() in DOC_EXTS:
                    yield Path(root) / fn


def main():
    ap = argparse.ArgumentParser(description="从非结构化文本抽取知识图谱三元组")
    ap.add_argument("--docs", required=True, help="文档目录或单个 .txt/.md 文件")
    ap.add_argument("--dict", required=True, help="实体与关系词典 JSON 路径")
    ap.add_argument("--out", required=True, help="输出 triples.jsonl 路径")
    ap.add_argument("--did", default="<YOUR_DID>")
    args = ap.parse_args()

    target = Path(args.docs)
    if not target.exists():
        print(json.dumps({"status": "ERROR", "reason": "docs not found", "path": str(target)}, ensure_ascii=False))
        return 2
    kb = load_dict(Path(args.dict))

    all_triples: List[Dict] = []
    doc_stats = []
    mention_total: Dict[str, int] = {}
    for dp in iter_docs(target):
        text = dp.read_text(encoding="utf-8", errors="ignore")
        mentions = find_mentions(text, kb["alias2canon"])
        for canon, n in mentions.items():
            mention_total[canon] = mention_total.get(canon, 0) + n
        tris = extract_triples(text, dp.name, kb)
        all_triples.extend(tris)
        doc_stats.append({"file": dp.name, "chars": len(text), "entities_mentioned": len(mentions), "triples": len(tris)})

    # 跨文件去重（同 主体/谓语/客体 合并 source_file 列表）
    merged: Dict[Tuple, Dict] = {}
    for t in all_triples:
        k = (t["subject"], t["predicate"], t["object"])
        if k not in merged:
            merged[k] = {**t, "source_files": [t.pop("source_file")], "support": 1}
        else:
            merged[k]["support"] += 1
            if t["source_file"] not in merged[k]["source_files"]:
                merged[k]["source_files"].append(t["source_file"])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for t in sorted(merged.values(), key=lambda x: (x["subject"], x["predicate"], x["object"])):
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    summary = {
        "status": "OK",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "did": args.did,
        "docs_scanned": len(doc_stats),
        "known_entities": len(kb["alias2canon"]),
        "entities_mentioned": len(mention_total),
        "triples_extracted": len(merged),
        "doc_stats": doc_stats,
        "out": str(out_path),
    }
    # 提及侧车：供建图阶段发现"被提及但未入边"的孤立节点
    sidecar = out_path.with_suffix(".mentions.json")
    sidecar.write_text(json.dumps(mention_total, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
