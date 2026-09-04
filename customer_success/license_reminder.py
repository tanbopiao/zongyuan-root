"""授权到期提醒 - 到期前7/3/1天自动提醒"""
import json, sqlite3, os
from datetime import datetime, timedelta

DB = "/opt/ZONGYUAN-ROOT/licenses.db"
REMINDER_LOG = "/opt/ZONGYUAN-ROOT/customer_success/reminder_log.json"

def check_expiring():
    if not os.path.exists(DB):
        return []
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        c.execute("SELECT license_key, customer_name, email, plan, expires_at FROM licenses WHERE expires_at IS NOT NULL")
        rows = c.fetchall()
    except:
        rows = []
    conn.close()
    
    now = datetime.now()
    expiring = []
    for key, name, email, plan, expires_str in rows:
        try:
            expires = datetime.fromisoformat(expires_str.replace("Z","+00:00").replace("+00:00",""))
            days_left = (expires - now).days
            if days_left in [7, 3, 1, 0]:
                expiring.append({"key": key, "name": name, "email": email, "plan": plan, "days_left": days_left})
        except: pass
    return expiring

if __name__ == "__main__":
    result = check_expiring()
    log = {"checked_at": datetime.now().isoformat(), "expiring_count": len(result), "items": result}
    with open(REMINDER_LOG, "w") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"授权到期检查: {len(result)} 个即将到期")
    for item in result:
        print(f"  {item['name']}({item['plan']}): {item['days_left']}天后到期 - {item['key']}")
