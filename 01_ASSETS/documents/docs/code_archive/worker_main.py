#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一自治体系｜本地宿主机Worker主程序
整合：三态指令路由 + M9资产账本 + 增量Merkle树 + 原子写入 + SQLite索引
     + Append-only审计日志 + 资产元数据嵌入 + 能量态采集 + 网关真值上报 + 双向对账
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""
import os
import sys
import json
import time
import hashlib
import sqlite3
import subprocess
import requests
import psutil
from pathlib import Path
from datetime import datetime

# ===================== 全局配置 =====================
BASE_DIR = Path(__file__).parent.parent.resolve()
ASSET_DIR = BASE_DIR / "assets"
TMP_DIR = BASE_DIR / "tmp_workspace"
LEDGER_DIR = BASE_DIR / "ledger"
DB_DIR = BASE_DIR / "db"
SNAPSHOT_DIR = BASE_DIR / "snapshot"
LOG_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

# 统一数据库连接模块（自动设置PRAGMA: WAL/NORMAL/20MB缓存）
sys.path.insert(0, str(BASE_DIR))
from comm.db_utils import get_connection

# 配置加载器（支持热加载）
sys.path.insert(0, str(CONFIG_DIR))
try:
    from config_loader import config as _config
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False

def _cfg(key, default):
    if _CONFIG_AVAILABLE:
        return _config.get(key, default)
    return default

ASSETS_LEDGER = LEDGER_DIR / "assets_ledger.jsonl"
MERKLE_TREE_FILE = LEDGER_DIR / "merkle_tree.json"
AUDIT_LOG = LEDGER_DIR / "audit_log.jsonl"
ASSET_INDEX_DB = DB_DIR / "asset_index.db"
PID_FILE = BASE_DIR / "worker.pid"

GATEWAY_BASE = _cfg("gateway.base_url", "https://www.huodouai.com")
GATEWAY_TRUTH_URL = GATEWAY_BASE + _cfg("gateway.truth_report_endpoint", "/api/report/truth")
GATEWAY_STATUS_URL = GATEWAY_BASE + _cfg("gateway.status_endpoint", "/api/report/status")
DID = _cfg("system.did", "DID-BR-000002")
TRACE_ID = _cfg("system.trace", "Ω₀⊂⊙∞⊂Ω")

WORKER_LOOP_INTERVAL = _cfg("worker.loop_interval", 30)
STEADY_DOMAIN_THRESHOLD = _cfg("worker.steady_domain_threshold", 0.15)

# 能量态阈值（从配置加载，支持热加载）
DEFAULT_ENERGY_LIMIT = {
    "cpu_max": _cfg("worker.energy_cpu_critical", 95.0),
    "mem_max": _cfg("worker.energy_mem_critical", 95.0),
    "disk_max": _cfg("worker.energy_disk_critical", 95.0),
}


