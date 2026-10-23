#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
truth_bidi_sync.py — 本地 ↔ 云端中枢 真值双向同步引擎 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 2026-10-24

契约（RULE-005 V3.1，2026-10-23/24 黑盒实测，勿凭文档假设）：
  上行 POST /api/report/truth  header X-DID 必带(否则401)
       body {"key","value":{"content","truth_type","source_node","confidence"}}
       废止 truth_key/truth_value -> 400 empty_value_rejected
  下行 GET  /api/truth?limit=200  limit 硬上限200；offset/page/limit=-1 无效
       key= 子串匹配；count=窗口返回条数(会饱和)；精确核验须二次过滤 exact key
  status 是分钟级缓存快照(实测滞后11条seq)，实时性以写入回读为准

方向与语义：
  --pull  云端 -> 本地：limit=200 滑窗，按 seq/event_id 去重合并（云端为准，只增不改）
         缺口(本地落后 > 200)因无 offset 不可补 → 显式写入 state.gaps 并留审计，绝不谎称补齐
  --push  本地 -> 云端：首次运行以本地 max_seq 建基线(push_baseline，历史行按铁律
         「所有新真值必须上报云端」已上报，不重推)；此后只推基线后新增
         且 scope != cloud_sync 的本地行（回流行绝不反向推送）
  --both  顺序 pull → push
  --selftest 离线自测（临时库 + mock transport，不发网络请求）

