#!/usr/bin/env python3
# 政务内核异构插件: /v1/gov/query 真RAG查政务真值
import json, sqlite3

def handle(h, path, p):
    if path != "/v1/gov/query":
        return False
    q = p.get("q", "")
    if not q:
        h._j(400, {"ok": False, "err": "q required"})
        return True
    try:
        con = sqlite3.connect("/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db")
        rows = con.execute("SELECT key,value FROM truth WHERE key LIKE \"GOV%\" AND value LIKE ? ORDER BY seq DESC LIMIT 5", ("%"+q+"%",)).fetchall()
        con.close()
        items = [{"key": k, "value": v[:300]} for k, v in rows]
        h._j(200, {"ok": True, "count": len(items), "items": items, "engine": "gov-rag"})
    except Exception as e:
        h._j(500, {"ok": False, "err": str(e)[:200]})
    return True
