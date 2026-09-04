"""客户健康度评分 - 基于使用数据"""
import json, os, sqlite3
from datetime import datetime

def get_customers():
    db = "/opt/ZONGYUAN-ROOT/licenses.db"
    if not os.path.exists(db): return []
    conn = sqlite3.connect(db)
    c = conn.cursor()
    try:
        c.execute("SELECT license_key, customer_name, plan, created_at, expires_at FROM licenses")
        rows = c.fetchall()
    except: rows = []
    conn.close()
    return rows

def score_customer(customer):
    key, name, plan, created, expires = customer
    score = 50  # 基础分
    # 授权状态
    try:
        exp = datetime.fromisoformat(str(expires).replace("Z","+00:00").replace("+00:00",""))
        days = (exp - datetime.now()).days
        score += 20 if days > 30 else 10 if days > 7 else -10 if days <= 0 else 0
    except: pass
    # 计划等级
    score += {"enterprise": 20, "professional": 15, "personal": 10, "trial": 5, "free": 0}.get(plan, 0)
    return min(score, 100)

if __name__ == "__main__":
    customers = get_customers()
    results = []
    for c in customers:
        health = score_customer(c)
        level = "A健康" if health >= 80 else "B正常" if health >= 60 else "C关注" if health >= 40 else "D流失风险"
        results.append({"name": c[1], "plan": c[2], "health_score": health, "level": level})
    print(json.dumps({"total": len(results), "customers": results}, ensure_ascii=False, indent=2))
