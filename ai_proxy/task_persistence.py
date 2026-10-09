"""任务持久化模块：IMAGE_TASKS/VIDEO_TASKS SQLite存储，重启不丢失"""
import sqlite3, json, time, os

DB_PATH = "/opt/ZONGYUAN-ROOT/ai_proxy/tasks.db"

def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS image_tasks (
        task_id TEXT PRIMARY KEY,
        status TEXT,
        prompt TEXT,
        provider TEXT,
        image_url TEXT,
        created_at REAL,
        error TEXT,
        extra TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS video_tasks (
        task_id TEXT PRIMARY KEY,
        status TEXT,
        prompt TEXT,
        provider TEXT,
        model TEXT,
        video_url TEXT,
        created_at REAL,
        progress INTEGER,
        error TEXT,
        extra TEXT
    )''')
    conn.commit()
    conn.close()

def save_image_task(task_id, task_data):
    """保存图片任务"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO image_tasks 
            (task_id, status, prompt, provider, image_url, created_at, error, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (task_id, task_data.get('status',''), task_data.get('prompt',''),
             task_data.get('provider',''), task_data.get('image_url',''),
             task_data.get('created_at', time.time()), task_data.get('error',''),
             json.dumps({k:v for k,v in task_data.items() if k not in ['status','prompt','provider','image_url','created_at','error']})))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

def get_image_task(task_id):
    """获取图片任务"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM image_tasks WHERE task_id=?", (task_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "task_id": row[0], "status": row[1], "prompt": row[2],
                "provider": row[3], "image_url": row[4], "created_at": row[5],
                "error": row[6], **json.loads(row[7] or '{}')
            }
    except:
        pass
    return None

def save_video_task(task_id, task_data):
    """保存视频任务"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO video_tasks 
            (task_id, status, prompt, provider, model, video_url, created_at, progress, error, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (task_id, task_data.get('status',''), task_data.get('prompt',''),
             task_data.get('provider',''), task_data.get('model',''),
             task_data.get('video_url',''), task_data.get('created_at', time.time()),
             task_data.get('progress', 0), task_data.get('error',''),
             json.dumps({k:v for k,v in task_data.items() if k not in ['status','prompt','provider','model','video_url','created_at','progress','error']})))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

def get_video_task(task_id):
    """获取视频任务"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM video_tasks WHERE task_id=?", (task_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "task_id": row[0], "status": row[1], "prompt": row[2],
                "provider": row[3], "model": row[4], "video_url": row[5],
                "created_at": row[6], "progress": row[7], "error": row[8],
                **json.loads(row[9] or '{}')
            }
    except:
        pass
    return None

def load_all_tasks():
    """启动时加载所有未完成任务到内存"""
    images = {}
    videos = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT task_id FROM image_tasks WHERE status IN ('processing','submitted')")
        for row in c.fetchall():
            t = get_image_task(row[0])
            if t: images[row[0]] = t
        c.execute("SELECT task_id FROM video_tasks WHERE status IN ('processing','submitted')")
        for row in c.fetchall():
            t = get_video_task(row[0])
            if t: videos[row[0]] = t
        conn.close()
    except:
        pass
    return images, videos

# 初始化
init_db()
