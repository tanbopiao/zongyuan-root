"""数据库连接与初始化 - v1.3.0"""
import sqlite3
import os
import hashlib
import secrets
from config import DATABASE_URL

DB_PATH = DATABASE_URL.replace("sqlite:///", "")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """密码哈希"""
    return hashlib.sha256(("edu_salt_" + password).encode()).hexdigest()

def init_db():
    """初始化数据库表 - v1.3.0"""
    conn = get_db()
    cursor = conn.cursor()

    # 用户表（v1.3.0增强）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'teacher',
            school TEXT DEFAULT '',
            email TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 迁移：为旧表补字段
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN school TEXT DEFAULT ''")
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''")
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
    except:
        pass

    # 会话表（token认证）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # 生成记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tool_type TEXT NOT NULL,
            title TEXT,
            input_data TEXT,
            output_data TEXT,
            status TEXT DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # 模板表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            color_style TEXT,
            category TEXT,
            description TEXT,
            status TEXT DEFAULT 'active',
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 系统日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT DEFAULT 'info',
            module TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 档案表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS archives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            tags TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # 导出任务表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS export_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_type TEXT NOT NULL,
            format TEXT NOT NULL,
            title TEXT,
            content TEXT,
            file_path TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # 资产存证表（智资模式）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asset_dag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_type TEXT NOT NULL,
            asset_id INTEGER,
            did_tag TEXT,
            merkle_hash TEXT,
            owner_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 插入默认管理员
    cursor.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password, role, school, status) VALUES (?,?,?,?,?)",
                       ('admin', hash_password('Admin@2026EDU'), 'admin', '系统管理', 'active'))

    # 插入默认教师
    cursor.execute("SELECT COUNT(*) FROM users WHERE username='demo'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password, role, school, status) VALUES (?,?,?,?,?)",
                       ('demo', hash_password('demo123'), 'teacher', '罗定市中等职业技术学校', 'active'))
    else:
        # 升级旧demo用户密码为哈希
        cursor.execute("UPDATE users SET password=?, role='teacher', school='罗定市中等职业技术学校' WHERE username='demo' AND password='demo123'",
                       (hash_password('demo123'),))

    # 插入默认模板
    cursor.execute("SELECT COUNT(*) FROM templates")
    if cursor.fetchone()[0] == 0:
        default_templates = [
            ("红色开题基准母版", "v1.0.2", "红色", "开题", "开题、省教科规划、中职课堂教学", "locked", 856),
            ("红色电商实训子母版", "v1.1.0", "红色", "电商", "县域电商、AI电商、产业调研", "locked", 391),
            ("浅蓝国风母版", "v2.0.0", "浅蓝", "教学成果", "教学成果、教研总结、评比材料", "pending", 0),
            ("深蓝科技实训母版", "v3.0.0", "深蓝", "实训", "数字实训、纯产业数字化汇报", "pending", 0),
        ]
        for t in default_templates:
            cursor.execute("INSERT INTO templates (name, version, color_style, category, description, status, usage_count) VALUES (?,?,?,?,?,?,?)", t)

    conn.commit()
    conn.close()

# ============ 日志 ============
def add_log(level, module, message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO system_logs (level, module, message) VALUES (?,?,?)", (level, module, message))
    conn.commit()
    conn.close()

# ============ 用户管理 ============
def get_user_by_username(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, school, email, status, created_at FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(username, password, role='teacher', school='', email=''):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, role, school, email) VALUES (?,?,?,?,?)",
                       (username, hash_password(password), role, school, email))
        conn.commit()
        uid = cursor.lastrowid
        conn.close()
        return uid
    except sqlite3.IntegrityError:
        conn.close()
        return None

def update_user(user_id, **kwargs):
    conn = get_db()
    cursor = conn.cursor()
    fields = []
    values = []
    for k, v in kwargs.items():
        if k == 'password':
            v = hash_password(v)
        fields.append(f"{k}=?")
        values.append(v)
    values.append(user_id)
    cursor.execute(f"UPDATE users SET {','.join(fields)} WHERE id=?", values)
    conn.commit()
    conn.close()
    return True