铁律：说完成必须有回读；说数量必须有 find/SELECT；报告与命令一致。
"""
import os
import sys
import json
import time
import sqlite3
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta

DID = "DID-BR-000002"
NODE = "NODE-DEV-DOUBAO-WORK-001"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
CLOUD_MAIN = "https://www.huodouai.com"
CLOUD_BACKUP = "https://drama.huodouai.com"
PULL_LIMIT = 200                    # 实测硬上限
REPO = Path(__file__).resolve().parent.parent
LOCAL_DB = REPO / "zhongshu/data/truth/truth.db"
MIRROR_DB = Path("/workspace/huodouai-cloud-mirror/truth/truth.db")
STATE_FILE = REPO / "var/truth_sync_state.json"
AUDIT_FILE = REPO / "var/truth_sync_audit.jsonl"
CST = timezone(timedelta(hours=8))


def now_cst():
    return datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S%z")


def short_sha(text):
    """与本地账本口径一致的 16 位短 sha（sha256 前 16 hex）。"""
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


# ---------------------------------------------------------------- state / audit
def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "version": "TRUTH-BIDI-STATE-V1.0",
        "did": DID,
        "last_pushed_seq": 0,
        "push_baseline": 0,
        "last_pull_seq": 0,
        "pull_count": 0,
        "push_count": 0,
        "gaps": [],
        "updated_at": None,
    }


def save_state(st):
    st["updated_at"] = now_cst()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=2))


def audit(rec):
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- cloud transport
class CloudTransport:
    """默认实现走真实 HTTP；selftest 注入 mock。"""

    def __init__(self, base=CLOUD_MAIN, timeout=25):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def pull(self, limit=PULL_LIMIT):
        url = f"{self.base}/api/truth?limit={min(limit, PULL_LIMIT)}"
        req = urllib.request.Request(url, headers={"X-DID": DID})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def push(self, key, value, timeout=25):
        body = json.dumps({"key": key, "value": value}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.base + "/api/report/truth",
            data=body,
            headers={"Content-Type": "application/json", "X-DID": DID},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())


# ---------------------------------------------------------------- local ledger
class LocalLedger:
    def __init__(self, db_path):
        self.db = Path(db_path)
        self.conn = sqlite3.connect(str(self.db))
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS truth ("
            "seq INTEGER PRIMARY KEY, key TEXT, value TEXT, ts TEXT,"
            "sha TEXT, event_id TEXT, scope TEXT)"
        )

    def max_seq(self):
        return self.conn.execute("SELECT COALESCE(MAX(seq),0) FROM truth").fetchone()[0]

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM truth").fetchone()[0]

    def event_ids(self, seqs):
        if not seqs:
            return set()
        q = ",".join("?" * len(seqs))
        rows = self.conn.execute(
            f"SELECT event_id FROM truth WHERE seq IN ({q})", list(seqs)
        ).fetchall()
        return {r[0] for r in rows}

    def insert_cloud(self, rows):
        """只增不改（云端为准）：同 seq 已存在则跳过；同 seq 不同 event_id → 记冲突。"""
        added, conflicts = 0, []
        for r in rows:
            seq = int(r["seq"])
            val = r.get("value")
            val_str = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
            cur = self.conn.execute("SELECT event_id FROM truth WHERE seq=?", (seq,)).fetchone()
            if cur:
                if cur[0] != r.get("event_id"):
                    conflicts.append({"seq": seq, "local_event": cur[0], "cloud_event": r.get("event_id")})
                continue
            self.conn.execute(
                "INSERT OR IGNORE INTO truth (seq,key,value,ts,sha,event_id,scope) "
                "VALUES (?,?,?,?,?,?,?)",
                (seq, r.get("key", ""), val_str, r.get("ts", ""),
                 short_sha(val_str), r.get("event_id", ""), "cloud_sync"),
            )
            added += 1
        self.conn.commit()
        return added, conflicts

    def pending_upstream(self, since_seq):
        """待上行：本地自产（非 cloud_sync 回流）且 seq > since_seq。"""
        return self.conn.execute(
            "SELECT seq,key,value,ts,sha,event_id FROM truth "
            "WHERE seq > ? AND scope != 'cloud_sync' ORDER BY seq ASC LIMIT 500",
            (since_seq,),
        ).fetchall()

    def close(self):
        self.conn.close()


# ---------------------------------------------------------------- sync ops
def do_pull(transport, ledger, state):
    d = transport.pull(PULL_LIMIT)
    results = d.get("results", [])
    if not results:
        return {"pulled": 0, "added": 0, "note": "empty window"}
    seqs = [int(r["seq"]) for r in results]
    cloud_top = max(seqs)
    local_top = ledger.max_seq()

    # 缺口检测：云端顶 - 本地顶 > 窗口 → 窗口外历史因无 offset 不可补，显式声明
    gap = None
    if cloud_top - local_top > PULL_LIMIT:
        gap = {
            "from_seq": local_top + 1,
            "to_seq": cloud_top - PULL_LIMIT,
            "reason": "cloud_has_no_offset_API(limit=200 max); historical window unreachable",
            "ts": now_cst(),
        }
        state.setdefault("gaps", []).append(gap)

    added, conflicts = ledger.insert_cloud(results)
    state["last_pull_seq"] = cloud_top
    state["pull_count"] = state.get("pull_count", 0) + added

    out = {
        "cloud_window": len(results),
        "cloud_top_seq": cloud_top,
        "local_top_seq": local_top,
        "added": added,
        "conflicts": len(conflicts),
        "gap": gap,
        "saturation": len(results) >= PULL_LIMIT,
    }
    if conflicts:
        out["conflict_detail"] = conflicts[:5]
    return out


def do_push(transport, ledger, state):
    # 基线初始化：首跑以本地 max_seq 为界，历史行不重推（铁律已上报过的旧账不翻）
    if not state.get("push_baseline"):
        base = ledger.max_seq()
        state["last_pushed_seq"] = base
        state["push_baseline"] = base
        audit({"ts": now_cst(), "mode": "push_baseline", "baseline_seq": base})
        return {"candidate": 0, "pushed": 0, "skipped": 0, "failed": [],
                "baseline_init": base,
                "note": "first run: baseline = local max_seq; historical rows not re-pushed"}
    rows = ledger.pending_upstream(state.get("last_pushed_seq", state["push_baseline"]))
    pushed, failed, skipped = 0, [], 0
    for seq, key, value, ts, sha, event_id in rows:
        # 空/缺 content 会被 400 拒绝 → 本地保底包装
        content = value if value else json.dumps({"local_seq": seq, "ts": ts}, ensure_ascii=False)
        payload = {
            "content": content,
            "truth_type": "data",
            "source_node": NODE,
            "confidence": 1.0,
        }
        try:
            r = transport.push(key, payload)
            if r.get("ok"):
                pushed += 1
                state["last_pushed_seq"] = seq
            else:
                failed.append({"seq": seq, "resp": r})
                break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:200]
            failed.append({"seq": seq, "http": e.code, "detail": detail})
            break                      # 契约错误立即停，不盲重试
        except Exception as e:
            failed.append({"seq": seq, "err": str(e)[:200]})
            break
        time.sleep(0.12)               # 轻量节流
    state["push_count"] = state.get("push_count", 0) + pushed
    return {
        "candidate": len(rows),
        "pushed": pushed,
        "skipped": skipped,
        "failed": failed,
        "last_pushed_seq": state.get("last_pushed_seq", 0),
    }


def run(mode, transport=None, db_path=None, dry=False):
    transport = transport or CloudTransport()
    ledger = LocalLedger(db_path or LOCAL_DB)
    state = load_state()
    report = {"mode": mode, "ts": now_cst(), "did": DID}

    if mode in ("pull", "both"):
        _safe_pull(transport, ledger, state, report)   # 成功->report["pull"]，异常->report["pull_error"]
    if mode in ("push", "both"):
        if dry:
            base = state.get("push_baseline") or ledger.max_seq()
            rows = ledger.pending_upstream(state.get("last_pushed_seq") or base)
            report["push"] = {"dry_run": True, "candidate": len(rows), "baseline": base}
        else:
            report["push"] = do_push(transport, ledger, state)

    if not dry:
        save_state(state)
        audit({"ts": now_cst(), "mode": mode, "report": report,
               "local_rows": ledger.count(), "local_max_seq": ledger.max_seq()})
    report["local"] = {"rows": ledger.count(), "max_seq": ledger.max_seq()}
    ledger.close()
    return report


def _safe_pull(transport, ledger, state, report):
    """pull 执行器；成功返回 None，异常写入 report['pull_error'] 并返回错误对象。"""
    try:
        report["pull"] = do_pull(transport, ledger, state)
        return None
    except Exception as e:
        report["pull_error"] = str(e)[:300]
        return e


# ---------------------------------------------------------------- selftest
def selftest():
    """离线自测：临时库 + mock transport，不发任何网络请求。"""
    import tempfile
    import shutil

    tmp = Path(tempfile.mkdtemp(prefix="bidi_test_"))
    db = tmp / "truth.db"
    stfile = tmp / "state.json"
    global STATE_FILE, AUDIT_FILE
    STATE_FILE, AUDIT_FILE = stfile, tmp / "audit.jsonl"

    ck = [0]

    def ok(cond, name):
        ck[0] += 1
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            raise AssertionError(name)

    class MockTransport:
        def __init__(self):
            self.pushed = []

        def pull(self, limit=PULL_LIMIT):
            # 窗口: 1 与本地重复, 2 为新增, 3 与本地同 seq 但 event_id 不同(冲突)
            return {"ok": True, "count": 3, "results": [
                {"seq": 101, "key": "K.A", "value": {"content": "a1"}, "ts": "2026-10-24T01:00:00+0800", "event_id": "e-101"},
                {"seq": 102, "key": "K.B", "value": {"content": "b1"}, "ts": "2026-10-24T01:00:01+0800", "event_id": "e-102"},
                {"seq": 90,  "key": "K.C", "value": {"content": "c1"}, "ts": "2026-10-24T01:00:02+0800", "event_id": "e-90-NEW"},
            ]}

        def push(self, key, value):
            self.pushed.append({"key": key, "value": value})
            return {"ok": True, "key": key, "seq": 5000 + len(self.pushed)}

    # 本地既有账本: seq90(旧event), seq101(与云端重复), 一条本地自产 seq200
    led = LocalLedger(db)
    led.conn.execute("INSERT INTO truth VALUES (90,'K.C','\"c0\"','2026-10-23T00:00:00+0800','sha90','e-90-OLD','general')")
    led.conn.execute("INSERT INTO truth VALUES (101,'K.A','\"a0\"','2026-10-23T00:00:01+0800','sha101','e-101','general')")
    led.conn.execute("INSERT INTO truth VALUES (200,'LOCAL.NEW','\"mine\"','2026-10-24T00:00:00+0800','sha200','e-200','local')")
    led.conn.commit()

    mock = MockTransport()

    # 1) pull: 新增 102 + 90(冲突不覆盖)
    rep = do_pull(mock, led, st := load_state())
    ok(rep["added"] == 1, "pull 只新增 1 条(seq102)")
    ok(rep["cloud_top_seq"] == 102, "cloud_top=102")
    ok(rep["conflicts"] == 1, "seq90 event_id 不同 → 记 1 冲突不覆盖")
    ok(led.count() == 4, "本地 4 行 (90,101,102,200)")
    v90 = led.conn.execute("SELECT value,event_id FROM truth WHERE seq=90").fetchone()
    ok(v90[1] == "e-90-OLD", "冲突时保留本地(event_id 未被改写)")

    # 2) pull 幂等
    rep2 = do_pull(mock, led, st)
    ok(rep2["added"] == 0, "重复 pull 幂等 added=0")

    # 3) gap 检测: 本地 top=200(seq200 本地自产), 云端顶=1000 → 窗口(801-1000)外历史不可达
    led.conn.execute("DELETE FROM truth WHERE seq=102")
    led.conn.commit()
    st["gaps"] = []
    mock.pull = lambda limit=PULL_LIMIT: {"ok": True, "count": 1, "results": [
        {"seq": 1000, "key": "K.L", "value": {"content": "l"}, "ts": "2026-10-24T02:00:00+0800", "event_id": "e-1000"}]}
    rep3 = do_pull(mock, led, st)
    ok(rep3["local_top_seq"] == 200, "gap 场景 local_top=200 (拉取前)")
    ok(rep3["gap"] is not None and rep3["gap"]["from_seq"] == 201, "gap 声明 from=201 (local_top+1)")
    ok(st["gaps"][0]["to_seq"] == 800, "gap to = 1000-200 = 800")

    # 4) push: 首跑建基线(此时本地 max=1000)，历史行(90/101/200)与 cloud_sync 回流都不推
    st["last_pushed_seq"] = 0
    st["push_baseline"] = 0
    rep4 = do_push(mock, led, st)
    ok(rep4["baseline_init"] == 1000, "首跑基线=本地 max_seq(1000)")
    ok(rep4["pushed"] == 0 and len(mock.pushed) == 0, "基线前历史行不重推")

    # 4b) 基线后新增本地行才会被推 (scope != cloud_sync)
    led.conn.execute("INSERT INTO truth VALUES (1001,'LOCAL.NEW2','\"mine2\"','2026-10-24T00:00:01+0800','sha1001','e-1001','general')")
    led.conn.commit()
    rep4b = do_push(mock, led, st)
    ok(rep4b["pushed"] == 1, "上行只推 1 条基线后新增")
    ok(len(mock.pushed) == 1 and mock.pushed[0]["key"] == "LOCAL.NEW2", "推送 key 正确")
    ok("content" in mock.pushed[0]["value"], "RULE-005 V3.1: value.content 存在")
    ok("truth_key" not in mock.pushed[0], "废止字段 truth_key 不存在")

    # 5) push 幂等 (last_pushed_seq 已推进)
    rep5 = do_push(mock, led, st)
    ok(rep5["pushed"] == 0, "二次 push 幂等 pushed=0")

    # 6) 状态与审计落盘
    save_state(st)
    ok(stfile.exists() and json.loads(stfile.read_text())["last_pushed_seq"] == 1001, "state 落盘且 last_pushed=1001")
    audit({"ts": now_cst(), "mode": "selftest", "n": ck[0]})
    ok(AUDIT_FILE.exists() and AUDIT_FILE.read_text().strip().endswith("}"), "审计 jsonl 追加成功")

    # 7) limit 上限约束
    ok(PULL_LIMIT == 200, "窗口硬上限=200 (契约实测)")

    led.close()
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nSELFTEST: {ck[0]}/{ck[0]} ALL PASS")
    return 0


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        sys.exit(selftest())
    mode = "both"
    if "--pull" in args:
        mode = "pull"
    elif "--push" in args:
        mode = "push"
    dry = "--dry-run" in args
    rep = run(mode, dry=dry)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
