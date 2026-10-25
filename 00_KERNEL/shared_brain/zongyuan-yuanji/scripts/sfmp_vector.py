#!/usr/bin/env python3
import sqlite3, json
DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"
def recall(query, limit=5):
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT key,value FROM truth WHERE value LIKE ? ORDER BY seq DESC LIMIT ?",
                       ("%"+query+"%", limit)).fetchall()
    con.close()
    return [{"key":k,"snippet":v[:200]} for k,v in rows]
if __name__=="__main__":
    for r in recall("多模型路由",3):
        print(r["key"])
