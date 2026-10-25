#!/usr/bin/env python3
# 联邦记忆池 SFMP
# 每个内核有本地记忆缓存，定期同步到主truth.db
import sqlite3, json, time, os

DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"

def local_recall(query, limit=5):
    # 从truth.db按关键词召回
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT key,value FROM truth WHERE value LIKE ? ORDER BY seq DESC LIMIT ?",
        ("%" + query + "%", limit)).fetchall()
    con.close()
    return [{"key": r[0], "value": r[1][:200]} for r in rows]

def report(key, value):
    # 上报到联邦记忆池（就是写truth.db）
    con = sqlite3.connect(DB)
    con.execute("INSERT INTO truth (key,value,ts,sha,event_id) VALUES (?,?,?,?,?)",
                (key, json.dumps(value, ensure_ascii=False), time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "sfmp"+str(int(time.time())), "sfmp-"+str(int(time.time()*1000))))
    con.commit()
    con.close()

if __name__ == "__main__":
    # 测试召回
    print("召回自治:")
    for r in local_recall("自治", 3):
        print(" -", r["key"], r["value"][:80])
