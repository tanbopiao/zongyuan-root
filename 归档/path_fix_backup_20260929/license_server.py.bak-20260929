#!/usr/bin/env python3
"""ZONGYUAN-ROOT 授权码管理服务"""
import hashlib, json, time, uuid, os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

DB_PATH = "/opt/ZONGYUAN-ROOT/licenses.db"
ADMIN_KEY = "8f95a041594914bdc89c103c9deb723290873220a07ec8d4"

app = FastAPI(title="ZONGYUAN License Server", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS licenses (
        id TEXT PRIMARY KEY,
        license_key TEXT UNIQUE,
        customer_name TEXT,
        customer_email TEXT,
        customer_phone TEXT,
        plan TEXT,
        status TEXT,
        created_at INTEGER,
        expires_at INTEGER,
        machine_id TEXT,
        activated_at INTEGER,
        last_check INTEGER,
        check_count INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()

def generate_key(plan: str, days: int) -> str:
    raw = f"ZY-{plan}-{uuid.uuid4().hex[:16]}-{int(time.time())}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    return f"ZY-{h[:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"

class GenerateReq(BaseModel):
    customer_name: str
    customer_email: str = ""
    customer_phone: str = ""
    plan: str = "trial"
    days: int = 30

class VerifyReq(BaseModel):
    license_key: str
    machine_id: str = ""

@app.on_event("startup")
def startup():
    init_db()

@app.post("/api/v1/license/generate")
def generate(req: GenerateReq, x_api_key: str = Header(None)):
    if x_api_key != ADMIN_KEY:
        raise HTTPException(401, "Unauthorized")
    lic_id = str(uuid.uuid4())
    key = generate_key(req.plan, req.days)
    now = int(time.time())
    expires = now + req.days * 86400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO licenses VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (lic_id, key, req.customer_name, req.customer_email, req.customer_phone,
               req.plan, "active", now, expires, "", 0, 0, 0))
    conn.commit()
    conn.close()
    return {"success": True, "license_id": lic_id, "license_key": key,
            "plan": req.plan, "expires_at": datetime.fromtimestamp(expires).isoformat(),
            "expires_days": req.days}

@app.post("/api/v1/license/verify")
def verify(req: VerifyReq):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM licenses WHERE license_key=?", (req.license_key,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"valid": False, "reason": "授权码不存在"}
    (lid, key, name, email, phone, plan, status, created, expires, mid, activated, last, count) = row
    if status != "active":
        conn.close()
        return {"valid": False, "reason": f"授权码状态: {status}"}
    if expires < int(time.time()):
        c.execute("UPDATE licenses SET status='expired' WHERE id=?", (lid,))
        conn.commit()
        conn.close()
        return {"valid": False, "reason": "授权码已过期"}
    # 首次激活绑定机器
    if not mid and req.machine_id:
        c.execute("UPDATE licenses SET machine_id=?, activated_at=? WHERE id=?",
                  (req.machine_id, int(time.time()), lid))
    elif mid and req.machine_id and mid != req.machine_id:
        conn.close()
        return {"valid": False, "reason": "授权码已绑定其他机器"}
    c.execute("UPDATE licenses SET last_check=?, check_count=check_count+1 WHERE id=?",
              (int(time.time()), lid))
    conn.commit()
    conn.close()
    return {"valid": True, "plan": plan, "customer": name,
            "expires_at": datetime.fromtimestamp(expires).isoformat(),
            "days_remaining": (expires - int(time.time())) // 86400}



@app.get("/health")
async def health():
    return {"status": "healthy", "service": "license", "version": "v1.0"}

@app.get("/status")
async def status():
    return {"service": "license", "version": "v1.0", "status": "running"}
@app.get("/api/v1/license/list")
def list_licenses(x_api_key: str = Header(None)):
    if x_api_key != ADMIN_KEY:
        raise HTTPException(401, "Unauthorized")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM licenses ORDER BY created_at DESC LIMIT 100")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"total": len(rows), "licenses": rows}

@app.get("/api/v1/license/stats")
def stats(x_api_key: str = Header(None)):
    if x_api_key != ADMIN_KEY:
        raise HTTPException(401, "Unauthorized")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT plan, COUNT(*) FROM licenses GROUP BY plan")
    by_plan = dict(c.fetchall())
    c.execute("SELECT status, COUNT(*) FROM licenses GROUP BY status")
    by_status = dict(c.fetchall())
    c.execute("SELECT COUNT(*) FROM licenses")
    total = c.fetchone()[0]
    conn.close()
    return {"total": total, "by_plan": by_plan, "by_status": by_status}

@app.post("/api/v1/trial/request")
def request_trial(req: GenerateReq):
    """公开的免费试用申请接口（无需管理员密钥）"""
    # 限制：同一邮箱/手机号只能申请一次
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if req.customer_email:
        c.execute("SELECT COUNT(*) FROM licenses WHERE customer_email=?", (req.customer_email,))
        if c.fetchone()[0] > 0:
            conn.close()
            return {"success": False, "reason": "该邮箱已申请过试用"}
    if req.customer_phone:
        c.execute("SELECT COUNT(*) FROM licenses WHERE customer_phone=?", (req.customer_phone,))
        if c.fetchone()[0] > 0:
            conn.close()
            return {"success": False, "reason": "该手机号已申请过试用"}
    conn.close()
    # 生成30天试用授权码
    req.plan = "trial"
    req.days = 30
    return generate(req, ADMIN_KEY)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
