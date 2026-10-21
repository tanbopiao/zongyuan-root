#!/usr/bin/env python3
# 真产品化：API Key鉴权+用量统计
import sqlite3, time
DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"

def check_keys():
    con = sqlite3.connect(DB)
    try:
        r = con.execute("SELECT COUNT(*) FROM usage").fetchone()
        return f"已有{r[0]}条用量记录"
    except:
        return "usage表不存在"

if __name__ == "__main__":
    print(check_keys())
