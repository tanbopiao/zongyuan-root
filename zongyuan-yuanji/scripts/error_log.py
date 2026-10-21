#!/usr/bin/env python3
# 错误日志记录
import sqlite3, time
DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"
def log_error(endpoint, error):
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS error_log (id INTEGER PRIMARY KEY AUTOINCREMENT, endpoint TEXT, error TEXT, ts TEXT)")
    con.execute("INSERT INTO error_log (endpoint,error,ts) VALUES (?,?,?)",(endpoint,error[:200],time.strftime("%Y-%m-%d %H:%M")))
    con.commit()
    con.close()
if __name__ == "__main__":
    log_error("/test","test error log")
    print("error_log表就绪")