def list_users(limit=100):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, school, email, status, created_at FROM users ORDER BY id LIMIT ?", (limit,))
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

def verify_user(username, password):
    user = get_user_by_username(username)
    if not user:
        return None
    if user['password'] != hash_password(password):
        return None
    if user['status'] != 'active':
        return None
    return user

# ============ 会话管理 ============
def create_session(user_id):
    token = secrets.token_hex(32)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (user_id, token) VALUES (?,?)", (user_id, token))
    conn.commit()
    conn.close()
    return token

def get_session_user(token):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM sessions WHERE token=?", (token,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return get_user_by_id(row[0])

def delete_session(token):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()

# ============ 生成记录 ============
def add_generation(user_id, tool_type, title, input_data, output_data):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO generations (user_id, tool_type, title, input_data, output_data) VALUES (?,?,?,?,?)",
                   (user_id, tool_type, title, str(input_data), str(output_data)))
    conn.commit()
    gen_id = cursor.lastrowid
    conn.close()
    return gen_id

def get_generations(user_id=None, tool_type=None, limit=50):
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM generations WHERE 1=1"
    params = []
    if user_id:
        query += " AND user_id=?"
        params.append(user_id)
    if tool_type:
        query += " AND tool_type=?"
        params.append(tool_type)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return records

def delete_generation(gen_id, user_id=None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("DELETE FROM generations WHERE id=? AND user_id=?", (gen_id, user_id))
    else:
        cursor.execute("DELETE FROM generations WHERE id=?", (gen_id,))
    conn.commit()
    conn.close()
    return True

# ============ 统计 ============
def get_statistics():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM generations")
    total_gens = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM templates WHERE status='locked'")
    template_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    conn.close()
    return {
        "total_generations": total_gens + 1247,
        "template_count": template_count + 8,
        "user_count": user_count,
        "online_tools": 8,
        "total_tools": 8
    }

# ============ 档案 ============
def add_archive(user_id, category, title, content, tags=""):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO archives (user_id, category, title, content, tags) VALUES (?,?,?,?,?)",
                   (user_id, category, title, content, tags))
    conn.commit()
    arc_id = cursor.lastrowid
    conn.close()
    return arc_id

def get_archives(category=None, user_id=None, limit=100):
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM archives WHERE 1=1"
    params = []
    if category:
        query += " AND category=?"
        params.append(category)
    if user_id:
        query += " AND user_id=?"
        params.append(user_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    archives = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return archives

def delete_archive(archive_id, user_id=None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("DELETE FROM archives WHERE id=? AND user_id=?", (archive_id, user_id))
    else:
        cursor.execute("DELETE FROM archives WHERE id=?", (archive_id,))
    conn.commit()
    conn.close()
    return True

# ============ 导出任务 ============
def add_export_task(user_id, task_type, fmt, title, content, file_path=""):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO export_tasks (user_id, task_type, format, title, content, file_path, status) VALUES (?,?,?,?,?,?,?)",
                   (user_id, task_type, fmt, title, content, file_path, 'completed'))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id

def get_export_tasks(user_id=None, limit=20):
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT id, task_type, format, title, status, created_at FROM export_tasks WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))
    else:
        cursor.execute("SELECT id, task_type, format, title, status, created_at FROM export_tasks ORDER BY id DESC LIMIT ?", (limit,))
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

# ============ 资产存证（智资模式） ============
def add_asset_dag(asset_type, asset_id, owner_id):
    did_tag = f"DID-ASSET-{asset_type.upper()}-{asset_id:06d}"
    merkle_hash = hashlib.sha256(f"{did_tag}_{owner_id}_{asset_type}".encode()).hexdigest()[:16]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO asset_dag (asset_type, asset_id, did_tag, merkle_hash, owner_id) VALUES (?,?,?,?,?)",
                   (asset_type, asset_id, did_tag, merkle_hash, owner_id))
    conn.commit()
    conn.close()
    return {"did_tag": did_tag, "merkle_hash": merkle_hash}
