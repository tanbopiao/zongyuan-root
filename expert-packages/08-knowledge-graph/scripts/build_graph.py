#!/usr/bin/env python3
"""知识图谱构建与稳态锚定 v1.0 —— 三元组建图 / 实体归一 / 指标度量 / 图谱补全 / 九类归类 / 哈希快照。

纯 Python 标准库。一次跑完：
  triples.jsonl -> graph.json (节点/边) -> metrics + 孤立节点 + 补全候选 + 九类归类 + 版本快照

用法:
  python3 scripts/build_graph.py --triples <triples.jsonl> --dict <dict.json> --outdir <输出目录> [--did <DID>] [--prev-snapshot <上一快照.json>]
"""
import sys, json, hashlib, time, argparse
from pathlib import Path
from typing import List, Dict, Tuple

# 九大元类关键词词典（通用企业资产分类）
NINE_CLASSES = {
    "公理": ["必须", "一律", "不可", "原则", "第一性", "根本"],
    "定理": ["证明", "因此", "由此可得", "结论", "推导", "定律"],
    "方法": ["采用", "方法", "步骤", "流程", "方案", "策略", "实践"],
    "数据": ["数据", "指标", "统计", "报表", "数据集", "看板", "口径"],
    "案例": ["案例", "案例分析", "例如", "实例", "实践表明", "客户"],
    "决策": ["决定", "决策", "立项", "审批", "选择", "拍板", "批准"],
    "创意": ["创意", "灵感", "构想", "设想", "脑洞", "创新点"],
    "风险": ["风险", "隐患", "缺陷", "故障", "事故", "合规风险", "告警"],
    "协议": ["协议", "接口", "契约", "规范", "约定", "标准", "合同", "SLA"],
}


def node_id(name: str) -> str:
    return "N-" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]


def load_triples(path: Path) -> List[Dict]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_dict(path: Path) -> Dict:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    canon = {}
    for e in d.get("entities", []):
        canon[e["name"]] = {"type": e.get("type", "未分类"), "aliases": e.get("aliases", [])}
    return canon


def build_nodes_edges(triples: List[Dict], canon: Dict) -> Tuple[List[Dict], List[Dict]]:
    nodes: Dict[str, Dict] = {}
    edges: List[Dict] = []
    for t in triples:
        for role, ent in (("subject", t["subject"]), ("object", t["object"])):
            nid = node_id(ent)
            if nid not in nodes:
                meta = canon.get(ent, {"type": "未分类", "aliases": []})
                nodes[nid] = {
                    "id": nid, "name": ent, "type": meta["type"],
                    "aliases": meta["aliases"], "degree": 0, "sources": set(),
                }
            nodes[nid]["degree"] += 1
            for sf in t.get("source_files", []):
                nodes[nid]["sources"].add(sf)
        eid = "E-" + hashlib.sha256(
            (t["subject"] + t["predicate"] + t["object"]).encode("utf-8")).hexdigest()[:12]
        edges.append({
            "id": eid, "subject": node_id(t["subject"]), "subject_name": t["subject"],
            "predicate": t["predicate"], "object": node_id(t["object"]), "object_name": t["object"],
            "support": t.get("support", 1), "sources": t.get("source_files", []),
        })
    node_list = sorted(nodes.values(), key=lambda n: n["name"])
    for n in node_list:
        n["sources"] = sorted(n["sources"])
    return node_list, edges


def connected_components(nodes: List[Dict], edges: List[Dict]) -> int:
    adj: Dict[str, set] = {n["id"]: set() for n in nodes}
    for e in edges:
        adj.setdefault(e["subject"], set()).add(e["object"])
        adj.setdefault(e["object"], set()).add(e["subject"])
    seen = set()
    comps = 0
    for nid in adj:
        if nid in seen:
            continue
        comps += 1
        stack = [nid]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(adj.get(cur, ()))
    return comps


def graph_metrics(nodes: List[Dict], edges: List[Dict]) -> Dict:
    n = len(nodes)
    e = len(edges)
    max_edges = n * (n - 1) / 2 if n > 1 else 1
    isolated = [n["name"] for n in nodes if n["degree"] == 0]
    return {
        "node_count": n,
        "edge_count": e,
        "density": round(e / max_edges, 4),
        "connected_components": connected_components(nodes, edges),
        "isolated_nodes": isolated,
        "isolated_count": len(isolated),
    }


