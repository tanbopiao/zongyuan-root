"""存储算子组 - 3算子：作品保存、任务持久化、内核锁档"""
import sqlite3, os, time, json

class StorageOperators:
    def __init__(self, config):
        self.config = config
        self.works_db = config.get("works_db", "/opt/ZONGYUAN-ROOT/timeseries/works.db")
        self.tasks_db = config.get("tasks_db", "/opt/ZONGYUAN-ROOT/ai_proxy/tasks.db")
        self.kernel_path = config.get("kernel_path", "/opt/ZONGYUAN-ROOT/kernel.json")
    
    def save_work(self, device_id, title, video_url, template="", timeout_retries=3):
        """算子S1：作品保存（带重试）"""
        for attempt in range(timeout_retries):
            try:
                os.makedirs(os.path.dirname(self.works_db), exist_ok=True)
                conn = sqlite3.connect(self.works_db)
                conn.execute("""CREATE TABLE IF NOT EXISTS works (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT, title TEXT, video_url TEXT,
                    template TEXT, created_at TEXT)""")
                conn.execute("INSERT INTO works VALUES (NULL,?,?,?,?,?)",
                    (device_id, title, video_url, template, time.strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit(); conn.close()
                return {"success": True, "title": title, "operator": "S1_save_work"}
            except Exception as e:
                if attempt < timeout_retries - 1:
                    time.sleep(2)
                else:
                    return {"success": False, "error": str(e), "operator": "S1_save_work"}
        return {"success": False, "error": "重试耗尽", "operator": "S1_save_work"}
    
    def persist_task(self, task_type, task_id, data):
        """算子S2：任务持久化"""
        try:
            conn = sqlite3.connect(self.tasks_db)
            if task_type == "image":
                conn.execute("""CREATE TABLE IF NOT EXISTS image_tasks (
                    task_id TEXT PRIMARY KEY, status TEXT, data TEXT, created_at REAL)""")
                conn.execute("INSERT OR REPLACE INTO image_tasks VALUES (?,?,?,?)",
                    (task_id, data.get("status","pending"), json.dumps(data), time.time()))
            elif task_type == "video":
                conn.execute("""CREATE TABLE IF NOT EXISTS video_tasks (
                    task_id TEXT PRIMARY KEY, status TEXT, provider TEXT, data TEXT, created_at REAL)""")
                conn.execute("INSERT OR REPLACE INTO video_tasks VALUES (?,?,?,?,?)",
                    (task_id, data.get("status","pending"), data.get("provider",""), json.dumps(data), time.time()))
            conn.commit(); conn.close()
            return {"success": True, "task_id": task_id, "operator": "S2_persist"}
        except Exception as e:
            return {"success": False, "error": str(e), "operator": "S2_persist"}
    
    def lock_kernel(self, snapshot_id, desc, module=""):
        """算子S3：内核锁档"""
        try:
            with open(self.kernel_path) as f:
                k = json.load(f)
            k.setdefault("snapshots", []).append({
                "id": snapshot_id, "desc": desc, "module": module,
                "timestamp": time.time(), "type": "operator_lock"
            })
            k["snapshot_count"] = len(k["snapshots"])
            with open(self.kernel_path, "w") as f:
                json.dump(k, f, ensure_ascii=False, indent=2)
            return {"success": True, "snapshot_id": snapshot_id, "total": k["snapshot_count"], "operator": "S3_lock"}
        except Exception as e:
            return {"success": False, "error": str(e), "operator": "S3_lock"}
