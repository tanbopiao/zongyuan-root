#!/usr/bin/env python3
# 元学习：从错误中学习新规则
import sqlite3, json, time
DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"

def learn():
    con = sqlite3.connect(DB)
    # 找最近错误
    r = con.execute("SELECT key,value FROM truth WHERE key LIKE \"%error%\" ORDER BY seq DESC LIMIT 3").fetchall()
    rules = []
    for k, v in r:
        if "wrapper" in v.lower():
            rules.append("规则:改wrapper前必须备份+语法检查")
        if "nginx" in v.lower():
            rules.append("规则:改nginx前必须nginx -t测试")
    return list(set(rules))

if __name__ == "__main__":
    for r in learn():
        print(r)