def complete_transitive(edges: List[Dict]) -> List[Dict]:
    """传递推理：同谓语链 A-p->B-p->C 推导 A-p->C 候选（仅作为提示，不直接入库）。"""
    by_pred: Dict[str, Dict[str, set]] = {}
    for ed in edges:
        by_pred.setdefault(ed["predicate"], {}).setdefault(ed["subject_name"], set()).add(ed["object_name"])
    candidates = []
    for pred, fwd in by_pred.items():
        for a, bs in fwd.items():
            for b in bs:
                for c in fwd.get(b, ()):
                    if c != a and c not in bs:
                        candidates.append({"subject": a, "predicate": pred, "object": c,
                                           "path": [a, b, c], "confidence": "low"})
    # 去重
    uniq = {(c["subject"], c["predicate"], c["object"]): c for c in candidates}
    return sorted(uniq.values(), key=lambda x: (x["subject"], x["predicate"]))


def classify_nodes(nodes: List[Dict], canon: Dict) -> List[Dict]:
    """九大元类归类：按节点名+类型命中关键词词典，输出归类与置信度。"""
    out = []
    for n in nodes:
        text = n["name"] + " " + n["type"]
        scores = {}
        for cls, kws in NINE_CLASSES.items():
            hit = sum(1 for kw in kws if kw in text)
            if hit:
                scores[cls] = hit
        if scores:
            best = max(scores, key=scores.get)
            conf = round(scores[best] / max(len(NINE_CLASSES[best]), 1), 2)
        else:
            best, conf = "未分类", 0.0
        out.append({"id": n["id"], "name": n["name"], "meta_class": best,
                    "confidence": conf, "score_detail": scores})
    return out


def snapshot_hash(graph: Dict) -> str:
    payload = json.dumps({"nodes": graph["nodes"], "edges": graph["edges"]},
                          ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main():
    ap = argparse.ArgumentParser(description="知识图谱构建与稳态锚定")
    ap.add_argument("--triples", required=True, help="extract_triples.py 产出的 triples.jsonl")
    ap.add_argument("--dict", required=True, help="实体词典 JSON")
    ap.add_argument("--outdir", required=True, help="产物输出目录")
    ap.add_argument("--did", default="<YOUR_DID>")
    ap.add_argument("--prev-snapshot", default="", help="上一版本快照 JSON（可选，用于版本升级判定）")
    args = ap.parse_args()

    triples = load_triples(Path(args.triples))
    canon = load_dict(Path(args.dict))
    nodes, edges = build_nodes_edges(triples, canon)

    # 提及侧车：把"被文档提及但未参与任何三元组"的实体补为孤立节点（degree=0）
    mention_sidecar = Path(args.triples).with_suffix(".mentions.json")
    if mention_sidecar.exists():
        mentioned = json.loads(mention_sidecar.read_text(encoding="utf-8"))
        existing = {n["name"] for n in nodes}
        for ent in sorted(mentioned):
            if ent not in existing:
                meta = canon.get(ent, {"type": "未分类", "aliases": []})
                nodes.append({"id": node_id(ent), "name": ent, "type": meta["type"],
                              "aliases": meta["aliases"], "degree": 0, "sources": []})
    metrics = graph_metrics(nodes, edges)
    completion = complete_transitive(edges)
    classified = classify_nodes(nodes, canon)

    graph = {
        "version": "1.0.0",
        "did": args.did,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "nodes": nodes,
        "edges": edges,
    }
    cur_hash = snapshot_hash(graph)

    version_bump = "initial"
    if args.prev_snapshot and Path(args.prev_snapshot).exists():
        prev = json.loads(Path(args.prev_snapshot).read_text(encoding="utf-8"))
        if prev.get("graph_hash") != cur_hash:
            old_ver = prev.get("version", "1.0.0")
            major, minor, patch = [int(x) for x in old_ver.split(".")]
            patch += 1
            graph["version"] = f"{major}.{minor}.{patch}"
            version_bump = f"{old_ver} -> {graph['version']}"
        else:
            graph["version"] = prev.get("version", "1.0.0")
            version_bump = "unchanged"

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=1), encoding="utf-8")

    report = {
        "status": "OK",
        "did": args.did,
        "graph_version": graph["version"],
        "version_bump": version_bump,
        "graph_hash": cur_hash,
        "metrics": metrics,
        "completion_candidates": completion,
        "classification": classified,
        "outdir": str(outdir),
    }
    (outdir / "graph-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    # 稳态锚定快照：只存哈希与版本，不存全量图（防无声漂移）
    snap = {
        "graph_hash": cur_hash,
        "version": graph["version"],
        "node_count": metrics["node_count"],
        "edge_count": metrics["edge_count"],
        "did": args.did,
        "ts": graph["ts"],
    }
    (outdir / "graph-snapshot.json").write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps({k: v for k, v in report.items() if k != "classification"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
