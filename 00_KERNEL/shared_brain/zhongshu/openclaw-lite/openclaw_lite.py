#!/usr/bin/env python3
"""openclaw_lite.py · 云端中枢 OpenClaw 轻量化复刻层
DID-BR-000002 · Ω₀⊂⊙∞⊂Ω · 基于 truth_store 增量扩展，不覆盖现有网关
六大模块：
  1. 压缩前记忆刷新钩子   POST /oc/memory/refresh
  2. 跨Agent记忆迁移      POST /oc/memory/export | POST /oc/memory/import
  3. 统一网关路由层       POST /oc/router
  4. 技能安全审查闭环     POST /oc/skills/submit | GET /oc/skills/queue | POST /oc/skills/review
  5. 心跳主动待办派发     POST /oc/heartbeat/todo | GET /oc/heartbeat/todos | POST /oc/heartbeat/todo/ack
  6. 沙箱执行策略         POST /oc/exec/sandbox
附：GET /oc/status（服务状态）
"""
import json, os, re, time, sqlite3, subprocess, hashlib, socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# ---------- 路径 ----------
BASE = os.path.dirname(os.path.abspath(__file__))
TRUTH_DIR = os.environ.get("ZR_TRUTH_DIR", "/www/wwwroot/huodouai.com/zhongshu/data/truth")
DB = os.path.join(TRUTH_DIR, "truth.db")
OC_DB = os.path.join(BASE, "oc_lite.db")
DID = "DID-BR-000002"
VALID_DIDS = {"DID-BR-000002", "DID-BR-000003", "NODE-DEV-DOUBAO-WORK-001", "NODE-CLOUD-WORKER-001"}

# 统一网关路由表：target -> (内网转发地址, 路径前缀, 需保留的子路径?)
ROUTES = {
    "feishu":  {"host": "127.0.0.1", "port": 9001, "path": "/api/report/truth"},
    "truth":   {"host": "127.0.0.1", "port": 9001, "path": "/api/report/truth"},
    "octop":   {"host": "127.0.0.1", "port": 8088, "path": "/api/health"},
    "a2a":     {"host": "127.0.0.1", "port": 8930, "path": "/a2a/queue/stats"},
    "distill": {"host": "127.0.0.1", "port": 9001, "path": "/api/report/truth"},
    "lake":    {"host": "127.0.0.1", "port": 8931, "path": "/"},
    "kg":      {"host": "127.0.0.1", "port": 8932, "path": "/"},
    "mcp":     {"host": "127.0.0.1", "port": 8766, "path": "/"},
}

# 沙箱危险命令/模式黑名单
SANDBOX_BLACKLIST = [
    "rm -rf", "mkfs", "dd if=", "shutdown", "reboot", "halt",
    ":(){", "fork bomb", "chmod -R 777 /", "> /dev/sda", "sudo",
    "curl.*|.*sh", "wget.*|.*sh", "base64 -d.*sh", "python -c", "eval(", "exec(",
    "subprocess", "os.system", "open(", "socket.", "/etc/passwd", "/etc/shadow",
    "chown", "useradd", "passwd", "iptables", "systemctl", "docker", "kubectl",
]

# 技能静态扫描危险模式
SKILL_SCAN_RULES = [
    ("exec(", 1), ("eval(", 1), ("os.system", 1), ("subprocess", 1),
    ("rm -rf", 1), ("shutdown", 1), ("reboot", 1), ("socket.", 1),
    ("curl", 0), ("requests", 0), ("http://", 0), ("api_key", 0), ("password", 0),
    ("/etc/", 0), ("/root/", 0), ("sudo", 1), ("base64", 0), ("pickle.load", 1),
    ("__import__", 1), ("compile(", 1), ("pty", 1), ("mkfifo", 1),
]


def _oc_ensure():
    """oc_lite.db：skills + todos 两张表"""
    os.makedirs(BASE, exist_ok=True)
    con = sqlite3.connect(OC_DB)
    con.execute("CREATE TABLE IF NOT EXISTS skills (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, desc TEXT, code TEXT, author TEXT, sha TEXT, status TEXT DEFAULT 'pending', scan_result TEXT DEFAULT '{}', created_at TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, target TEXT, task TEXT, status TEXT DEFAULT 'pending', claimed_by TEXT DEFAULT '', created_at TEXT, acked_at TEXT)")
    con.commit()
    return con


