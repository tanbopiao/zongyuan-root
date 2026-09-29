import sqlite3, time

try:
    conn = sqlite3.connect("/home/user/ZONGYUAN-ROOT/ai_proxy/production_tasks.db")
    c = conn.cursor()
    now = time.time()
    c.execute("SELECT task_id, created_at FROM production_tasks WHERE status=?", ("running",))
    cleaned = 0
    for row in c.fetchall():
        if now - row[1] > 3600:
            c.execute("UPDATE production_tasks SET status=?, error=? WHERE task_id=?", 
                      ("failed", "超时自动清理", row[0]))
            cleaned += 1
    conn.commit()
    conn.close()
    if cleaned > 0:
        print("清理超时任务: %d个" % cleaned)
except Exception as e:
    print("任务队列检查错误: %s" % e)
