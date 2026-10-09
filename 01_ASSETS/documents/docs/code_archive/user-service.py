#!/usr/bin/env python3
"""
火斗云智AIOS 用户系统服务
端口: 8090
功能: 注册/登录/JWT认证/API Key管理/用量统计/套餐管理
"""
import os
import json
import time
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import sqlite3
import jwt

# ============ 配置 ============
APP_DIR = "/opt/user-service"
DATA_DIR = f"{APP_DIR}/data"
DB_PATH = f"{DATA_DIR}/users.db"
JWT_SECRET = os.environ.get("JWT_SECRET", "huodou-aios-jwt-secret-2026-omega")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7  # 7天

os.makedirs(DATA_DIR, exist_ok=True)

# ============ 数据库 ============
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # 用户表
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT DEFAULT '',
        avatar TEXT DEFAULT '',
        plan TEXT DEFAULT 'free',
        status TEXT DEFAULT 'active',
        created_at REAL,
        updated_at REAL,
        last_login_at REAL
    )""")
    # API Key表
    c.execute("""CREATE TABLE IF NOT EXISTS api_keys (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        name TEXT DEFAULT 'default',
        key_hash TEXT UNIQUE NOT NULL,
        key_prefix TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        created_at REAL,
        last_used_at REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    # 用量表
    c.execute("""CREATE TABLE IF NOT EXISTS usage (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        api_key_id TEXT,
        model TEXT NOT NULL,
        endpoint TEXT DEFAULT '',
        prompt_tokens INTEGER DEFAULT 0,
        completion_tokens INTEGER DEFAULT 0,
        total_tokens INTEGER DEFAULT 0,
        requests INTEGER DEFAULT 1,
        created_at REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    # 订单表
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        plan TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'CNY',
        status TEXT DEFAULT 'pending',
        payment_method TEXT DEFAULT '',
        transaction_id TEXT DEFAULT '',
        created_at REAL,
        paid_at REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    conn.commit()
    conn.close()

init_db()

# ============ 工具函数 ============
def hash_password(password: str) -> str:
    return hashlib.sha256((password + JWT_SECRET).encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash

def generate_api_key() -> tuple:
    """生成API Key，返回 (明文key, key_hash, key_prefix)"""
    raw = "hd-" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    key_prefix = raw[:12] + "..."
    return raw, key_hash, key_prefix

def create_jwt(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效Token")

# ============ 套餐配置 ============
PLANS = {
    "free": {
        "name": "免费版",
        "price_monthly": 0,
        "price_yearly": 0,
        "limits": {
            "7b_tokens_monthly": 100000,
            "05b_tokens_monthly": 1000000,
            "memory_entries": 10000,
            "api_keys": 3,
            "rate_limit_per_min": 10
        }
    },
    "pro": {
        "name": "专业版",
        "price_monthly": 99,
        "price_yearly": 950,
        "limits": {
            "7b_tokens_monthly": 5000000,
            "05b_tokens_monthly": 50000000,
            "memory_entries": 500000,
            "api_keys": 20,
            "rate_limit_per_min": 100
        }
    },
    "enterprise": {
        "name": "企业版",
        "price_monthly": 999,
        "price_yearly": 9500,
        "limits": {
            "7b_tokens_monthly": 50000000,
            "05b_tokens_monthly": 500000000,
            "memory_entries": -1,  # 无限
            "api_keys": 100,
            "rate_limit_per_min": 500
        }
    }
}

# ============ Pydantic模型 ============
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = ""

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class CreateApiKeyRequest(BaseModel):
    name: str = "default"

class UsageRecordRequest(BaseModel):
    api_key: str
    model: str
    endpoint: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

# ============ FastAPI应用 ============
app = FastAPI(title="火斗云智AIOS 用户系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 认证依赖 ============
def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证Token")
    token = authorization.replace("Bearer ", "")
    payload = verify_jwt(token)
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (payload["user_id"],)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if user["status"] != "active":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return dict(user)

# ============ 路由 ============

@app.get("/health")
async def health():
    return {"status": "ok", "service": "user-service", "version": "1.0.0", "timestamp": time.time()}

@app.post("/auth/register")
async def register(req: RegisterRequest):
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (req.email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="邮箱已注册")
    user_id = str(uuid.uuid4())
    now = time.time()
    conn.execute("""INSERT INTO users (id, email, password_hash, name, plan, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'free', 'active', ?, ?)""",
        (user_id, req.email, hash_password(req.password), req.name, now, now))
    conn.commit()
    # 自动创建一个默认API Key
    api_key_raw, key_hash, key_prefix = generate_api_key()
    conn.execute("""INSERT INTO api_keys (id, user_id, name, key_hash, key_prefix, status, created_at)
        VALUES (?, ?, 'default', ?, ?, 'active', ?)""",
        (str(uuid.uuid4()), user_id, key_hash, key_prefix, now))
    conn.commit()
    conn.close()
    token = create_jwt(user_id, req.email)
    return {
        "status": "success",
        "message": "注册成功",
        "token": token,
        "user": {"id": user_id, "email": req.email, "name": req.name, "plan": "free"},
        "api_key": api_key_raw,
        "api_key_prefix": key_prefix
    }

@app.post("/auth/login")
async def login(req: LoginRequest):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (req.email,)).fetchone()
    if not user or not verify_password(req.password, user["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if user["status"] != "active":
        conn.close()
        raise HTTPException(status_code=403, detail="账号已被禁用")
    now = time.time()
    conn.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (now, now, user["id"]))
    conn.commit()
    conn.close()
    token = create_jwt(user["id"], user["email"])
    return {
        "status": "success",
        "message": "登录成功",
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"], "plan": user["plan"]}
    }

@app.get("/user/me")
async def get_me(user: dict = Depends(get_current_user)):
    conn = get_db()
    # 获取API Key数量
    key_count = conn.execute("SELECT COUNT(*) as cnt FROM api_keys WHERE user_id = ? AND status = 'active'", (user["id"],)).fetchone()["cnt"]
    # 获取本月用量
    month_start = time.time() - 30 * 24 * 3600
    usage = conn.execute("""SELECT COALESCE(SUM(total_tokens),0) as total_tokens, COALESCE(SUM(requests),0) as requests
        FROM usage WHERE user_id = ? AND created_at > ?""", (user["id"], month_start)).fetchone()
    conn.close()
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "plan": user["plan"],
        "plan_info": PLANS.get(user["plan"], PLANS["free"]),
        "status": user["status"],
        "created_at": user["created_at"],
        "last_login_at": user["last_login_at"],
        "api_key_count": key_count,
        "monthly_usage": {"total_tokens": usage["total_tokens"], "requests": usage["requests"]}
    }

@app.get("/user/api-keys")
async def list_api_keys(user: dict = Depends(get_current_user)):
    conn = get_db()
    keys = conn.execute("""SELECT id, name, key_prefix, status, created_at, last_used_at
        FROM api_keys WHERE user_id = ? ORDER BY created_at DESC""", (user["id"],)).fetchall()
    conn.close()
    return {"api_keys": [dict(k) for k in keys]}

@app.post("/user/api-keys")
async def create_api_key(req: CreateApiKeyRequest, user: dict = Depends(get_current_user)):
    conn = get_db()
    # 检查数量限制
    count = conn.execute("SELECT COUNT(*) as cnt FROM api_keys WHERE user_id = ? AND status = 'active'", (user["id"],)).fetchone()["cnt"]
    limit = PLANS.get(user["plan"], PLANS["free"])["limits"]["api_keys"]
    if count >= limit:
        conn.close()
        raise HTTPException(status_code=400, detail=f"API Key数量已达上限（{limit}个），请升级套餐")
    api_key_raw, key_hash, key_prefix = generate_api_key()
    now = time.time()
    key_id = str(uuid.uuid4())
    conn.execute("""INSERT INTO api_keys (id, user_id, name, key_hash, key_prefix, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'active', ?)""", (key_id, user["id"], req.name, key_hash, key_prefix, now))
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "message": "API Key创建成功",
        "id": key_id,
        "name": req.name,
        "api_key": api_key_raw,
        "key_prefix": key_prefix,
        "warning": "请立即保存此API Key，关闭后将无法再次查看完整密钥"
    }

@app.delete("/user/api-keys/{key_id}")
async def delete_api_key(key_id: str, user: dict = Depends(get_current_user)):
    conn = get_db()
    result = conn.execute("UPDATE api_keys SET status = 'revoked' WHERE id = ? AND user_id = ?", (key_id, user["id"]))
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="API Key不存在")
    return {"status": "success", "message": "API Key已吊销"}

@app.get("/user/usage")
async def get_usage(user: dict = Depends(get_current_user), days: int = 30):
    conn = get_db()
    since = time.time() - days * 24 * 3600
    # 按天统计
    daily = conn.execute("""SELECT DATE(created_at, 'unixepoch', 'localtime') as date,
        COALESCE(SUM(total_tokens),0) as tokens, COALESCE(SUM(requests),0) as requests
        FROM usage WHERE user_id = ? AND created_at > ?
        GROUP BY DATE(created_at, 'unixepoch', 'localtime') ORDER BY date DESC LIMIT ?""",
        (user["id"], since, days)).fetchall()
    # 按模型统计
    by_model = conn.execute("""SELECT model, COALESCE(SUM(total_tokens),0) as tokens, COALESCE(SUM(requests),0) as requests
        FROM usage WHERE user_id = ? AND created_at > ? GROUP BY model ORDER BY tokens DESC""",
        (user["id"], since)).fetchall()
    # 总计
    total = conn.execute("""SELECT COALESCE(SUM(total_tokens),0) as tokens, COALESCE(SUM(requests),0) as requests
        FROM usage WHERE user_id = ? AND created_at > ?""", (user["id"], since)).fetchone()
    conn.close()
    return {
        "period_days": days,
        "total": dict(total),
        "daily": [dict(d) for d in daily],
        "by_model": [dict(m) for m in by_model]
    }

@app.get("/plans")
async def list_plans():
    return {"plans": PLANS}

# ============ 内部API（API网关调用） ============

@app.post("/internal/verify-api-key")
async def verify_api_key(req: dict):
    """供API网关调用验证API Key"""
    api_key = req.get("api_key", "")
    if not api_key:
        raise HTTPException(status_code=401, detail="未提供API Key")
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    conn = get_db()
    key_row = conn.execute("SELECT * FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
    if not key_row:
        conn.close()
        raise HTTPException(status_code=401, detail="无效的API Key")
    if key_row["status"] != "active":
        conn.close()
        raise HTTPException(status_code=403, detail="API Key已被吊销")
    user = conn.execute("SELECT * FROM users WHERE id = ?", (key_row["user_id"],)).fetchone()
    if not user or user["status"] != "active":
        conn.close()
        raise HTTPException(status_code=403, detail="用户账号不可用")
    # 更新最后使用时间
    now = time.time()
    conn.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (now, key_row["id"]))
    conn.commit()
    conn.close()
    return {
        "valid": True,
        "user_id": user["id"],
        "email": user["email"],
        "plan": user["plan"],
        "api_key_id": key_row["id"],
        "api_key_name": key_row["name"],
        "limits": PLANS.get(user["plan"], PLANS["free"])["limits"]
    }

@app.post("/internal/record-usage")
async def record_usage(req: UsageRecordRequest):
    """供API网关调用记录用量"""
    key_hash = hashlib.sha256(req.api_key.encode()).hexdigest()
    conn = get_db()
    key_row = conn.execute("SELECT id, user_id FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
    if not key_row:
        conn.close()
        raise HTTPException(status_code=401, detail="无效的API Key")
    now = time.time()
    usage_id = str(uuid.uuid4())
    conn.execute("""INSERT INTO usage (id, user_id, api_key_id, model, endpoint, prompt_tokens, completion_tokens, total_tokens, requests, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
        (usage_id, key_row["user_id"], key_row["id"], req.model, req.endpoint,
         req.prompt_tokens, req.completion_tokens, req.total_tokens, now))
    conn.commit()
    conn.close()
    return {"status": "success", "usage_id": usage_id}

# ============ 启动 ============
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  火斗云智AIOS 用户系统服务启动")
    print(f"  端口: 8090")
    print(f"  数据库: {DB_PATH}")
    print(f"  JWT有效期: {JWT_EXPIRE_HOURS}小时")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8090, log_level="info")
