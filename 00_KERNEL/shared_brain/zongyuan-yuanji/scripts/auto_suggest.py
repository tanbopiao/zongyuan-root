#!/usr/bin/env python3
# 主动提进化建议
import sqlite3, subprocess
DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"

def suggest():
    s = []
    con = sqlite3.connect(DB)
    # 最近错误
    r = con.execute("SELECT key FROM truth WHERE key LIKE \"%error%\" OR key LIKE \"%fail%\" ORDER BY seq DESC LIMIT 3").fetchall()
    if r:
        s.append("有错误待处理: "+",".join(x[0] for x in r))
    # 内存
    mem = int(subprocess.run(["free","-m"],capture_output=True,text=True).stdout.split("\n")[1].split()[2])
    if mem > 2500:
        s.append("内存偏高,考虑加缓存策略")
    return s

if __name__ == "__main__":
    for x in suggest():
        print("建议:", x)
