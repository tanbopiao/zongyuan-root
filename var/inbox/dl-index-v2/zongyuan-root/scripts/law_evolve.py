#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元法则进化真值管线（law_evolve）｜ META-EVOLUTION-001 执行器
锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
职责：每次实战产生的进化真值 → 记录 pending → 提炼法则草案 → schema 门 → 锁档固化
用法：
  law_evolve.py append '<真值描述>' [--source <事件/机制>]  记录进化真值
  law_evolve.py pending [--json]                            列出未提炼真值
  law_evolve.py draft <law_id> --name <名称> --level P0    生成法则草案骨架（含 clauses 占位）
  law_evolve.py check --dir <meta-rules目录>                运行 schema 门
  law_evolve.py review                                     总结：pending 数量 + 法则总数 + 缺口
"""
import argparse, datetime, json, os, subprocess, sys

ZR = "/home/user/ZONGYUAN-ROOT"
PENDING = os.path.join(ZR, "var", "law-evolution", "pending.jsonl")
META_RULES = os.path.join(ZR, "meta-rules")
AUDIT = "/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/var/audit/audit.jsonl"
SCHEMA_CHECK = "/home/user/.doubao/agent_mode/workspace/.user_skills/zongyuan-auto-lock/scripts/meta_law_schema_check.py"

def now(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def audit(detail):
    rec = {"ts": now(), "event": "kernel.truth", "actor": "operator", "action": "law-evolve", "result": "ok", "detail": detail}
    os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
    with open(AUDIT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def append(args):
    os.makedirs(os.path.dirname(PENDING), exist_ok=True)
    rec = {"ts": now(), "truth": args.truth, "source": args.source or "unknown", "status": "pending"}
    with open(PENDING, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    audit(f"进化真值记录：{args.truth[:60]}（来源 {rec['source']}）")
    print(f"APPENDED: {rec['ts']} ｜ {args.truth[:80]}")

def pending(args):
    if not os.path.exists(PENDING):
        print("pending: 无记录"); return
    rows = [json.loads(l) for l in open(PENDING, encoding="utf-8") if l.strip()]
    pend = [r for r in rows if r.get("status") == "pending"]
    if args.json:
        print(json.dumps(pend, ensure_ascii=False, indent=2)); return
    print(f"PENDING: {len(pend)} 条待提炼真值")
    for r in pend:
        print(f"  [{r['ts']}] {r['truth'][:70]}（{r.get('source','')}）")

def draft(args):
    os.makedirs(META_RULES, exist_ok=True)
    d = {"law_id": args.law_id, "name": args.name, "level": args.level or "P0",
         "description": "（草案：由进化真值提炼，待补充 clauses）",
         "clauses": [{"id": args.law_id.split("-")[-1] + "-1", "text": "（待提炼）"}],
         "anchor": "Ω₀⊂⊙∞⊂Ω", "DID": "DID-BR-000002"}
    p = os.path.join(META_RULES, args.law_id + ".json")
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"DRAFT: {p}（骨架已建，请补 clauses 后过 schema 门）")

def check(args):
    r = subprocess.run([sys.executable, SCHEMA_CHECK, "--dir", args.dir or META_RULES],
                       capture_output=True, text=True)
    print(r.stdout[-600:])
    return 0 if "SCHEMA_CHECK_EXIT: 0" in r.stdout else 1

def review(args):
    laws = [f for f in os.listdir(META_RULES) if f.endswith(".json")]
    pend_n = 0
    if os.path.exists(PENDING):
        pend_n = sum(1 for l in open(PENDING, encoding="utf-8") if l.strip() and json.loads(l).get("status") == "pending")
    print(f"REVIEW: 法则总数 {len(laws)} ｜ 待提炼真值 {pend_n} ｜ 目录 {META_RULES}")
    if pend_n > 0:
        print("缺口：存在未提炼真值，按 META-EVOLUTION-001 EV-5 应提炼为法则")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("append"); a.add_argument("truth"); a.add_argument("--source")
    b = sub.add_parser("pending"); b.add_argument("--json", action="store_true")
    c = sub.add_parser("draft"); c.add_argument("law_id"); c.add_argument("--name", required=True); c.add_argument("--level", default="P0")
    d = sub.add_parser("check"); d.add_argument("--dir")
    e = sub.add_parser("review")
    args = ap.parse_args()
    try:
        sys.exit({"append": append, "pending": pending, "draft": draft, "check": check, "review": review}[args.cmd](args))
    except KeyboardInterrupt:
        sys.exit(130)
