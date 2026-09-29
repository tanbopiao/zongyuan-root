"""
短剧生产后台Worker V2 - 基于算子组架构
调用统一注册表OperatorRegistry，消除重复代码
遵循元极恒一体系：算子即太极，标准化优先
"""
import sqlite3, time, os, uuid, threading, sys

sys.path.insert(0, "/opt/ZONGYUAN-ROOT/ai_proxy")
from operators import get_registry

DB_PATH = "/opt/ZONGYUAN-ROOT/ai_proxy/production_tasks.db"

# 超时配置（秒）
TIMEOUT = {
    "script": 90, "storyboard": 90, "image": 180,
    "video": 600, "tts": 60, "merge": 180
}
MAX_RETRIES = 2
WORKER_COUNT = 1  # V2.0.0: Worker并发数，当前2GB内存默认1，升级4核8GB后改为2

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS production_tasks (
        task_id TEXT PRIMARY KEY, template_id TEXT, template_name TEXT,
        device_id TEXT, status TEXT, current_stage TEXT, progress INTEGER,
        script TEXT, storyboard TEXT, keyframe_url TEXT, video_url TEXT,
        final_url TEXT, error TEXT, created_at REAL, updated_at REAL)""")
    conn.commit(); conn.close()

def create_task(template_id, template_name, device_id):
    task_id = "prod-" + uuid.uuid4().hex[:12]
    now = time.time()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO production_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (task_id, template_id, template_name, device_id, "pending", "初始化", 0,
         "", "", "", "", "", "", now, now))
    conn.commit(); conn.close()
    return task_id

def update_task(task_id, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    sets = ", ".join([k + "=?" for k in kwargs])
    vals = list(kwargs.values()) + [time.time(), task_id]
    conn.execute("UPDATE production_tasks SET " + sets + ", updated_at=? WHERE task_id=?", vals)
    conn.commit(); conn.close()

def get_task(task_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT * FROM production_tasks WHERE task_id=?", (task_id,)).fetchone()
    conn.close()
    if not row: return None
    cols = ["task_id","template_id","template_name","device_id","status","current_stage",
            "progress","script","storyboard","keyframe_url","video_url","final_url",
            "error","created_at","updated_at"]
    return dict(zip(cols, row))

def list_tasks(device_id, limit=20):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT task_id,template_name,status,current_stage,progress,final_url,created_at FROM production_tasks WHERE device_id=? ORDER BY created_at DESC LIMIT ?", (device_id, limit)).fetchall()
    conn.close()
    return [{"task_id":r[0],"template_name":r[1],"status":r[2],"stage":r[3],"progress":r[4],"video_url":r[5],"created_at":r[6]} for r in rows]

def run_production(task_id):
    """6阶段生产流程 - 全部通过算子注册表调用"""
    task = get_task(task_id)
    if not task: return
    tn, did, tid = task["template_name"], task["device_id"], task["template_id"]
    reg = get_registry()
    print("[Worker] 开始生产(算子组模式): %s | %s" % (task_id, tn))
    
    try:
        # 阶段1：剧本生成（算子 T1）
        update_task(task_id, status="running", current_stage="剧本生成", progress=8)
        script = ""
        for attempt in range(MAX_RETRIES + 1):
            r = reg.call("text", "generate_script", template_name=tn, timeout=TIMEOUT["script"])
            if r.get("success") and r.get("script") and len(r["script"]) > 50:
                script = r["script"]; break
            print("[Worker] 剧本生成重试 %d/%d" % (attempt+1, MAX_RETRIES))
            time.sleep(2)
        if not script:
            script = tn + "：纯东方神女觉醒，月光下执剑而立，守护昆仑洞天。"
        update_task(task_id, script=script, progress=18)
        # 自建RAG剧本增强（默认启用，完全自主可控）
        try:
            rag_result = reg.call("local_rag", "enhance_script", template_name=tn, base_script=script)
            if rag_result.get("success") and rag_result.get("enhanced_by") == "local_rag":
                script = rag_result.get("script", script)
                print("[Worker] 自建RAG剧本增强成功, 知识命中:", rag_result.get("knowledge_used"))
                update_task(task_id, script=script)
        except Exception as e:
            print("[Worker] RAG增强跳过:", e)
        update_task(task_id, progress=20)
        
        # 阶段2：分镜设计（算子 T2）
        update_task(task_id, current_stage="分镜设计", progress=30)
        r = reg.call("text", "generate_storyboard", script=script, timeout=TIMEOUT["storyboard"])
        sb = r.get("storyboard", "") if r.get("success") else ""
        update_task(task_id, storyboard=sb, progress=40)
        
        # 阶段3：关键帧生成（算子 I1）
        update_task(task_id, current_stage="关键帧生成", progress=50)
        kf_prompt = "纯乌黑长发东方神女，" + tn + "，青黑长裙，月光下，零雄性化，零西方铠甲，电影级画质"
        r = reg.call("image", "generate_keyframe", prompt=kf_prompt, timeout=TIMEOUT["image"])
        kf = r.get("image_url") if r.get("success") else None
        update_task(task_id, keyframe_url=kf or "", progress=65)
        
        # 阶段4：视频生成（算子 V2→V1 多级降级）
        update_task(task_id, current_stage="视频生成", progress=70)
        vp = tn + "，纯东方神女，纯乌黑长发，青黑长裙，流畅运镜，电影级画质，9:16竖屏，零雄性化"
        vu = None
        if kf:
            r = reg.call("video", "image_to_video", prompt=vp, image_url=kf, timeout=TIMEOUT["video"])
            vu = r.get("video_url") if r.get("success") else None
            if not vu: print("[Worker] 图生视频失败，降级文生视频")
        if not vu:
            r = reg.call("video", "text_to_video", prompt=vp, timeout=TIMEOUT["video"])
            vu = r.get("video_url") if r.get("success") else None
        if not vu:
            r = reg.call("video", "text_to_video", prompt=tn + "，东方神女，电影级画质，9:16", timeout=TIMEOUT["video"])
            vu = r.get("video_url") if r.get("success") else None
        update_task(task_id, video_url=vu or "", progress=85)
        
        # 阶段5：TTS配音（算子 A1）
        fu = vu
        if vu and script:
            update_task(task_id, current_stage="配音合成", progress=90)
            r = reg.call("text", "extract_narration", script=script, max_len=200)
            narration = r.get("narration", "") if r.get("success") else script[:200]
            r = reg.call("audio", "text_to_speech", text=narration, timeout=TIMEOUT["tts"])
            au = r.get("audio_url") if r.get("success") else None
            # 阶段6：音画合并（算子 V3）
            if au:
                r = reg.call("video", "merge_audio", video_url=vu, audio_url=au, timeout=TIMEOUT["merge"])
                if r.get("success"): fu = r.get("output_url")
        
        # 完成：作品保存（算子 S1）
        update_task(task_id, status="completed", current_stage="完成", progress=100, final_url=fu or "")
        if fu:
            reg.call("storage", "save_work", device_id=did, title=tn, video_url=fu, template=tid)
        print("[Worker] 生产完成: %s | %s" % (task_id, fu or "无视频"))
        # 自学习闭环：任务完成后触发进化学习（异步不阻塞）
        try:
            import subprocess
            subprocess.Popen(["python3", "/opt/ZONGYUAN-ROOT/learning_engine/self_evolution_loop.py"],
                           stdout=open("/opt/ZONGYUAN-ROOT/logs/auto_learning.log", "a"),
                           stderr=subprocess.STDOUT)
            print("[Worker] 自学习闭环已触发")
        except Exception as e:
            print("[Worker] 自学习触发跳过:", e)
        
    except Exception as e:
        update_task(task_id, status="failed", error=str(e)[:200])
        print("[Worker] 生产失败: %s | %s" % (task_id, e))

_worker_running = False
def start_worker():
    global _worker_running
    if _worker_running: return
    _worker_running = True
    def loop():
        while True:
            try:
                # 超时清理：running超过30分钟的任务标记为failed
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("UPDATE production_tasks SET status=\"failed\", error=\"任务超时30分钟\" WHERE status=\"running\" AND created_at < datetime(\"now\", \"-30 minutes\")")
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print("[Worker] 超时清理异常:", e)
                # 取pending任务
                conn = sqlite3.connect(DB_PATH)
                row = conn.execute("SELECT task_id FROM production_tasks WHERE status=\"pending\" ORDER BY created_at LIMIT 1").fetchone()
                conn.close()
                if row:
                    try:
                        run_production(row[0])
                    except Exception as e:
                        print("[Worker] 任务 %s 失败: %s" % (row[0], e))
                        try:
                            conn = sqlite3.connect(DB_PATH)
                            conn.execute("UPDATE production_tasks SET status=\"failed\", error=? WHERE task_id=?", (str(e)[:200], row[0]))
                            conn.commit()
                            conn.close()
                        except Exception:
                            pass
                else:
                    time.sleep(3)
            except Exception as e:
                print("[Worker] 循环异常(自动恢复):", e)
                time.sleep(5)
    threading.Thread(target=loop, daemon=True).start()
    print("[Worker] 后台生产Worker已启动（异常隔离+超时清理）")

init_db()


def start_multi_workers(count=WORKER_COUNT):
    """V2.0.0: 启动多个Worker并发生产（服务器升级后启用）"""
    threads = []
    for i in range(count):
        t = threading.Thread(target=start_worker, daemon=True, name="ProductionWorker-%d" % i)
        t.start()
        threads.append(t)
        print("[WorkerHub] 启动Worker %d/%d" % (i+1, count))
    return threads
