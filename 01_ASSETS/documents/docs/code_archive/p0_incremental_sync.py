#!/usr/bin/env python3
"""P0性能优化①：增量同步改造 - 修复sync_state+添加增量API"""
import sqlite3, subprocess, time, os

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
GW_PATH = "/opt/ZONGYUAN-ROOT/engine/scripts/unified_gateway_9120.py"

print("【1】修复sync_state数据")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES ('global_rev', '1', ?)", (time.time(),))
c.execute("INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES ('last_sync', ?, ?)", (str(time.time()), time.time()))
conn.commit()
c.execute("SELECT * FROM sync_state")
print("  sync_state:", c.fetchall())
conn.close()

print("\n【2】添加增量同步API到记忆网关")
with open(GW_PATH) as f:
    content = f.read()

if "/api/sync/incremental" not in content:
    # 添加增量同步处理方法
    handler = '''
    def _handle_incremental_sync(self):
        """增量同步：客户端携带local_rev，仅返回更新的条目"""
        import urllib.parse
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        local_rev = int(params.get("local_rev", ["0"])[0])
        limit = int(params.get("limit", ["500"])[0])
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT truth_key, truth_value, truth_hash, category, node_id, version, updated_at FROM truths WHERE version > ? ORDER BY version ASC LIMIT ?", (local_rev, limit))
        rows = c.fetchall()
        c.execute("SELECT value FROM sync_state WHERE key='global_rev'")
        gr = c.fetchone()
        current_rev = int(gr[0]) if gr else 0
        conn.close()
        result = {"success": True, "global_rev": current_rev, "incremental_count": len(rows),
                  "truths": [{"key": r[0], "value": r[1], "hash": r[2], "category": r[3], "node_id": r[4], "version": r[5], "updated_at": r[6]} for r in rows]}
        self._send_json(200, result)

'''
    # 在do_GET之前插入处理方法
    content = content.replace("    def do_GET(self):", handler + "    def do_GET(self):", 1)
    
    # 在do_GET中添加路由
    content = content.replace(
        "    def do_GET(self):\n        path = self.path.split(\"?\")[0]",
        "    def do_GET(self):\n        path = self.path.split(\"?\")[0]\n        if path == \"/api/sync/incremental\":\n            self._handle_incremental_sync()\n            return"
    )
    
    with open(GW_PATH, "w") as f:
        f.write(content)
    print("  ✅ 增量同步API已添加")
else:
    print("  ⚠️ 已存在")

print("\n【3】重启记忆网关")
subprocess.run(["systemctl", "restart", "zr-memory-gateway"])
time.sleep(2)

print("\n【4】验证增量同步API")
result = subprocess.run(["curl", "-s", "http://127.0.0.1:9120/api/sync/incremental?local_rev=0&limit=3"],
                       capture_output=True, text=True)
try:
    import json
    d = json.loads(result.stdout)
    print("  global_rev:", d.get("global_rev"))
    print("  增量条目:", d.get("incremental_count"))
    print("  ✅ 增量同步API正常")
except Exception as e:
    print("  ❌ 验证失败:", e, result.stdout[:200])
