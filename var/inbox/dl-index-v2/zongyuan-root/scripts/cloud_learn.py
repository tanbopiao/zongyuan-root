#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端→本地学习拉取执行器（META-CLOUD-LEARN-001）
用法:
  python3 cloud_learn.py --pull      # 拉取云端高价值表（真值共识区全量分页）
  python3 cloud_learn.py --clean     # 清洗：共识过滤+去重+领域归类+价值评分
  python3 cloud_learn.py --apply     # 提炼应用：经验候选+学习报告+上报+审计
  python3 cloud_learn.py --all       # 一键全流程
来源: 共享大脑真值共识区 tbl9QxL35rwA16eS（已达成共识仅采纳）
"""
import json, os, sys, io, subprocess, datetime, re

ZR = "/home/user/ZONGYUAN-ROOT"
CL = f"{ZR}/var/cloud-learn"
LEDGER = f"{CL}/learn-ledger.jsonl"
BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
TABLE = "tbl9QxL35rwA16eS"  # 真值共识区
HIGH_SIGNS = ["断点", "根因", "修复", "共识", "教训", "禁止", "必须", "只读", "锁档", "上报", "仲裁", "调度", "审批", "指纹"]

def ts_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")

def lark(args):
    r = subprocess.run(["lark-cli", "base"] + args, capture_output=True, text=True, timeout=180)
    return r.returncode == 0, r.stdout

def parse_records(out):
    rows, cur, header = [], [], None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("| _record_id"):
            header = [c.strip() for c in s.strip("|").split("|")][1:]
        elif s.startswith("| rec") and header:
            vals = [c.strip() for c in s.strip("|").split("|")][1:]
            rows.append(dict(zip(header, vals)))
    return rows

def pull():
    os.makedirs(CL, exist_ok=True)
    all_rows, offset = [], 0
    while True:
        ok, out = lark(["+record-list", "--base-token", BASE_TOKEN, "--table-id", TABLE,
                        "--limit", "200", "--offset", str(offset), "--format", "json", "--as", "user"])
        if not ok:
            print(f"[拉取] 失败 offset={offset}: {out[:150]}"); break
        try:
            d = json.loads(out)
        except Exception:
            print("[拉取] 非JSON输出，改用表格解析"); break
        rows = d.get("data", {}).get("data", [])
        fields = d.get("data", {}).get("fields", [])
        for row in rows:
            rec = {}
            for j, fname in enumerate(fields):
                if j < len(row):
                    v = row[j]
                    if isinstance(v, list):
                        v = "、".join(str(x) for x in v)
                    rec[fname] = str(v if v is not None else "")
            all_rows.append(rec)
        has_more = d.get("data", {}).get("has_more", False)
        offset += len(rows)
        if not has_more or not rows:
            break
    ts = ts_now()
    with io.open(f"{CL}/truth-{ts}.json", "w", encoding="utf-8") as f:
        json.dump({"ts": ts, "source": "真值共识区", "total": len(all_rows), "rows": all_rows}, f, ensure_ascii=False, indent=2)
    print(f"[拉取] 真值共识区 {len(all_rows)} 条 → var/cloud-learn/truth-{ts}.json")
    return ts

def clean(ts):
    data = json.load(io.open(f"{CL}/truth-{ts}.json", encoding="utf-8"))
    learned = set()
    if os.path.exists(LEDGER):
        for line in io.open(LEDGER, encoding="utf-8"):
            line = line.strip()
            if line:
                try: learned.add(json.loads(line).get("key"))
                except Exception: pass
    items = []
    for r in data["rows"]:
        key = r.get("真值key", "") or r.get("key", "")
        st = r.get("最终状态", "") or r.get("最终状态_select", "")
        content = r.get("真值内容", "") or r.get("content", "")
        if key in learned:
            continue
        if st and "已达成共识" not in st and "已吸收" not in st:
            continue  # 争议/待确认不采纳
        score = 60
        for s in HIGH_SIGNS:
            if s in content:
                score = min(95, score + 8)
        domain = "通用"
        for dname, dsig in [("调度", "调度|cron|任务|定时"), ("锁档", "锁档|只读|快照|归档"),
                            ("上报", "上报|网关|truth|上报器"), ("治理", "仲裁|审批|冲突|评级|指纹"),
                            ("进化", "进化|法则|经验|提炼|学习"), ("链路", "握手|心跳|断点|worker|消费")]:
            if re.search(dsig, content):
                domain = dname; break
        items.append({"key": key, "state": st, "domain": domain, "score": score,
                      "content": content[:220], "node": r.get("确认节点", ""), "learned": False})
    items.sort(key=lambda x: -x["score"])
    out = {"ts": ts, "cleaned_at": ts_now(), "raw": data["total"], "learned_before": len(learned),
           "candidates": items}
    with io.open(f"{CL}/cleaned-{ts}.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[清洗] 原始{data['total']} → 候选 {len(items)}（去重{len(learned)}已学/过滤非共识）")
    print(f"[评分] 高分(≥84): {sum(1 for i in items if i['score']>=84)} ｜ 中分(70-83): {sum(1 for i in items if 70<=i['score']<84)}")
    return items

def apply(ts):
    data = json.load(io.open(f"{CL}/cleaned-{ts}.json", encoding="utf-8"))
    items = data["candidates"]
    if not items:
        print("[应用] 无候选，跳过"); return
    top = items[:5]
    learned_records = []
    for i in top:
        learned_records.append({"key": i["key"], "domain": i["domain"], "score": i["score"],
                                "learned_at": ts_now(), "source": "cloud-truth-consensus",
                                "essence": i["content"][:160]})
        with io.open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(learned_records[-1], ensure_ascii=False) + "\n")
    # 经验候选（提炼为本地进化增量）
    exp = {"id": f"EXP-CLOUD-20260929-001", "ts": ts_now(), "source": "云端学习拉取·真值共识区",
           "learned": len(top), "lessons": [f"[{i['domain']}/{i['score']}] {i['content'][:80]}" for i in top[:5]]}
    with io.open(f"{ZR}/var/experience/EXP-CLOUD-20260929-001.json", "w", encoding="utf-8") as f:
        json.dump(exp, f, ensure_ascii=False, indent=2)
    report = {"ts": ts, "report_ts": ts_now(), "rule": "META-CLOUD-LEARN-001",
              "learned": len(top), "candidates_total": len(items), "report": learned_records}
    with io.open(f"{CL}/learned-{ts}.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    # 上报
    value = {"event": "cloud_learn", "rule": "META-CLOUD-LEARN-001", "learned": len(top),
             "total_candidates": len(items), "top": [i["key"] for i in top]}
    r = subprocess.run(["python3", f"{ZR}/scripts/gateway_report.py", f"cloud.learn.{ts}",
                        json.dumps(value, ensure_ascii=False)], capture_output=True, text=True, timeout=60)
    print(f"[应用] 提炼 {len(top)} 条为本地学习增量（TOP5 高分）→ EXP-CLOUD-20260929-001 + ledger")
    for i in top:
        print(f"  [{i['domain']}/{i['score']}] {i['key']}")
    print(f"[上报] {(r.stdout+r.stderr).strip()[-100:]}")
    return report

if __name__ == "__main__":
    if "--all" in sys.argv or "--pull" in sys.argv:
        ts = pull()
    if "--all" in sys.argv or "--clean" in sys.argv:
        if "--all" not in sys.argv and "--pull" not in sys.argv:
            ts = sorted([f for f in os.listdir(CL) if f.startswith("truth-")])[-1][6:-5]
        items = clean(ts)
    if "--all" in sys.argv or "--apply" in sys.argv:
        if "--all" not in sys.argv and "--pull" not in sys.argv and "--clean" not in sys.argv:
            ts = sorted([f for f in os.listdir(CL) if f.startswith("cleaned-")])[-1][8:-5]
        apply(ts)
    if len(sys.argv) == 1:
        print(__doc__)
