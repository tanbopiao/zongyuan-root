#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 记忆网关自动吸收守护进程
功能：轮询9120真值网关，自动吸收新真值，分类、去重、锁档
部署：/opt/ZONGYUAN-ROOT/services/truth_absorber/
systemd：zr-truth-absorber.service
"""
import json, time, hashlib, os, sqlite3, urllib.request
from datetime import datetime, timezone

# ===== 配置 =====
GATEWAY_URL = "http://127.0.0.1:9120"
POLL_INTERVAL = 60  # 秒
DB_PATH = "/opt/ZONGYUAN-ROOT/data/truth_absorber.db"
LOG_PATH = "/opt/ZONGYUAN-ROOT/logs/truth_absorber.log"
DID = "DID-BR-000002"

# ===== 分类规则 =====
def classify(key: str, value: dict) -> str:
    k = key.upper()
    if any(x in k for x in ["MR-", "METALAW", "META-RULE", "META_"]):
        return "meta_rule"
    if any(x in k for x in ["AXIOM", "TIANYUAN", "L1", "PRINCIPLE"]):
        return "L1"
    if any(x in k for x in ["SOP", "STANDARD", "POLICY", "RULE", "CONFIG"]):
        return "L2"
    if any(x in k for x in ["STATUS", "HEALTH", "SNAPSHOT", "TEMP", "LOG"]):
        return "L3"
    return "business"

# ===== 数据库初始化 =====
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS absorbed_truths (
        key TEXT PRIMARY KEY,
        level TEXT,
        title TEXT,
        content_hash TEXT,
        absorbed_at TEXT,
        source_node TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event TEXT,
        detail TEXT,
        ts TEXT
    )""")
    conn.commit()
    conn.close()

# ===== HTTP请求 =====
def http_get(path: str) -> dict:
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    try:
        with opener.open(f"{GATEWAY_URL}{path}", timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

# ===== 主循环 =====
def poll_once():
    result = http_get("/api/truths")
    if "error" in result:
        log("ERROR", f"网关不可达: {result['error']}")
        return

    keys = result.get("truths", [])
    conn = sqlite3.connect(DB_PATH)
    absorbed = set(row[0] for row in conn.execute("SELECT key FROM absorbed_truths"))
    new_keys = [k for k in keys if k and k not in absorbed]

    if not new_keys:
        log("INFO", f"无新真值（当前{len(keys)}条）")
        conn.close()
        return

    log("INFO", f"发现{len(new_keys)}条新真值，开始吸收...")
    absorbed_count = 0
    for key in new_keys:
        detail = http_get(f"/api/truth/{key}")
        value = detail.get("value", detail)
        level = classify(key, value)
        title = value.get("title", key) if isinstance(value, dict) else key
        content_str = json.dumps(value, sort_keys=True, ensure_ascii=False)
        chash = hashlib.sha256(content_str.encode()).hexdigest()[:32]
        source = detail.get("source_node", "unknown")
        now = datetime.now(timezone.utc).isoformat()

        conn.execute(
            "INSERT OR REPLACE INTO absorbed_truths VALUES (?,?,?,?,?,?)",
            (key, level, title, chash, now, source)
        )
        absorbed_count += 1
        log("ABSORB", f"[{level}] {key}")

    conn.commit()
    conn.close()
    log("DONE", f"本次吸收{absorbed_count}条，累计{len(keys)}条")

def log(event: str, detail: str):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] [{event}] {detail}\n"
    with open(LOG_PATH, "a") as f:
        f.write(line)

def main():
    init_db()
    log("START", "truth_absorber常驻进程启动")
    while True:
        try:
            poll_once()
        except Exception as e:
            log("ERROR", f"主循环异常: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
