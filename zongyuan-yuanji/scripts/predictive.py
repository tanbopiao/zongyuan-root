#!/usr/bin/env python3
# 预测性维护：在问题发生前预防
import sqlite3, time
DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"

def predict():
    con = sqlite3.connect(DB)
    # 看最近错误趋势
    r = con.execute("SELECT COUNT(*) FROM truth WHERE key LIKE \"%error%\" AND seq > (SELECT MAX(seq)-100 FROM truth)").fetchone()
    errors = r[0]
    if errors > 5:
        return f"错误趋势上升({errors}个),建议检查日志"
    return "错误趋势稳定"

if __name__ == "__main__":
    print(predict())