# ===================== 工具函数 =====================
def ensure_dirs():
    """确保所有目录存在"""
    for d in [ASSET_DIR, TMP_DIR, LEDGER_DIR, DB_DIR, SNAPSHOT_DIR, LOG_DIR, CONFIG_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def log(msg, level="INFO"):
    """日志输出"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    log_file = LOG_DIR / f"worker_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def calc_sha256(file_path: Path) -> str:
    """计算文件SHA256哈希"""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_str(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ===================== 模块1：SQLite资产索引 =====================
def init_db():
    """初始化SQLite资产索引库"""
    conn = get_connection(ASSET_INDEX_DB)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT UNIQUE,
        sha256 TEXT,
        size_bytes INTEGER,
        create_ts REAL,
        asset_type TEXT,
        task_id TEXT,
        merkle_node TEXT,
        archived INTEGER DEFAULT 0
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL,
        event_type TEXT,
        payload TEXT,
        did TEXT
    )''')
    conn.commit()
    conn.close()
    log("SQLite资产索引库初始化完成")


def insert_index_record(filepath, sha256, size, ts, asset_type, task_id, merkle_node):
    """插入资产索引记录"""
    conn = get_connection(ASSET_INDEX_DB)
    cur = conn.cursor()
    cur.execute('''INSERT OR IGNORE INTO assets
    (filepath,sha256,size_bytes,create_ts,asset_type,task_id,merkle_node,archived)
    VALUES (?,?,?,?,?,?,?,1)''', (filepath, sha256, size, ts, asset_type, task_id, merkle_node))
    conn.commit()
    conn.close()


def query_assets(limit=100):
    """查询资产列表"""
    conn = get_connection(ASSET_INDEX_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM assets ORDER BY create_ts DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ===================== 模块2：M9资产账本 + 增量Merkle树 =====================
def append_asset_ledger(filepath, sha256, asset_type, task_id, merkle_node_hash):
    """追加资产账本记录（仅追加）"""
    entry = {
        "ts": time.time(),
        "filepath": filepath,
        "sha256": sha256,
        "asset_type": asset_type,
        "task_id": task_id,
        "merkle_node": merkle_node_hash,
        "did_source": DID,
        "trace": TRACE_ID
    }
    with open(ASSETS_LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    log(f"资产账本追加: {Path(filepath).name}")


def build_merkle_root(leaf_hashes):
    """构建Merkle根哈希"""
    nodes = leaf_hashes.copy()
    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])
        new_nodes = []
        for i in range(0, len(nodes), 2):
            combined = sha256_str(nodes[i] + nodes[i + 1])
            new_nodes.append(combined)
        nodes = new_nodes
    return nodes[0] if nodes else ""


def update_merkle_tree(new_leaf_hash):
    """更新增量Merkle树"""
    tree = {"leaves": [], "root": ""}
    if MERKLE_TREE_FILE.exists():
        try:
            tree = json.loads(MERKLE_TREE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    tree["leaves"].append(new_leaf_hash)
    tree["root"] = build_merkle_root(tree["leaves"])
    tree["updated_at"] = time.time()
    MERKLE_TREE_FILE.write_text(json.dumps(tree, indent=2, ensure_ascii=False), encoding="utf-8")
    return tree["root"]


def get_current_merkle_root():
    """获取当前Merkle根"""
    if MERKLE_TREE_FILE.exists():
        try:
            tree = json.loads(MERKLE_TREE_FILE.read_text(encoding="utf-8"))
            return tree.get("root", "")
        except Exception:
            pass
    return ""


# ===================== 模块3：原子写入封装 =====================
def atomic_save_asset(src_tmp: Path, target: Path):
    """原子写入：临时文件校验通过后rename，失败自动清理tmp"""
    if not src_tmp.exists():
        return {"ok": False, "msg": "临时文件不存在"}

    # 视频完整性校验
    if target.suffix.lower() in [".mp4", ".mov", ".avi", ".mkv"]:
        ret = subprocess.run(["ffprobe", "-v", "error", str(src_tmp)],
                             capture_output=True, timeout=30)
        if ret.returncode != 0:
            src_tmp.unlink(missing_ok=True)
            return {"ok": False, "msg": "视频文件损坏，已丢弃临时文件"}

    # 图片完整性校验
    if target.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
        try:
            from PIL import Image
            with Image.open(src_tmp) as img:
                img.verify()
        except Exception as e:
            src_tmp.unlink(missing_ok=True)
            return {"ok": False, "msg": f"图片损坏: {e}，已丢弃临时文件"}

    # 原子重命名
    try:
        src_tmp.replace(target)
        return {"ok": True, "msg": "原子写入完成"}
    except Exception as e:
        return {"ok": False, "msg": f"rename失败: {e}"}


# ===================== 模块4：资产元数据嵌入 =====================
def embed_image_exif(img_path: Path, merkle_root: str, task_id: str):
    """图片EXIF写入溯源信息"""
    try:
        from PIL import Image
        img = Image.open(img_path)
        exif_data = img.getexif()
        exif_data[0x9286] = f"DID={DID}|TRACE={TRACE_ID}|MERKLE={merkle_root}|TASK={task_id}"
        img.save(img_path, exif=exif_data)
        log(f"图片EXIF溯源嵌入: {img_path.name}")
        return True
    except Exception as e:
        log(f"EXIF嵌入失败: {e}", "WARN")
        return False


def embed_video_meta(video_path: Path, merkle_root: str, task_id: str):
    """视频元数据写入溯源信息"""
    try:
        tmp_meta = video_path.with_suffix(".meta.tmp" + video_path.suffix)
        comment = f"DID={DID}|TRACE={TRACE_ID}|MERKLE={merkle_root}|TASK={task_id}"
        cmd = ["ffmpeg", "-y", "-i", str(video_path),
               "-metadata", f"comment={comment}",
               "-c", "copy", str(tmp_meta)]
        subprocess.run(cmd, capture_output=True, timeout=60)
        if tmp_meta.exists():
            tmp_meta.replace(video_path)
            log(f"视频元数据溯源嵌入: {video_path.name}")
            return True
        return False
    except Exception as e:
        log(f"视频元数据嵌入失败: {e}", "WARN")
        return False


# ===================== 模块5：Append-only审计日志 =====================
def write_audit_log(event_type: str, payload: dict):
    """写入审计日志（仅追加）"""
    log_entry = {
        "ts": time.time(),
        "event": event_type,
        "payload": payload,
        "did": DID,
        "trace": TRACE_ID
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    # 同时写入SQLite审计表
    try:
        conn = get_connection(ASSET_INDEX_DB)
        cur = conn.cursor()
        cur.execute("INSERT INTO audit_events (ts,event_type,payload,did) VALUES (?,?,?,?)",
                    (time.time(), event_type, json.dumps(payload, ensure_ascii=False), DID))
        conn.commit()
        conn.close()
    except Exception:
        pass


# ===================== 模块6：能量态资源采集 =====================
def get_host_energy_state():
    """采集宿主机能量态指标"""
    cpu_pct = psutil.cpu_percent(interval=0.2)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(BASE_DIR))
    return {
        "timestamp": time.time(),
        "cpu_usage": cpu_pct,
        "mem_total_gb": round(mem.total / (1024 ** 3), 2),
        "mem_used_gb": round(mem.used / (1024 ** 3), 2),
        "mem_usage_pct": mem.percent,
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),
        "disk_usage_pct": disk.percent
    }


def energy_state_check(energy_data, energy_rule=None):
    """能量态阈值裁决"""
    rule = energy_rule or DEFAULT_ENERGY_LIMIT
    if energy_data["cpu_usage"] > rule.get("cpu_max", 85):
        return {"allow": False, "fuse_level": "S1", "reason": f"CPU超出配额: {energy_data['cpu_usage']}%"}
    if energy_data["mem_usage_pct"] > rule.get("mem_max", 90):
        return {"allow": False, "fuse_level": "S1", "reason": f"内存超出配额: {energy_data['mem_usage_pct']}%"}
    if energy_data["disk_usage_pct"] > rule.get("disk_max", 92):
        return {"allow": False, "fuse_level": "S1", "reason": f"磁盘超出配额: {energy_data['disk_usage_pct']}%"}
    return {"allow": True, "fuse_level": "NONE", "reason": "资源校验通过"}


# ===================== 模块7：记忆网关真值上报 =====================
def report_truth(truth_key, truth_value, truth_type="protocol", confidence=0.98):
    """上报真值到记忆网关"""
    payload = {
        "truth_key": truth_key,
        "truth_value": truth_value,
        "source_node": DID,
        "confidence": confidence,
        "truth_type": truth_type
    }
    try:
        resp = requests.post(GATEWAY_TRUTH_URL, json=payload, timeout=15)
        data = resp.json()
        success = data.get("written_to_gateway", False) or data.get("success", False)
        if success:
            log(f"真值上报成功: {truth_key}")
        else:
            log(f"真值上报失败: {truth_key} | {data}", "WARN")
        return data
    except Exception as e:
        log(f"真值上报异常: {e}", "ERROR")
        return {"error": str(e)}


def report_heartbeat():
    """上报Worker心跳（携带能量态快照）"""
    energy_snapshot = get_host_energy_state()
    asset_count = len(query_assets(limit=10000))
    payload = {
        "worker_status": "active",
        "asset_count": asset_count,
        "merkle_root": get_current_merkle_root(),
        "energy_snapshot": energy_snapshot,
        "pid": os.getpid()
    }
    return report_truth(
        "WORKER.LOCAL_HOST.HEARTBEAT",
        json.dumps(payload, ensure_ascii=False),
        "protocol", 0.98
    )


# ===================== 模块8：本地账本↔网关双向对账 =====================
def cross_verify_ledger():
    """本地账本与记忆网关双向对账"""
    local_root = get_current_merkle_root()
    if not local_root:
        return {"match": True, "fuse": "NONE", "msg": "本地账本为空，跳过对账"}

    # 上报本地根，网关返回已存储根进行比对
    result = report_truth(
        "LEDGER.MERKLE.ROOT.CROSS_VERIFY",
        json.dumps({"local_root": local_root, "action": "VERIFY"}, ensure_ascii=False),
        "protocol", 0.99
    )

    gw_root = result.get("merkle_root", "")
    if gw_root and gw_root != local_root:
        write_audit_log("RISK.LEDGER_MISMATCH", {
            "local_root": local_root,
            "gw_root": gw_root
        })
        log(f"⚠️ 账本对账不一致! 本地: {local_root[:16]}... 网关: {gw_root[:16]}...", "WARN")
        return {"match": False, "fuse": "S2", "local_root": local_root, "gw_root": gw_root}

    log(f"✅ 账本对账一致: {local_root[:16]}...")
    return {"match": True, "fuse": "NONE", "local_root": local_root}


# ===================== 三态指令路由 =====================
def tri_state_router(cmd_package):
    """三态路由：逻辑态校验 → 信息态解析 → 能量态分配"""
    logic_state = cmd_package.get("logic_state", {})
    info_state = cmd_package.get("info_state", {})
    energy_state = cmd_package.get("energy_state", {})

    # 逻辑态校验
    if not logic_state.get("allow_execute", False):
        return {"status": "deny", "reason": "逻辑态裁决不通过，熔断拦截"}

    # 能量态校验
    energy_data = get_host_energy_state()
    energy_check = energy_state_check(energy_data, energy_state)
    if not energy_check["allow"]:
        return {
            "status": "deny",
            "fuse_level": energy_check["fuse_level"],
            "reason": energy_check["reason"],
            "energy_snapshot": energy_data
        }

    # 信息态动作分发
    action = info_state.get("action")
    if action == "SCAN_ASSET":
        return {"status": "run", "task": "scan_asset"}
    elif action == "RUN_PIPELINE":
        return {"status": "run", "task": "trigger_pipeline", "params": info_state}
    elif action == "RELOAD_META_RULE":
        return {"status": "run", "task": "reload_rule"}
    elif action == "CROSS_VERIFY":
        return {"status": "run", "task": "cross_verify"}
    elif action == "STOP_WORKER":
        return {"status": "run", "task": "grace_shutdown"}
    else:
        return {"status": "unknown_action", "action": action}


def execute_task(task_result):
    """执行路由后的任务"""
    task = task_result.get("task")
    if task == "scan_asset":
        assets = scan_local_assets()
        write_audit_log("TASK.SCAN_ASSET", {"count": len(assets)})
        return {"ok": True, "asset_count": len(assets)}
    elif task == "trigger_pipeline":
        return run_asset_pipeline(task_result.get("params", {}))
    elif task == "cross_verify":
        return cross_verify_ledger()
    elif task == "grace_shutdown":
        log("收到优雅停止指令")
        return {"ok": True, "shutdown": True}
    return {"ok": False, "msg": f"未知任务: {task}"}


# ===================== 资产流水线 =====================
def scan_local_assets():
    """扫描本地资产目录"""
    asset_list = []
    for f in ASSET_DIR.rglob("*"):
        if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov"]:
            stat = f.stat()
            asset_list.append({
                "filepath": str(f),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "filename": f.name
            })
    return asset_list


def run_asset_pipeline(params):
    """执行资产入库全流水线"""
    task_id = params.get("task_id", f"TASK-{int(time.time())}")
    src_path = params.get("asset_path", "")
    target_name = params.get("target_name", Path(src_path).name if src_path else "")

    if not src_path or not Path(src_path).exists():
        return {"ok": False, "msg": "源文件不存在"}

    src = Path(src_path)
    target = ASSET_DIR / target_name

    # 1. 原子写入
    log(f"[流水线1/7] 原子写入: {src.name}")
    atomic_result = atomic_save_asset(src, target)
    if not atomic_result["ok"]:
        write_audit_log("PIPELINE.FAIL_ATOMIC", {"file": src.name, "reason": atomic_result["msg"]})
        return {"ok": False, "stage": "atomic_write", "msg": atomic_result["msg"]}

    # 2. 计算SHA256
    log("[流水线2/7] 计算SHA256哈希")
    file_hash = calc_sha256(target)

    # 3. 更新Merkle树
    log("[流水线3/7] 更新增量Merkle树")
    merkle_root = update_merkle_tree(file_hash)

    # 4. 元数据嵌入
    log("[流水线4/7] 嵌入溯源元数据")
    if target.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
        embed_image_exif(target, merkle_root, task_id)
    elif target.suffix.lower() in [".mp4", ".mov"]:
        embed_video_meta(target, merkle_root, task_id)

    # 5. 资产账本追加
    log("[流水线5/7] 追加M9资产账本")
    append_asset_ledger(str(target), file_hash, target.suffix.lower(), task_id, file_hash)

    # 6. SQLite索引入库
    log("[流水线6/7] SQLite资产索引入库")
    stat = target.stat()
    insert_index_record(str(target), file_hash, stat.st_size, time.time(),
                        target.suffix.lower(), task_id, file_hash)

    # 7. 真值上报网关
    log("[流水线7/7] 上报真值到记忆网关")
    report_truth(
        f"ASSET.{file_hash[:16].upper()}",
        json.dumps({
            "filename": target.name,
            "sha256": file_hash,
            "merkle_root": merkle_root,
            "task_id": task_id,
            "size": stat.st_size,
            "asset_type": target.suffix.lower()
        }, ensure_ascii=False),
        "creative", 0.99
    )

    write_audit_log("PIPELINE.SUCCESS", {
        "file": target.name,
        "sha256": file_hash,
        "merkle_root": merkle_root,
        "task_id": task_id
    })

    log(f"✅ 资产流水线完成: {target.name} | Merkle: {merkle_root[:16]}...")
    return {
        "ok": True,
        "file": str(target),
        "sha256": file_hash,
        "merkle_root": merkle_root,
        "task_id": task_id
    }


# ===================== Worker主循环 =====================
class LocalHostWorker:
    def __init__(self):
        self.running = True
        self.last_asset_hash = ""
        self.loop_count = 0
        # 初始化三态驱动引擎（完整逻辑态/信息态/能量态裁决）
        try:
            sys.path.insert(0, str(BASE_DIR / "worker"))
            from tri_state_engine import get_engine
            self.tri_state_engine = get_engine()
            log("三态驱动引擎已初始化（完整裁决链路）")
        except ImportError as e:
            log(f"三态驱动引擎初始化失败，降级为基础路由: {e}", "WARN")
            self.tri_state_engine = None

    def check_pending_commands(self):
        """检查待执行指令（从配置目录读取指令文件）"""
        cmd_file = CONFIG_DIR / "pending_cmd.json"
        if cmd_file.exists():
            try:
                cmd = json.loads(cmd_file.read_text(encoding="utf-8"))
                cmd_file.unlink()  # 消费后删除
                log(f"收到三态指令: {cmd.get('info_state',{}).get('action')}")
                return cmd
            except Exception as e:
                log(f"指令文件解析失败: {e}", "ERROR")
        return None

    def main_loop(self):
        """Worker常驻主循环"""
        log("=" * 60)
        log("元极恒一本地宿主机Worker启动")
        log(f"部署路径: {BASE_DIR}")
        log(f"PID: {os.getpid()}")
        log(f"溯源: {TRACE_ID} | {DID}")
        log("=" * 60)

        # 启动时执行一次对账
        cross_verify_ledger()

        while self.running:
            self.loop_count += 1
            log(f"--- 主循环第 {self.loop_count} 轮 ---")

            # 1. 心跳上报（每轮）
            heartbeat = report_heartbeat()
            log(f"心跳上报: {'成功' if (heartbeat.get('written_to_gateway') or heartbeat.get('success')) else '失败'}")

            # 2. 检查待执行指令
            cmd = self.check_pending_commands()
            if cmd:
                # 使用三态驱动引擎（完整裁决链路）或降级为基础路由
                if self.tri_state_engine:
                    route_result = self.tri_state_engine.route(cmd, executor=execute_task)
                    final_status = route_result.get("final_status", "unknown")
                    logic_decision = route_result["stages"]["logic_state"]["decision"]
                    energy_fuse = route_result["stages"]["energy_state"]["fuse_level"]
                    log(f"三态引擎裁决: {final_status} (逻辑:{logic_decision}, 能量:{energy_fuse})")
                    exec_result = route_result.get("stages", {}).get("execution", {}).get("result", {})
                    if exec_result.get("shutdown"):
                        self.running = False
                        break
                else:
                    route_result = tri_state_router(cmd)
                    log(f"三态路由结果: {route_result['status']}")
                    if route_result["status"] == "run":
                        exec_result = execute_task(route_result)
                        log(f"任务执行结果: {exec_result}")
                        if exec_result.get("shutdown"):
                            self.running = False
                            break
                    else:
                        exec_result = None
                write_audit_log("CMD.EXECUTED", {
                    "action": cmd.get("info_state", {}).get("action"),
                    "route": route_result if self.tri_state_engine else {"status": route_result["status"]},
                    "result": exec_result,
                    "engine": "tri_state_engine" if self.tri_state_engine else "basic_router",
                })

            # 3. 资产变更检测
            assets = scan_local_assets()
            current_hash = sha256_str(json.dumps(sorted([a["filepath"] for a in assets])))
            if current_hash != self.last_asset_hash and self.last_asset_hash != "":
                log(f"检测到资产目录变更 (当前{len(assets)}个文件)")
                write_audit_log("ASSET.CHANGE_DETECTED", {"count": len(assets)})
            self.last_asset_hash = current_hash

            # 4. 每10轮执行一次双向对账
            if self.loop_count % 10 == 0:
                cross_verify_ledger()

            # 5. 清理临时目录过期文件
            self.cleanup_tmp()

            time.sleep(WORKER_LOOP_INTERVAL)

        log("Worker已停止")

    def cleanup_tmp(self):
        """清理临时目录中超过1小时的文件"""
        cutoff = time.time() - 3600
        cleaned = 0
        for f in TMP_DIR.rglob("*"):
            if f.is_file() and f.stat().st_mtime < cutoff:
                try:
                    f.unlink()
                    cleaned += 1
                except Exception:
                    pass
        if cleaned > 0:
            log(f"清理临时文件: {cleaned}个")


# ===================== 入口 =====================
def main():
    ensure_dirs()
    init_db()

    # 写入PID文件
    PID_FILE.write_text(str(os.getpid()))

    worker = LocalHostWorker()
    try:
        worker.main_loop()
    except KeyboardInterrupt:
        log("收到中断信号，优雅退出")
        worker.running = False
    except Exception as e:
        log(f"Worker异常: {e}", "ERROR")
        write_audit_log("WORKER.CRASH", {"error": str(e)})
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()


if __name__ == "__main__":
    main()
