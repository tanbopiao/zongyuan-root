#!/usr/bin/env python3
"""truth_store.py · 云端中枢元内核 · append-only 真值库
DID-BR-000002 · Ω₀⊂⊙∞⊂Ω · META-LAW-ARCH-001
职责：真值事件追加落盘(只追加不修改) + HASH-LEDGER 账本 + Merkle 基线
"""
import json, os, hashlib, time, sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRUTH_DIR = os.environ.get("ZR_TRUTH_DIR", os.path.join(BASE_DIR, "..", "data", "truth"))
LEDGER = os.path.join(TRUTH_DIR, "HASH-LEDGER.jsonl")
DB = os.path.join(TRUTH_DIR, "truth.db")
STATE = os.path.join(TRUTH_DIR, "state.json")

DID = "DID-BR-000002"


def _ensure():
    os.makedirs(TRUTH_DIR, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS truth (seq INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, value TEXT, ts TEXT, sha TEXT, event_id TEXT)")
    con.commit()
    return con


def _sha(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ledger_append(seq, event_id, sha):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"seq": seq, "event_id": event_id, "sha": sha, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, ensure_ascii=False) + "\n")


def _state_save():
    # Merkle 根 = 账本全部行的累积哈希
    root = "0000"
    try:
        with open(LEDGER, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    root = hashlib.sha256((root + line.strip()).encode()).hexdigest()
    except FileNotFoundError:
        root = "0000"
    st = {"did": DID, "merkle_root": root, "ledger_lines": _ledger_lines(), "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    return st


def _ledger_lines():
    try:
        with open(LEDGER, encoding="utf-8") as f:
            return sum(1 for l in f if l.strip())
    except FileNotFoundError:
        return 0


def append_truth(key: str, value: dict, x_did: str = None) -> dict:
    """追加一条真值，返回 {seq, event_id, sha, truth_count}"""
    _ensure()
    payload = json.dumps({"key": key, "value": value, "did": x_did or DID}, ensure_ascii=False, sort_keys=True)
    sha = _sha(payload)
    event_id = f"truth-{int(time.time()*1000)}-{sha[:8]}"
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    con = sqlite3.connect(DB)
    cur = con.execute("INSERT INTO truth (key, value, ts, sha, event_id) VALUES (?,?,?,?,?)",
                      (key, json.dumps(value, ensure_ascii=False), ts, sha, event_id))
    seq = cur.lastrowid
    con.commit(); con.close()
    _ledger_append(seq, event_id, sha)
    st = _state_save()
    return {"seq": seq, "event_id": event_id, "sha": sha[:16], "truth_count": st["ledger_lines"]}


def state() -> dict:
    _ensure()
    return _state_save()


def status_ok() -> bool:
    """自检：账本可读、state 可写"""
    try:
        _ensure()
        return state().get("ledger_lines", -1) >= 0
    except Exception:
        return False


if __name__ == "__main__":
    print(json.dumps(append_truth("init.test", {"note": "云端中枢元内核真值库初始化"}), ensure_ascii=False))