def _append_truth(key, value):
    """复用真值库（append-only）"""
    from urllib.request import Request, urlopen
    req = Request("http://127.0.0.1:9001/api/report/truth",
                  data=json.dumps({"key": key, "value": value}).encode("utf-8"),
                  headers={"Content-Type": "application/json", "X-DID": DID}, method="POST")
    try:
        with urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


def _forward(target, payload):
    """统一网关路由转发"""
    if target not in ROUTES:
        return {"ok": False, "error": f"未知target: {target}", "routes": list(ROUTES.keys())}
    r = ROUTES[target]
    from urllib.request import Request, urlopen
    url = f"http://{r['host']}:{r['port']}{r['path']}"
    try:
        req = Request(url, data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json", "X-DID": DID}, method="POST")
        with urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return {"ok": True, "target": target, "http": resp.status, "body": body[:500]}
    except Exception as e:
        return {"ok": False, "target": target, "error": str(e)[:150]}


def _scan_skill(code):
    """技能静态扫描：返回 {risk_score, findings}"""
    score = 0
    findings = []
    for pattern, weight in SKILL_SCAN_RULES:
        if pattern in code:
            score += weight
            findings.append({"pattern": pattern, "weight": weight})
    level = "safe" if score == 0 else ("review" if score <= 2 else "danger")
    return {"risk_score": score, "level": level, "findings": findings}


def _sandbox_exec(command, timeout=10, cwd=None):
    """沙箱执行：白名单命令 + 超时 + 黑名单拦截 + 输出限制"""
    cmd = command.strip()
    if not cmd:
        return {"ok": False, "error": "空命令"}
    for bad in SANDBOX_BLACKLIST:
        if bad in cmd:
            return {"ok": False, "error": f"沙箱拦截: 命中危险模式 '{bad}'", "blocked": True}
    # 白名单：仅允许安全基础命令
    first = cmd.split()[0]
    ALLOWED = {"echo", "cat", "ls", "pwd", "whoami", "date", "head", "tail",
               "wc", "grep", "find", "printf", "df", "du", "free", "uname",
               "curl", "wget", "python3", "python", "node", "sha256sum", "md5sum"}
    if first not in ALLOWED:
        return {"ok": False, "error": f"沙箱拦截: 命令 '{first}' 不在白名单", "blocked": True}
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=timeout, cwd=cwd or BASE,
                              env={**os.environ, "PATH": "/usr/local/bin:/usr/bin:/bin"})
        out = (proc.stdout or "")[:2000]
        err = (proc.stderr or "")[:1000]
        return {"ok": True, "exit_code": proc.returncode, "stdout": out, "stderr": err}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"执行超时(>{timeout}s)", "blocked": True}
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not length:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as e:
            return {"_parse_error": str(e)[:100]}

    def _check_auth(self):
        x_did = self.headers.get("X-DID", "")
        return x_did in VALID_DIDS

    # ---------- GET ----------
    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/oc/status":
            _oc_ensure()
            con = sqlite3.connect(OC_DB)
            skill_cnt = con.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
            todo_cnt = con.execute("SELECT COUNT(*) FROM todos").fetchone()[0]
            con.close()
            self._send(200, {
                "ok": True, "service": "openclaw-lite", "version": "V1.0",
                "did": DID, "anchor": "Ω₀⊂⊙∞⊂Ω",
                "modules": ["memory_refresh", "memory_migrate", "router", "skill_review", "heartbeat_todo", "sandbox_exec"],
                "stats": {"skills": skill_cnt, "todos": todo_cnt},
            })
        elif p == "/oc/skills/queue":
            if not self._check_auth():
                self._send(401, {"error": "unauthorized"}); return
            _oc_ensure()
            con = sqlite3.connect(OC_DB)
            rows = con.execute("SELECT id,name,desc,author,status,scan_result,created_at FROM skills ORDER BY id DESC LIMIT 50").fetchall()
            con.close()
            self._send(200, {"ok": True, "count": len(rows), "queue": [
                {"id": r[0], "name": r[1], "desc": r[2], "author": r[3], "status": r[4], "scan": json.loads(r[5]), "created_at": r[6]} for r in rows]})
        elif p == "/oc/heartbeat/todos":
            _oc_ensure()
            con = sqlite3.connect(OC_DB)
            rows = con.execute("SELECT id,target,task,status,claimed_by,created_at FROM todos WHERE status='pending' ORDER BY id ASC LIMIT 20").fetchall()
            con.close()
            self._send(200, {"ok": True, "count": len(rows), "todos": [
                {"id": r[0], "target": r[1], "task": r[2], "status": r[3], "claimed_by": r[4], "created_at": r[5]} for r in rows]})
        else:
            self._send(404, {"error": "not_found", "message": f"未知端点: {p}"})

    # ---------- POST ----------
    def do_POST(self):
        p = urlparse(self.path).path
        # 统一鉴权（公开端点除外）
        public_eps = {"/oc/memory/refresh", "/oc/router", "/oc/exec/sandbox"}
        if p not in public_eps and not self._check_auth():
            self._send(401, {"error": "unauthorized", "message": "X-DID 未授权"}); return
        payload = self._read_json()
        if "_parse_error" in payload:
            self._send(400, {"error": "bad_json", "message": payload["_parse_error"]}); return

        # ---- 1. 压缩前记忆刷新钩子 ----
        if p == "/oc/memory/refresh":
            key = payload.get("key", "MEMORY.REFRESH." + time.strftime("%Y%m%d-%H%M%S"))
            content = payload.get("content", "")
            session = payload.get("session", "unknown")
            if not content:
                self._send(400, {"error": "content_required"}); return
            # 提炼：压缩前把关键结论直接沉淀为真值
            distilled = {
                "event": "memory_refresh_pre_compaction",
                "session": session,
                "content_len": len(content),
                "content_snapshot": content[:2000],
                "origin": "openclaw-lite",
                "did": DID,
            }
            r = _append_truth(key, distilled)
            self._send(200, {"ok": True, "refreshed": True, "key": key, "truth": r})

        # ---- 2a. 跨Agent记忆导出 ----
        elif p == "/oc/memory/export":
            scope = payload.get("scope", "META.")
            limit = int(payload.get("limit", 200))
            agent_id = payload.get("agent_id", DID)
            # 从真值库读取
            rows = []
            try:
                con = sqlite3.connect(DB)
                cur = con.execute("SELECT seq,key,value,ts FROM truth WHERE key LIKE ? ORDER BY seq DESC LIMIT ?", (scope + "%", limit))
                rows = cur.fetchall()
                con.close()
            except Exception as e:
                self._send(500, {"error": str(e)[:120]}); return
            exported = {
                "format": "zr-memory-v1",
                "agent_id": agent_id,
                "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "scope": scope,
                "count": len(rows),
                "blocks": [{"seq": r[0], "key": r[1], "value": json.loads(r[2]), "ts": r[3]} for r in rows[:limit]],
            }
            self._send(200, {"ok": True, "export": exported})

        # ---- 2b. 跨Agent记忆导入 ----
        elif p == "/oc/memory/import":
            exp = payload.get("export", payload)
            blocks = exp.get("blocks", [])
            if not blocks:
                self._send(400, {"error": "blocks_required"}); return
            imported = 0
            for b in blocks:
                key = b.get("key", "")
                val = b.get("value", {})
                if key and isinstance(val, dict):
                    r = _append_truth(key, val)
                    if r.get("ok", True):
                        imported += 1
            self._send(200, {"ok": True, "imported": imported, "total": len(blocks),
                             "note": "append-only: 导入以新增写入，不覆盖既有"})

        # ---- 3. 统一网关路由层 ----
        elif p == "/oc/router":
            target = payload.get("target", "")
            body = payload.get("body", payload)
            if not target:
                self._send(400, {"error": "target_required", "routes": list(ROUTES.keys())}); return
            r = _forward(target, body)
            self._send(200 if r.get("ok") else 502, r)

        # ---- 4a. 技能提交 ----
        elif p == "/oc/skills/submit":
            name = payload.get("name", "")
            desc = payload.get("desc", "")
            code = payload.get("code", "")
            author = payload.get("author", DID)
            if not name or not code:
                self._send(400, {"error": "name_and_code_required"}); return
            sha = hashlib.sha256(code.encode()).hexdigest()[:16]
            scan = _scan_skill(code)
            _oc_ensure()
            con = sqlite3.connect(OC_DB)
            cur = con.execute("INSERT INTO skills (name,desc,code,author,sha,status,scan_result,created_at) VALUES (?,?,?,?,?,?,?,?)",
                              (name, desc, code, author, sha, "pending", json.dumps(scan, ensure_ascii=False), time.strftime("%Y-%m-%dT%H:%M:%S%z")))
            con.commit()
            sid = cur.lastrowid
            con.close()
            self._send(200, {"ok": True, "skill_id": sid, "sha": sha, "scan": scan,
                             "message": "已进入审查队列", "status": "pending"})

        # ---- 4b. 技能审查(approve/reject) ----
        elif p == "/oc/skills/review":
            sid = payload.get("skill_id")
            action = payload.get("action", "")
            if not sid or action not in ("approve", "reject"):
                self._send(400, {"error": "skill_id_and_action_required", "actions": ["approve", "reject"]}); return
            _oc_ensure()
            con = sqlite3.connect(OC_DB)
            row = con.execute("SELECT name,scan_result FROM skills WHERE id=?", (sid,)).fetchone()
            if not row:
                con.close()
                self._send(404, {"error": "skill_not_found"}); return
            scan = json.loads(row[1])
            if action == "approve" and scan.get("level") == "danger":
                con.close()
                self._send(400, {"error": "danger_skill_cannot_approve", "scan": scan}); return
            new_status = "approved" if action == "approve" else "rejected"
            con.execute("UPDATE skills SET status=? WHERE id=?", (new_status, sid))
            con.commit()
            con.close()
            # 上架成功记录真值
            if action == "approve":
                _append_truth("SKILL.APPROVED." + str(sid), {"skill_id": sid, "name": row[0], "scan": scan, "by": DID})
            self._send(200, {"ok": True, "skill_id": sid, "status": new_status})

        # ---- 5a. 心跳主动待办派发 ----
        elif p == "/oc/heartbeat/todo":
            target = payload.get("target", "all")
            task = payload.get("task", "")
            if not task:
                self._send(400, {"error": "task_required"}); return
            _oc_ensure()
            con = sqlite3.connect(OC_DB)
            cur = con.execute("INSERT INTO todos (target,task,status,created_at) VALUES (?,?,?,?)",
                              (target, task, "pending", time.strftime("%Y-%m-%dT%H:%M:%S%z")))
            con.commit()
            tid = cur.lastrowid
            con.close()
            _append_truth("HEARTBEAT.TODO." + str(tid), {"todo_id": tid, "target": target, "task": task, "by": DID})
            self._send(200, {"ok": True, "todo_id": tid, "target": target, "status": "pending"})

        # ---- 5b. 待办确认完成 ----
        elif p == "/oc/heartbeat/todo/ack":
            tid = payload.get("todo_id")
            node = payload.get("node", DID)
            if not tid:
                self._send(400, {"error": "todo_id_required"}); return
            _oc_ensure()
            con = sqlite3.connect(OC_DB)
            row = con.execute("SELECT task FROM todos WHERE id=?", (tid,)).fetchone()
            if not row:
                con.close()
                self._send(404, {"error": "todo_not_found"}); return
            con.execute("UPDATE todos SET status='done', claimed_by=?, acked_at=? WHERE id=?", (node, time.strftime("%Y-%m-%dT%H:%M:%S%z"), tid))
            con.commit()
            con.close()
            _append_truth("HEARTBEAT.TODO.DONE." + str(tid), {"todo_id": tid, "task": row[0], "done_by": node})
            self._send(200, {"ok": True, "todo_id": tid, "status": "done", "done_by": node})

        # ---- 6. 沙箱执行 ----
        elif p == "/oc/exec/sandbox":
            command = payload.get("command", "")
            timeout = int(payload.get("timeout", 10))
            cwd = payload.get("cwd", BASE)
            r = _sandbox_exec(command, timeout=min(timeout, 30), cwd=cwd)
            # 审计日志（记录执行请求）
            _append_truth("SANDBOX.EXEC." + time.strftime("%Y%m%d%H%M%S"), {
                "command": command[:200], "result": r.get("ok"), "exit": r.get("exit_code"),
                "by": self.headers.get("X-DID", "anonymous"), "blocked": r.get("blocked", False)})
            self._send(200 if r.get("ok") else 400, r)
        else:
            self._send(404, {"error": "not_found", "message": f"未知端点: {p}"})


def main():
    _oc_ensure()
    port = int(os.environ.get("OC_PORT", "8935"))
    srv = HTTPServer(("127.0.0.1", port), Handler)
    print(f"[openclaw-lite] 已启动 127.0.0.1:{port} | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
