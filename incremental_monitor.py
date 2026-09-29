#!/usr/bin/env python3
"""
全域云资产增量监控锁档引擎 V2.2
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | 协议: ZONGYUAN-ROOT
V2.0优化: 五阶段流水线 | 双轮删除确认 | 扫描置信度 | 资产健康评分
          结构化告警 | 统计账本 | 临时快照门控 | 业务活跃视图
V2.1优化: 递归深度扩展至15层 | eFuse按M1-M9元类分区 | 快照三级分层
V2.2优化: 内容级SHA256真值锁档 | content_hash精确变更检测 | 重复资产自动关联
功能: 前置预检 → 节点心跳 → 云资产扫描 → 增量真值校正 → 临时快照 → 内核固化门控
"""
import os, sys, json, hashlib, subprocess, datetime, time, platform, shutil, glob, tempfile, errno

# ==================== P0修复: 文件锁 + 原子写入 ====================
LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".incremental_monitor.lock")

def acquire_lock():
    """获取排他文件锁，防止并发执行。含陈旧锁自动检测与清理。"""
    # 陈旧锁检测：锁文件存在但对应进程已不存在 → 自动清理
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                lock_content = f.read()
            old_pid = int(lock_content.split('PID=')[1].split()[0])
            try:
                os.kill(old_pid, 0)
                # 进程存在，检查fcntl锁
            except OSError:
                # 进程不存在，陈旧锁，自动清理
                print(f"[LOCK] 检测到陈旧锁 (PID={old_pid}已不存在)，自动清理。")
                os.remove(LOCK_FILE)
        except:
            # 无法解析锁文件，视为陈旧
            try: os.remove(LOCK_FILE)
            except: pass
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR)
        try:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.ftruncate(fd, 0)
            os.write(fd, f"PID={os.getpid()} TIME={datetime.datetime.utcnow().isoformat()}Z".encode())
            os.fsync(fd)
            return fd
        except ImportError:
            # Windows fallback: PID文件锁
            try:
                if os.path.exists(LOCK_FILE):
                    with open(LOCK_FILE, 'r') as f:
                        old_pid = int(f.read().split('PID=')[1].split()[0])
                    try: os.kill(old_pid, 0)
                    except OSError: pass
                    else:
                        print(f"[LOCK] 另一实例正在运行 (PID={old_pid})，退出。")
                        sys.exit(1)
            except: pass
            with open(LOCK_FILE, 'w') as f:
                f.write(f"PID={os.getpid()}")
            return None
    except OSError as e:
        if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            print("[LOCK] 获取文件锁失败，另一实例正在运行，退出。")
            sys.exit(1)
        raise

def release_lock(fd):
    """释放文件锁。"""
    if fd is None:
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except: pass
        return
    try:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    except: pass
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except: pass

def atomic_write_json(path, data):
    """原子写入JSON：写临时文件→fsync→os.rename替换，防止并发写入损坏。"""
    dir_name = os.path.dirname(path) or '.'
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp', prefix=os.path.basename(path) + '.')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, path)
    except:
        try: os.remove(tmp_path)
        except: pass
        raise

# ==================== 常量配置 ====================
WORKDIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(WORKDIR, "UNIFIED_GLOBAL_LOCK_MANIFEST.json")
REPORT_DIR = os.path.join(WORKDIR, "inc_reports")
HASH_CHAIN_PATH = os.path.join(WORKDIR, "hash_chain.json")
EFUSE_REGISTRY = os.path.join(WORKDIR, "efuse_registry.json")
STAT_LEDGER_PATH = os.path.join(WORKDIR, "asset_stat_ledger.json")
EVENT_ALARM_PATH = os.path.join(WORKDIR, "event_alarm.json")
TEMP_SNAP_DIR = os.path.join(WORKDIR, "temp_snapshots")
BUSINESS_VIEW_PATH = os.path.join(WORKDIR, "business_active_view.json")
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
PROTOCOL = "ZONGYUAN-ROOT"
LARK_CLI = "lark-cli"
GENESIS_HASH = "0" * 64
# 门控阈值
SCAN_CONFIDENCE_THRESHOLD = 75  # 扫描置信度固化阈值
DISK_WARN_THRESHOLD = 80  # 磁盘告警阈值%
MEM_WARN_THRESHOLD = 85  # 内存告警阈值%
LARGE_DELETION_THRESHOLD = 80  # 大规模删除告警阈值（单次删除数）
FLUCTUATION_RATIO_WARN = 0.3  # 扫描波动占比告警阈值
# V2.1: 元类定义 M1-M9
META_CLASSES = {
    "M1": {"name": "算法架构层", "keywords": ["engine", "algorithm", "arch", "pipeline", "core", "os", "系统", "引擎", "架构", "算法"]},
    "M2": {"name": "数据模型层", "keywords": ["schema", "model", "data", "结构", "数据", "模型"]},
    "M3": {"name": "接口协议层", "keywords": ["api", "protocol", "interface", "接口", "协议"]},
    "M4": {"name": "理论体系层", "keywords": ["whitepaper", "theory", "philosophy", "白皮书", "理论", "哲学", "体系"]},
    "M5": {"name": "应用产线层", "keywords": ["product", "app", "application", "产线", "应用", "产品"]},
    "M6": {"name": "运维治理层", "keywords": ["ops", "monitor", "governance", "运维", "治理", "监控"]},
    "M7": {"name": "安全合规层", "keywords": ["security", "compliance", "audit", "安全", "合规", "审计"]},
    "M8": {"name": "业务逻辑层", "keywords": ["business", "workflow", "process", "业务", "流程"]},
    "M9": {"name": "元秩序层", "keywords": ["meta", "order", "root", "axiom", "元", "秩序", "根", "公理", "锁档", "归档", "hash", "efuse"]},
}
# V2.1: eFuse按元类分配区间（每类预留10000位）
EFUSE_CLASS_RANGES = {
    "M1": (1, 10000), "M2": (10001, 20000), "M3": (20001, 30000),
    "M4": (30001, 40000), "M5": (40001, 50000), "M6": (50001, 60000),
    "M7": (60001, 70000), "M8": (70001, 80000), "M9": (80001, 90000),
}
# V2.1: 快照三级分层阈值
SNAPSHOT_HOT_LIMIT = 20   # 热层：最近20轮常驻
SNAPSHOT_WARM_LIMIT = 200 # 温层：21-200轮本地磁盘
SNAPSHOT_COLD_DIR = "cold_archive"  # 冷层：>200轮外移归档
# V2.2: 内容级真值锁档配置
CONTENT_HASH_ENABLED = True        # 启用内容级SHA256哈希
MAX_CONTENT_HASH_PER_ROUND = 30    # 每轮最多处理30个内容哈希（避免超时）
MAX_FILE_SIZE_FOR_HASH = 50 * 1024 * 1024  # 超过50MB跳过内容哈希
CONTENT_HASH_TEMP_DIR = "content_hash_temp"  # 临时下载目录
# 支持内容哈希的文件类型
CONTENT_HASH_TYPES = {
    "upload": ["pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "txt", "md", "csv", "json", "zip"],
    "online_doc": ["docx", "doc"],  # 在线文档导出为markdown计算哈希
    "online_sheet": ["sheet"],       # 表格导出为csv计算哈希
}

os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(TEMP_SNAP_DIR, exist_ok=True)

# ==================== 工具函数 ====================
def sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def now_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def run_cli(args, timeout=60):
    try:
        r = subprocess.run([LARK_CLI] + args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, "", str(e)

def parse_cli_json(stdout: str):
    lines = stdout.strip().split("\n")
    json_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("{"):
            json_start = i
            break
    try:
        return json.loads("\n".join(lines[json_start:]))
    except:
        return None

# ==================== 阶段0: 前置预检 ====================
def preflight_check():
    """前置预检：lark-cli登录态、磁盘水位、内存阈值。返回(是否通过, 告警列表)"""
    alarms = []
    passed = True

    # 1. lark-cli登录态检测 - 用实际轻量命令验证，而非可能不存在的auth命令
    auth_ok = False
    # 尝试1: auth status
    rc, out, err = run_cli(["auth", "status"], timeout=15)
    if rc == 0:
        data = parse_cli_json(out)
        if data and data.get("ok"):
            auth_ok = True
    # 尝试2: whoami
    if not auth_ok:
        rc2, out2, err2 = run_cli(["whoami"], timeout=15)
        if rc2 == 0 and out2.strip():
            auth_ok = True
    # 尝试3: 实际轻量扫描命令（最可靠）
    if not auth_ok:
        rc3, out3, err3 = run_cli(["drive", "files", "list", "--page-size", "1"], timeout=30)
        if rc3 == 0:
            data3 = parse_cli_json(out3)
            if data3 and data3.get("ok"):
                auth_ok = True
    if not auth_ok:
        alarms.append({
            "level": "WARN", "category": "auth",
            "event_id": "AUTH_UNVERIFIED",
            "desc": "lark-cli登录态未能通过预检验证（命令可能不支持），将在扫描阶段实际验证",
            "suggest": "若扫描失败请执行 lark-cli auth login 重新登录"
        })
        # 不阻断流程，扫描阶段会自己检测

    # 2. 磁盘水位
    try:
        disk = shutil.disk_usage(WORKDIR)
        disk_percent = round(disk.used / disk.total * 100, 1) if disk.total else 0
        if disk_percent >= DISK_WARN_THRESHOLD:
            alarms.append({
                "level": "WARN", "category": "resource",
                "event_id": "DISK_HIGH",
                "desc": f"磁盘使用率{disk_percent}%超过阈值{DISK_WARN_THRESHOLD}%",
                "suggest": "清理冷归档快照或扩展磁盘空间"
            })
    except:
        pass

    # 3. 内存水位
    try:
        with open("/proc/meminfo") as f:
            mi = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    mi[parts[0].rstrip(":")] = int(parts[1])
            mem_total = mi.get("MemTotal", 1)
            mem_available = mi.get("MemAvailable", 0)
            mem_percent = round((mem_total - mem_available) / mem_total * 100, 1)
            if mem_percent >= MEM_WARN_THRESHOLD:
                alarms.append({
                    "level": "WARN", "category": "resource",
                    "event_id": "MEM_HIGH",
                    "desc": f"内存使用率{mem_percent}%超过阈值{MEM_WARN_THRESHOLD}%",
                    "suggest": "释放内存或检查异常进程"
                })
    except:
        pass

    return passed, alarms

# ==================== 阶段1: 节点心跳上报 ====================
def node_heartbeat():
    try:
        cpu_load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
        cpu_count = os.cpu_count() or 1
        cpu_percent = round(cpu_load / cpu_count * 100, 1)
        mem_total = mem_used = mem_percent = 0
        try:
            with open("/proc/meminfo") as f:
                mi = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        mi[parts[0].rstrip(":")] = int(parts[1])
                mem_total = mi.get("MemTotal", 0)
                mem_available = mi.get("MemAvailable", 0)
                mem_used = mem_total - mem_available
                mem_percent = round(mem_used / mem_total * 100, 1) if mem_total else 0
        except:
            pass
        disk = shutil.disk_usage(WORKDIR)
        disk_total = disk.total
        disk_used = disk.used
        disk_percent = round(disk_used / disk_total * 100, 1) if disk_total else 0
        hb = {
            "node_id": "ZONGYUAN-CLOUD-001",
            "status": "ACTIVE",
            "platform": platform.platform(),
            "cpu_cores": cpu_count,
            "cpu_load_1m": round(cpu_load, 2),
            "cpu_percent": cpu_percent,
            "mem_total_mb": round(mem_total / 1024, 0),
            "mem_used_mb": round(mem_used / 1024, 0),
            "mem_percent": mem_percent,
            "disk_total_gb": round(disk_total / 1024**3, 1),
            "disk_used_gb": round(disk_used / 1024**3, 1),
            "disk_percent": disk_percent,
            "last_heartbeat": now_iso(),
            "did": DID,
            "trace": TRACE
        }
        return hb
    except Exception as e:
        return {"node_id": "ZONGYUAN-CLOUD-001", "status": "UNKNOWN", "error": str(e), "last_heartbeat": now_iso()}

# ==================== 阶段2: 云资产扫描 ====================
def scan_drive():
    assets = []
    visited_folders = set()
    def _scan_folder(folder_token=None, depth=0):
        if depth > 12:  # V2.2: 从15调整为12层，平衡覆盖度和扫描性能
            return
        args = ["drive", "files", "list", "--page-size", "50", "--page-all", "--page-limit", "0"]
        if folder_token:
            args.extend(["--folder-token", folder_token])
        rc, out, err = run_cli(args, timeout=120)
        data = parse_cli_json(out)
        if not data or not data.get("ok"):
            return
        files = data.get("data", {}).get("files", [])
        for f in files:
            token = f.get("token")
            if not token:
                continue
            assets.append({
                "asset_id": token,
                "asset_type": "drive:" + f.get("type", "unknown"),
                "name": f.get("name", ""),
                "mtime": f.get("modified_time", "0"),
                "ctime": f.get("created_time", "0"),
                "owner": f.get("owner_id", ""),
                "url": f.get("url", ""),
                "parent_token": folder_token or f.get("parent_token", ""),
                "depth": depth
            })
            if f.get("type") == "folder" and token not in visited_folders:
                visited_folders.add(token)
                _scan_folder(token, depth + 1)
    _scan_folder(None, 0)
    return assets

def scan_wiki():
    assets = []
    rc, out, err = run_cli(["wiki", "+space-list"], timeout=30)
    data = parse_cli_json(out)
    spaces = []
    if data and data.get("ok"):
        spaces = data.get("data", {}).get("spaces", [])
    for space in spaces:
        sid = space.get("space_id")
        sname = space.get("name", "")
        def walk_nodes(parent_token=None, depth=0):
            if depth > 15:  # V2.1: Wiki递归深度从10扩展至15层
                return
            args = ["wiki", "+node-list", "--space-id", sid, "--page-size", "50", "--page-all", "--page-limit", "0"]
            if parent_token:
                args.extend(["--parent-node-token", parent_token])
            rc2, out2, _ = run_cli(args, timeout=60)
            d2 = parse_cli_json(out2)
            if not d2 or not d2.get("ok"):
                return
            nodes = d2.get("data", {}).get("nodes", [])
            for n in nodes:
                nt = n.get("node_token")
                assets.append({
                    "asset_id": "wiki:" + nt,
                    "asset_type": "wiki:" + n.get("obj_type", "unknown"),
                    "name": n.get("title", ""),
                    "mtime": n.get("obj_edit_time", "0"),
                    "ctime": n.get("obj_create_time", "0"),
                    "space_id": sid,
                    "space_name": sname,
                    "obj_token": n.get("obj_token", ""),
                    "has_child": n.get("has_child", False),
                    "depth": depth
                })
                if n.get("has_child"):
                    walk_nodes(nt, depth + 1)
        walk_nodes()
    return assets

def scan_all_assets():
    print("[SCAN] 扫描Drive云盘...")
    drive_assets = scan_drive()
    print(f"  Drive资产: {len(drive_assets)}")
    print("[SCAN] 扫描Wiki知识库...")
    wiki_assets = scan_wiki()
    print(f"  Wiki资产: {len(wiki_assets)}")
    base_assets = [a for a in drive_assets if a["asset_type"] == "drive:bitable"]
    print(f"  Base(bitable)资产: {len(base_assets)}")
    all_assets = drive_assets + wiki_assets
    return all_assets, drive_assets, wiki_assets, base_assets

# ==================== 阶段3: 哈希链与锁档 ====================
def load_hash_chain():
    if os.path.exists(HASH_CHAIN_PATH):
        with open(HASH_CHAIN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"chain": [], "root_hash": GENESIS_HASH, "length": 0}

def save_hash_chain(chain):
    atomic_write_json(HASH_CHAIN_PATH, chain)

def append_chain(chain, entry):
    prev_hash = chain["root_hash"]
    entry["prev_hash"] = prev_hash
    entry["seq"] = chain["length"]
    entry["timestamp"] = now_iso()
    entry_str = json.dumps(entry, sort_keys=True, ensure_ascii=False)
    entry_hash = sha256(prev_hash + entry_str)
    entry["entry_hash"] = entry_hash
    chain["chain"].append(entry)
    chain["root_hash"] = entry_hash
    chain["length"] += 1
    return entry_hash

def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "version": "2.0",
        "did": DID,
        "trace": TRACE,
        "protocol": PROTOCOL,
        "created_at": now_iso(),
        "assets": {},
        "root_hash": GENESIS_HASH,
        "efuse_counter": 0
    }

def save_manifest(m):
    m["updated_at"] = now_iso()
    atomic_write_json(MANIFEST_PATH, m)

def load_efuse():
    if os.path.exists(EFUSE_REGISTRY):
        with open(EFUSE_REGISTRY, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"fuses": [], "counter": 0}

def save_efuse(e):
    atomic_write_json(EFUSE_REGISTRY, e)

def get_content_hash(asset):
    """V2.2: 获取文件内容SHA256哈希
    支持：上传文件(download) + 在线文档(export to markdown)
    大文件(>50MB)跳过，返回CONTENT_HASH_SKIPPED_LARGE_FILE
    下载/导出失败返回CONTENT_HASH_UNAVAILABLE
    """
    if not CONTENT_HASH_ENABLED:
        return "CONTENT_HASH_DISABLED", 0, "disabled"
    asset_type = asset.get("asset_type", "")
    token = asset.get("asset_id", "")
    name = asset.get("name", "")
    temp_dir = os.path.join(WORKDIR, CONTENT_HASH_TEMP_DIR)
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = os.path.join(temp_dir, f"{token}_{int(time.time())}.tmp")

    try:
        # 判断文件类型，选择下载或导出
        is_online_doc = asset_type.startswith("drive:docx") or asset_type.startswith("drive:doc") or asset_type.startswith("wiki:")
        is_online_sheet = asset_type.startswith("drive:sheet")
        is_upload_file = asset_type.startswith("drive:") and not is_online_doc and not is_online_sheet

        if is_online_doc:
            # 在线文档：导出为markdown（注意：lark-cli要求相对路径，不能用绝对路径）
            rc, out, err = run_cli([
                "drive", "+export",
                "--token", token,
                "--doc-type", "docx" if "docx" in asset_type else "doc",
                "--file-extension", "markdown",
                "--output-dir", CONTENT_HASH_TEMP_DIR,
                "--file-name", f"{token}.md",
                "--overwrite"
            ], timeout=120)
            exported = os.path.join(temp_dir, f"{token}.md")
            if not os.path.exists(exported):
                return "CONTENT_HASH_UNAVAILABLE", 0, "export_failed"
            temp_file = exported
            content_type = "online_doc_markdown"

        elif is_online_sheet:
            # 在线表格：导出为csv（第一个子表）
            rc, out, err = run_cli([
                "drive", "+export",
                "--token", token,
                "--doc-type", "sheet",
                "--file-extension", "csv",
                "--output-dir", CONTENT_HASH_TEMP_DIR,
                "--file-name", f"{token}.csv",
                "--overwrite"
            ], timeout=120)
            exported = os.path.join(temp_dir, f"{token}.csv")
            if not os.path.exists(exported):
                return "CONTENT_HASH_UNAVAILABLE", 0, "export_failed"
            temp_file = exported
            content_type = "online_sheet_csv"

        elif is_upload_file:
            # 上传文件：直接下载（用相对路径避免unsafe path）
            temp_file_rel = os.path.join(CONTENT_HASH_TEMP_DIR, f"{token}_{int(time.time())}.tmp")
            rc, out, err = run_cli([
                "drive", "+download",
                "--file-token", token,
                "--output", temp_file_rel,
                "--overwrite"
            ], timeout=120)
            temp_file = os.path.join(WORKDIR, temp_file_rel)
            if not os.path.exists(temp_file):
                return "CONTENT_HASH_UNAVAILABLE", 0, "download_failed"
            content_type = "uploaded_file"

        else:
            return "CONTENT_HASH_UNSUPPORTED_TYPE", 0, asset_type

        # 检查文件大小
        file_size = os.path.getsize(temp_file)
        if file_size > MAX_FILE_SIZE_FOR_HASH:
            os.remove(temp_file)
            return "CONTENT_HASH_SKIPPED_LARGE_FILE", file_size, "large_file_skipped"

        # 计算SHA256
        h = hashlib.sha256()
        with open(temp_file, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        content_hash = h.hexdigest()

        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)

        return content_hash, file_size, content_type

    except Exception as e:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        return "CONTENT_HASH_ERROR", 0, f"error:{str(e)[:100]}"

def classify_meta_class(asset):
    """V2.1: 根据资产名称和类型自动分配元类M1-M9"""
    name = asset.get("name", "").lower()
    asset_type = asset.get("asset_type", "").lower()
    text = name + " " + asset_type
    best_class = "M8"
    best_score = 0
    for mc, info in META_CLASSES.items():
        score = sum(1 for kw in info["keywords"] if kw.lower() in text)
        if score > best_score:
            best_score = score
            best_class = mc
    if asset_type.startswith("wiki:") and best_score == 0:
        best_class = "M4"
    if "bitable" in asset_type and best_score == 0:
        best_class = "M2"
    return best_class

def generate_efuse(efuse_registry, asset_id, asset_hash, meta_class="M8"):
    """V2.1: 按元类M1-M9分配独立熔断位区间"""
    if "class_counters" not in efuse_registry:
        efuse_registry["class_counters"] = {mc: 0 for mc in META_CLASSES}
    if "class_ranges" not in efuse_registry:
        efuse_registry["class_ranges"] = EFUSE_CLASS_RANGES
    class_start, class_end = EFUSE_CLASS_RANGES.get(meta_class, (70001, 80000))
    efuse_registry["class_counters"][meta_class] = efuse_registry["class_counters"].get(meta_class, 0) + 1
    class_seq = efuse_registry["class_counters"][meta_class]
    fuse_num = class_start + class_seq - 1
    efuse_registry["counter"] = max(efuse_registry.get("counter", 0), fuse_num)
    fuse_id = f"EFUSE-{fuse_num:06d}"
    fuse = {
        "fuse_id": fuse_id,
        "asset_id": asset_id,
        "asset_hash": asset_hash,
        "meta_class": meta_class,
        "meta_class_name": META_CLASSES[meta_class]["name"],
        "blown_at": now_iso(),
        "did": DID,
        "status": "BLOWN"
    }
    efuse_registry["fuses"].append(fuse)
    return fuse_id

def lock_asset(chain, manifest, efuse_registry, asset, change_type, trust_level="TRUE", prev_snap_ref="", content_hash_counter=None):
    """V2.2: 内容级SHA256真值锁档 + 自动元类分类 + eFuse按元类分区
    content_hash_counter: 全局计数器，每轮最多处理MAX_CONTENT_HASH_PER_ROUND个
    """
    aid = asset["asset_id"]
    meta_class = classify_meta_class(asset)
    asset["meta_class"] = meta_class
    asset["meta_class_name"] = META_CLASSES[meta_class]["name"]

    # V2.2: 内容级SHA256哈希（每轮限量处理）
    content_hash = "LEGACY_NO_CONTENT_HASH"
    content_size = 0
    content_type = "unknown"
    if content_hash_counter is not None and content_hash_counter["count"] < MAX_CONTENT_HASH_PER_ROUND:
        content_hash_counter["count"] += 1
        content_hash, content_size, content_type = get_content_hash(asset)
        content_hash_counter["results"].append({
            "asset_id": aid,
            "name": asset.get("name", ""),
            "content_hash": content_hash,
            "content_size": content_size,
            "content_type": content_type
        })

    asset_content = json.dumps(asset, sort_keys=True, ensure_ascii=False)
    asset_hash = sha256(asset_content)
    fuse_id = generate_efuse(efuse_registry, aid, asset_hash, meta_class)
    entry = {
        "type": change_type,
        "asset_id": aid,
        "asset_type": asset.get("asset_type", ""),
        "name": asset.get("name", ""),
        "asset_hash": asset_hash,
        "content_hash": content_hash,  # V2.2: 内容级哈希
        "content_size": content_size,   # V2.2: 内容大小
        "content_type": content_type,   # V2.2: 内容类型
        "mtime": asset.get("mtime", ""),
        "efuse_id": fuse_id,
        "meta_class": meta_class,
        "event_trust_level": trust_level,
        "prev_snap_ref": prev_snap_ref,
        "did": DID,
        "trace": TRACE
    }
    if change_type == "REV" and aid in manifest["assets"]:
        entry["rev_parent_hash"] = manifest["assets"][aid]["latest_hash"]
    entry_hash = append_chain(chain, entry)
    manifest["assets"][aid] = {
        "asset_type": asset.get("asset_type", ""),
        "name": asset.get("name", ""),
        "meta_class": meta_class,
        "meta_class_name": META_CLASSES[meta_class]["name"],
        "latest_hash": entry_hash,
        "asset_hash": asset_hash,
        "content_hash": content_hash,  # V2.2: 内容级哈希
        "content_size": content_size,   # V2.2: 内容大小
        "content_type": content_type,   # V2.2: 内容类型
        "mtime": asset.get("mtime", ""),
        "efuse_id": fuse_id,
        "locked_at": now_iso(),
        "deleted": False,
        "event_trust_level": trust_level,
        "rev_count": manifest["assets"].get(aid, {}).get("rev_count", 0) + (1 if change_type == "REV" else 0)
    }
    return entry_hash, fuse_id

def flag_deleted(chain, manifest, efuse_registry, asset_id, trust_level="TRUE", prev_snap_ref=""):
    """V2.0: 增加trust_level, prev_snap_ref; 扫描波动不分配eFuse"""
    if asset_id not in manifest["assets"]:
        return None
    entry = {
        "type": "DELETED_FLAGGED",
        "asset_id": asset_id,
        "name": manifest["assets"][asset_id].get("name", ""),
        "event_trust_level": trust_level,
        "prev_snap_ref": prev_snap_ref,
        "did": DID,
        "trace": TRACE
    }
    # 仅真实删除分配eFuse，扫描波动不分配
    if trust_level == "TRUE":
        asset_hash = manifest["assets"][asset_id].get("asset_hash", "")
        fuse_id = generate_efuse(efuse_registry, asset_id, asset_hash)
        entry["efuse_id"] = fuse_id
    entry_hash = append_chain(chain, entry)
    manifest["assets"][asset_id]["deleted"] = True
    manifest["assets"][asset_id]["deleted_at"] = now_iso()
    manifest["assets"][asset_id]["delete_trust_level"] = trust_level
    return entry_hash

# ==================== V2.0新增: 双轮删除确认 ====================
def load_prev_report():
    """读取上一轮增量报告，用于双轮删除确认"""
    reports = sorted(glob.glob(os.path.join(REPORT_DIR, "incremental_report_*.json")))
    if len(reports) >= 2:
        # 倒数第二个是上一轮（最新的是当前正在写的，但还没写）
        # 实际上当前报告还没写，所以最新的就是上一轮
        prev_path = reports[-1]
        try:
            with open(prev_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
    return None

def classify_deletions(deleted_ids, prev_report, manifest):
    """
    双轮删除确认：将删除事件分类
    - TRUE: 上一轮也标记删除（连续两轮消失）→ 真实删除
    - SCAN_FLUCTUATION: 上一轮存在且活跃，本轮消失 → 疑似扫描波动
    - SUSPECT: 无法判定
    返回 {asset_id: trust_level}
    """
    classification = {}
    prev_deleted = set()
    if prev_report:
        # 从上一轮报告中提取已标记删除的资产ID
        prev_manifest_total = prev_report.get("unified_manifest", {}).get("total_assets", 0)
        prev_active = prev_report.get("unified_manifest", {}).get("active_assets", 0)
        # 上一轮删除的资产ID集合（从change_summary推断）
        prev_change = prev_report.get("change_summary", {})
        prev_deleted_count = prev_change.get("deleted_flag_count", 0)
        # 更精确：从上一轮报告的deleted_asset_ids字段（V2.0新增）
        prev_deleted = set(prev_report.get("deleted_asset_ids", []))

    for aid in deleted_ids:
        # 检查是否在统一清单中已经标记为历史删除（deleted=True）
        manifest_assets = manifest.get("assets", {}) if manifest else {}
        asset_record = manifest_assets.get(aid, {})
        if isinstance(asset_record, dict) and asset_record.get("deleted") == True:
            # 历史已删除资产，本轮扫描不出现是正常现象，不参与波动检测
            classification[aid] = "ALREADY_DELETED"
        elif aid in prev_deleted:
            # 连续两轮消失 → 真实删除
            classification[aid] = "TRUE"
        else:
            # 首次消失 → 扫描波动嫌疑
            classification[aid] = "SCAN_FLUCTUATION"
    return classification

# ==================== V2.0新增: 扫描置信度计算 ====================
def calc_scan_confidence(current_total, prev_total, deleted_count, new_count, fluctuation_count, api_errors=0):
    """
    计算扫描置信度(0-100)
    因素：总量稳定性、删除比例、波动占比、API错误率
    """
    score = 100.0
    # 1. 总量波动惩罚（变化超过10%扣分）
    if prev_total > 0:
        change_ratio = abs(current_total - prev_total) / prev_total
        if change_ratio > 0.1:
            score -= min(30, (change_ratio - 0.1) * 200)
    # 2. 删除比例惩罚
    if current_total > 0:
        del_ratio = deleted_count / current_total
        if del_ratio > 0.05:
            score -= min(25, (del_ratio - 0.05) * 300)
    # 3. 波动占比惩罚
    total_events = deleted_count + new_count
    if total_events > 0:
        fluct_ratio = fluctuation_count / total_events
        if fluct_ratio > FLUCTUATION_RATIO_WARN:
            score -= min(20, (fluct_ratio - FLUCTUATION_RATIO_WARN) * 100)
    # 4. API错误惩罚
    score -= api_errors * 5
    return max(0, round(score, 1))

# ==================== V2.0新增: 资产健康评分 ====================
def calc_asset_health_score(scan_confidence, hb, chain_ok, alarm_count, fluctuation_count, total_assets):
    """资产健康评分(0-100)，加权计算"""
    score = 100.0
    # 扫描置信度权重40%
    score -= (100 - scan_confidence) * 0.4
    # 节点状态权重15%
    if hb.get("status") != "ACTIVE":
        score -= 15
    # 哈希链完整性权重20%
    if not chain_ok:
        score -= 20
    # 告警数量权重15%
    score -= min(15, alarm_count * 5)
    # 波动占比权重10%
    if total_assets > 0:
        fluct_ratio = fluctuation_count / total_assets
        score -= min(10, fluct_ratio * 500)
    return max(0, round(score, 1))

# ==================== V2.0新增: 统计账本 ====================
def load_stat_ledger():
    if os.path.exists(STAT_LEDGER_PATH):
        with open(STAT_LEDGER_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0", "did": DID, "records": []}

def append_stat_ledger(ledger, record):
    ledger["records"].append(record)
    # 只保留最近100轮
    if len(ledger["records"]) > 100:
        ledger["records"] = ledger["records"][-100:]
    with open(STAT_LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)

# ==================== V2.0新增: 结构化告警 ====================
def save_event_alarm(alarms, ts):
    """保存结构化告警事件"""
    existing = []
    if os.path.exists(EVENT_ALARM_PATH):
        try:
            with open(EVENT_ALARM_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f).get("events", [])
        except:
            existing = []
    for a in alarms:
        a["timestamp"] = now_iso()
        a["snap_id"] = f"INC-{ts}"
    existing.extend(alarms)
    # 只保留最近200条
    if len(existing) > 200:
        existing = existing[-200:]
    with open(EVENT_ALARM_PATH, "w", encoding="utf-8") as f:
        json.dump({"version": "1.0", "did": DID, "events": existing}, f, ensure_ascii=False, indent=2)

# ==================== V2.0新增: 业务活跃视图 ====================
def build_business_view(manifest, chain):
    """
    构建业务活跃视图：逻辑过滤SCAN_FLUCTUATION标记的删除，
    输出业务可用资产统计。不改动底层链数据。
    """
    active_assets = {}
    for aid, asset in manifest["assets"].items():
        if asset.get("deleted") and asset.get("delete_trust_level") == "SCAN_FLUCTUATION":
            # 扫描波动删除 → 业务视图中视为活跃
            active_assets[aid] = {**asset, "business_status": "ACTIVE_FLUCTUATION"}
        elif not asset.get("deleted"):
            active_assets[aid] = {**asset, "business_status": "ACTIVE"}
        else:
            active_assets[aid] = {**asset, "business_status": "DELETED_TRUE"}
    view = {
        "version": "1.0",
        "did": DID,
        "trace": TRACE,
        "generated_at": now_iso(),
        "total_business_active": sum(1 for a in active_assets.values() if a["business_status"] in ("ACTIVE", "ACTIVE_FLUCTUATION")),
        "true_deleted": sum(1 for a in active_assets.values() if a["business_status"] == "DELETED_TRUE"),
        "fluctuation_active": sum(1 for a in active_assets.values() if a["business_status"] == "ACTIVE_FLUCTUATION"),
        "assets": active_assets,
        "root_hash": chain["root_hash"]
    }
    with open(BUSINESS_VIEW_PATH, "w", encoding="utf-8") as f:
        json.dump(view, f, ensure_ascii=False, indent=2)
    return view

# ==================== V2.0新增: 临时快照与内核固化门控 ====================
def save_temp_snapshot(ts, manifest, chain, efuse, scan_confidence, health_score):
    """保存临时快照，不执行BLOWN_PERMANENT"""
    snap = {
        "snapshot_id": f"TEMP-SNAP-{ts}",
        "timestamp": now_iso(),
        "did": DID,
        "trace": TRACE,
        "status": "TEMPORARY",
        "scan_confidence": scan_confidence,
        "health_score": health_score,
        "total_assets": len(manifest["assets"]),
        "chain_length": chain["length"],
        "root_hash": chain["root_hash"],
        "efuse_total": efuse["counter"],
        "manifest_hash": sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False)),
        "chain_hash": sha256(json.dumps(chain, sort_keys=True, ensure_ascii=False))
    }
    path = os.path.join(TEMP_SNAP_DIR, f"TEMP-SNAP-{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    return snap, path

def kernel_write_gate(scan_confidence, health_score, large_deletion, fatal_alarms):
    """
    内核固化门控：判断是否执行BLOWN_PERMANENT
    通过条件：置信分≥阈值 AND 无FATAL告警 AND 健康分≥50
    """
    reasons = []
    if scan_confidence < SCAN_CONFIDENCE_THRESHOLD:
        reasons.append(f"扫描置信度{scan_confidence}<{SCAN_CONFIDENCE_THRESHOLD}")
    if health_score < 50:
        reasons.append(f"资产健康分{health_score}<50")
    if fatal_alarms > 0:
        reasons.append(f"存在{fatal_alarms}条FATAL级告警")
    passed = len(reasons) == 0
    return passed, reasons

# ==================== 阶段4: 哈希链校验 ====================
def verify_chain(chain):
    breaks = []
    prev = GENESIS_HASH
    for i, entry in enumerate(chain["chain"]):
        entry_copy = {k: v for k, v in entry.items() if k != "entry_hash"}
        entry_str = json.dumps(entry_copy, sort_keys=True, ensure_ascii=False)
        expected = sha256(prev + entry_str)
        if entry.get("entry_hash") != expected:
            breaks.append({"seq": i, "asset_id": entry.get("asset_id"), "expected": expected, "actual": entry.get("entry_hash")})
        prev = entry.get("entry_hash", prev)
    root_ok = chain["root_hash"] == prev
    return len(breaks) == 0 and root_ok, breaks

# ==================== 主流程 V2.0 ====================
def main():
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    report_path = os.path.join(REPORT_DIR, f"incremental_report_{ts}.json")
    all_alarms = []

    print("=" * 60)
    print(f"全域云资产增量监控锁档 V2.0 | {now_iso()}")
    print(f"确权: {DID} | 溯源: {TRACE} | 协议: {PROTOCOL}")
    print("=" * 60)

    # ===== 阶段0: 前置预检 =====
    print("\n[STAGE 0] 前置预检...")
    preflight_ok, preflight_alarms = preflight_check()
    all_alarms.extend(preflight_alarms)
    fatal_count = sum(1 for a in all_alarms if a["level"] == "FATAL")
    if not preflight_ok:
        print(f"  ✗ 前置预检失败: {fatal_count}条FATAL告警")
        for a in preflight_alarms:
            print(f"    [{a['level']}] {a['event_id']}: {a['desc']}")
        # 预检失败仍生成报告，但不执行扫描和锁档
        fail_report = {
            "report_id": f"INC-{ts}", "timestamp": now_iso(),
            "did": DID, "trace": TRACE, "protocol": PROTOCOL,
            "status": "PREFLIGHT_FAILED",
            "alarms": all_alarms,
            "stage": "preflight"
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(fail_report, f, ensure_ascii=False, indent=2)
        save_event_alarm(all_alarms, ts)
        print(f"\n预检失败，任务终止。报告: {report_path}")
        return fail_report
    print(f"  ✓ 前置预检通过 (告警: {len(all_alarms)}条)")

    # ===== 阶段1: 节点心跳 =====
    print("\n[STAGE 1] 云电脑节点心跳上报...")
    hb = node_heartbeat()
    print(f"  节点: {hb['node_id']} | 状态: {hb['status']}")
    print(f"  CPU: {hb.get('cpu_percent',0)}% | 内存: {hb.get('mem_percent',0)}% | 磁盘: {hb.get('disk_percent',0)}%")
    if hb["status"] != "ACTIVE":
        all_alarms.append({"level": "WARN", "category": "node", "event_id": "NODE_INACTIVE", "desc": f"节点状态{hb['status']}", "suggest": "检查节点健康状态"})

    # ===== 阶段2: 云资产扫描 =====
    print("\n[STAGE 2] 云资产增量扫描...")
    all_assets, drive_assets, wiki_assets, base_assets = scan_all_assets()
    print(f"  扫描总计: {len(all_assets)} (Drive={len(drive_assets)}, Wiki={len(wiki_assets)}, Base={len(base_assets)})")

    # ===== 阶段3: 增量真值校正（V2.0核心） =====
    print("\n[STAGE 3] 增量真值校正与锁档...")
    manifest = load_manifest()
    chain = load_hash_chain()
    efuse = load_efuse()
    prev_report = load_prev_report()
    prev_total = prev_report.get("scan_summary", {}).get("total_scanned", len(all_assets)) if prev_report else len(all_assets)

    baseline_ids = set(manifest["assets"].keys())
    cloud_ids = set(a["asset_id"] for a in all_assets)
    cloud_map = {a["asset_id"]: a for a in all_assets}

    new_assets = []
    modified_assets = []
    deleted_ids = []
    unchanged = []

    for aid, asset in cloud_map.items():
        if aid not in baseline_ids:
            new_assets.append(asset)
        else:
            old = manifest["assets"][aid]
            if old.get("deleted"):
                new_assets.append(asset)  # 恢复
            elif str(old.get("mtime", "")) != str(asset.get("mtime", "")):
                modified_assets.append(asset)
            else:
                unchanged.append(asset)
    for aid in baseline_ids:
        if aid not in cloud_ids and not manifest["assets"][aid].get("deleted"):
            deleted_ids.append(aid)

    # V2.0: 双轮删除确认分类
    deletion_classification = classify_deletions(deleted_ids, prev_report, manifest)
    true_deletions = [aid for aid, tl in deletion_classification.items() if tl == "TRUE"]
    fluctuation_deletions = [aid for aid, tl in deletion_classification.items() if tl == "SCAN_FLUCTUATION"]
    already_deleted = [aid for aid, tl in deletion_classification.items() if tl == "ALREADY_DELETED"]
    # 从删除标记列表中移除历史已删除资产（不参与本轮统计、不重复标记）
    deleted_ids = [aid for aid in deleted_ids if aid not in already_deleted]

    # V2.0: 计算扫描置信度
    scan_confidence = calc_scan_confidence(
        len(all_assets), prev_total,
        len(deleted_ids), len(new_assets),
        len(fluctuation_deletions)
    )

    print(f"  新增: {len(new_assets)} | 修改: {len(modified_assets)} | 删除标记: {len(deleted_ids)}")
    print(f"  双轮确认 → 真实删除: {len(true_deletions)} | 扫描波动: {len(fluctuation_deletions)} | 历史已删除跳过: {len(already_deleted)}")
    print(f"  扫描置信度: {scan_confidence}/100 (固化阈值≥{SCAN_CONFIDENCE_THRESHOLD})")
    print(f"  未变更: {len(unchanged)}")

    # 大规模删除告警
    if len(deleted_ids) >= LARGE_DELETION_THRESHOLD:
        all_alarms.append({
            "level": "WARN", "category": "scan", "event_id": "LARGE_DELETION",
            "desc": f"本轮删除标记{len(deleted_ids)}项超过阈值{LARGE_DELETION_THRESHOLD}",
            "suggest": "人工确认是否为真实批量删除操作"
        })
    # 扫描波动占比告警
    total_events = len(deleted_ids) + len(new_assets)
    if total_events > 0 and len(fluctuation_deletions) / total_events > FLUCTUATION_RATIO_WARN:
        all_alarms.append({
            "level": "WARN", "category": "scan", "event_id": "HIGH_FLUCTUATION",
            "desc": f"扫描波动占比{round(len(fluctuation_deletions)/total_events*100,1)}%超过阈值{FLUCTUATION_RATIO_WARN*100}%",
            "suggest": "检查lark-cli分页扫描稳定性，API可能存在截断"
        })

    # 执行锁档（V2.2: 内容级哈希 + 元类分区 + trust_level）
    locked_count = 0
    content_hash_counter = {"count": 0, "results": []}
    prev_snap_ref = f"INC-{ts}"
    for asset in new_assets:
        lock_asset(chain, manifest, efuse, asset, "NEW", trust_level="TRUE", prev_snap_ref=prev_snap_ref, content_hash_counter=content_hash_counter)
        locked_count += 1
    for asset in modified_assets:
        lock_asset(chain, manifest, efuse, asset, "REV", trust_level="TRUE", prev_snap_ref=prev_snap_ref, content_hash_counter=content_hash_counter)
        locked_count += 1
    for aid in true_deletions:
        flag_deleted(chain, manifest, efuse, aid, trust_level="TRUE", prev_snap_ref=prev_snap_ref)
    for aid in fluctuation_deletions:
        flag_deleted(chain, manifest, efuse, aid, trust_level="SCAN_FLUCTUATION", prev_snap_ref=prev_snap_ref)

    manifest["root_hash"] = chain["root_hash"]
    manifest["efuse_counter"] = efuse["counter"]
    save_manifest(manifest)
    save_hash_chain(chain)
    save_efuse(efuse)
    print(f"  锁档凭证数: {locked_count} | eFuse熔断位: {efuse['counter']} | 链长度: {chain['length']}")
    # V2.2: 内容哈希统计
    ch_success = sum(1 for r in content_hash_counter["results"] if len(r["content_hash"]) == 64)
    ch_skipped = sum(1 for r in content_hash_counter["results"] if r["content_hash"].startswith("CONTENT_HASH_"))
    ch_legacy = sum(1 for r in content_hash_counter["results"] if r["content_hash"] == "LEGACY_NO_CONTENT_HASH")
    print(f"  内容级哈希: 处理{content_hash_counter['count']}个 | 成功{ch_success} | 跳过/失败{ch_skipped} | 待补充{ch_legacy}")
    # V2.2: 重复资产检测（基于content_hash）
    duplicate_groups = {}
    for aid, asset_data in manifest["assets"].items():
        ch = asset_data.get("content_hash", "")
        if ch and len(ch) == 64 and not ch.startswith("CONTENT_HASH_"):
            if ch not in duplicate_groups:
                duplicate_groups[ch] = []
            duplicate_groups[ch].append({"asset_id": aid, "name": asset_data.get("name", "")})
    duplicate_assets = {ch: group for ch, group in duplicate_groups.items() if len(group) > 1}
    duplicate_count = sum(len(g) for g in duplicate_assets.values())
    duplicate_group_count = len(duplicate_assets)
    if duplicate_group_count > 0:
        print(f"  重复资产检测: {duplicate_group_count}组重复 | 涉及{duplicate_count}个资产")
    else:
        print(f"  重复资产检测: 无重复（基于已获取content_hash的资产）")

    # ===== 阶段4: 哈希链校验 =====
    print("\n[STAGE 4] 哈希链完整性校验...")
    chain_ok, breaks = verify_chain(chain)
    if chain_ok:
        print(f"  ✓ 哈希链完整 | 根哈希: {chain['root_hash'][:16]}... | 链长: {chain['length']}")
    else:
        print(f"  ✗ 哈希链断裂! 断裂点: {len(breaks)}")
        all_alarms.append({"level": "ERROR", "category": "chain", "event_id": "CHAIN_BREAK", "desc": f"哈希链断裂{len(breaks)}处", "suggest": "从备份恢复哈希链"})

    # ===== V2.0: 资产健康评分 =====
    health_score = calc_asset_health_score(scan_confidence, hb, chain_ok, len(all_alarms), len(fluctuation_deletions), len(all_assets))
    print(f"\n[V2.0] 资产健康评分: {health_score}/100")

    # ===== V2.0: 业务活跃视图 =====
    business_view = build_business_view(manifest, chain)
    print(f"[V2.0] 业务活跃视图: 业务活跃={business_view['total_business_active']} | 真实删除={business_view['true_deleted']} | 波动活跃={business_view['fluctuation_active']}")

    # ===== 阶段5: 临时快照 + 内核固化门控 =====
    print("\n[STAGE 5] 临时快照与内核固化门控...")
    temp_snap, temp_path = save_temp_snapshot(ts, manifest, chain, efuse, scan_confidence, health_score)
    print(f"  临时快照已保存: {temp_path}")

    fatal_count = sum(1 for a in all_alarms if a["level"] == "FATAL")
    gate_passed, gate_reasons = kernel_write_gate(scan_confidence, health_score, len(deleted_ids) >= LARGE_DELETION_THRESHOLD, fatal_count)
    if gate_passed:
        print(f"  ✓ 内核固化门控通过 → 允许BLOWN_PERMANENT写入")
        kernel_write_status = "BLOWN_PERMANENT_READY"
    else:
        print(f"  ⚠ 内核固化门控未通过，仅保留临时快照:")
        for r in gate_reasons:
            print(f"    - {r}")
        kernel_write_status = "TEMP_ONLY_GATE_BLOCKED"
        all_alarms.append({"level": "WARN", "category": "kernel", "event_id": "GATE_BLOCKED", "desc": "内核固化门控未通过，本轮仅临时快照", "suggest": "; ".join(gate_reasons)})

    # ===== V2.0: 统计账本 =====
    stat_ledger = load_stat_ledger()
    stat_record = {
        "round_id": f"INC-{ts}",
        "timestamp": now_iso(),
        "total_scanned": len(all_assets),
        "new_count": len(new_assets),
        "modified_count": len(modified_assets),
        "deleted_flag_count": len(deleted_ids),
        "true_deletion_count": len(true_deletions),
        "fluctuation_count": len(fluctuation_deletions),
        "unchanged_count": len(unchanged),
        "scan_confidence": scan_confidence,
        "health_score": health_score,
        "chain_length": chain["length"],
        "efuse_total": efuse["counter"],
        "kernel_write_status": kernel_write_status
    }
    append_stat_ledger(stat_ledger, stat_record)

    # ===== 生成巡检报告 V2.0 =====
    print("\n[REPORT] 生成巡检报告...")
    total_active = sum(1 for a in manifest["assets"].values() if not a.get("deleted"))
    total_deleted = sum(1 for a in manifest["assets"].values() if a.get("deleted"))
    report = {
        "report_id": f"INC-{ts}",
        "timestamp": now_iso(),
        "did": DID,
        "trace": TRACE,
        "protocol": PROTOCOL,
        "engine_version": "2.0",
        "node_heartbeat": hb,
        "scan_summary": {
            "drive_count": len(drive_assets),
            "wiki_count": len(wiki_assets),
            "base_count": len(base_assets),
            "total_scanned": len(all_assets)
        },
        "change_summary": {
            "new_count": len(new_assets),
            "modified_count": len(modified_assets),
            "deleted_flag_count": len(deleted_ids),
            "true_deletion_count": len(true_deletions),
            "fluctuation_deletion_count": len(fluctuation_deletions),
            "unchanged_count": len(unchanged),
            "locked_credential_count": locked_count
        },
        "v2_metrics": {
            "scan_confidence": scan_confidence,
            "health_score": health_score,
            "kernel_write_status": kernel_write_status,
            "gate_passed": gate_passed,
            "gate_reasons": gate_reasons
        },
        "hash_chain": {
            "integrity": "PASS" if chain_ok else "FAIL",
            "root_hash": chain["root_hash"],
            "chain_length": chain["length"],
            "break_count": len(breaks)
        },
        "efuse": {
            "total_blown": efuse["counter"],
            "new_this_run": locked_count
        },
        "unified_manifest": {
            "total_assets": len(manifest["assets"]),
            "active_assets": total_active,
            "deleted_assets": total_deleted,
            "manifest_path": MANIFEST_PATH
        },
        "business_view": {
            "business_active": business_view["total_business_active"],
            "true_deleted": business_view["true_deleted"],
            "fluctuation_active": business_view["fluctuation_active"]
        },
        "deleted_asset_ids": deleted_ids,  # V2.0: 供下一轮双轮确认
        "alarms": all_alarms,
        "warnings": [a["desc"] for a in all_alarms if a["level"] in ("WARN", "ERROR")],
        "status": "SUCCESS" if not any(a["level"] == "FATAL" for a in all_alarms) else "SUCCESS_WITH_WARNINGS"
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 保存结构化告警
    save_event_alarm(all_alarms, ts)

    # ===== 输出摘要 =====
    print(f"\n{'=' * 60}")
    print(f"巡检完成 V2.0 | 状态: {report['status']}")
    print(f"新增: {len(new_assets)} | 修改: {len(modified_assets)} | 删除标记: {len(deleted_ids)} (真实{len(true_deletions)}/波动{len(fluctuation_deletions)})")
    print(f"扫描置信度: {scan_confidence} | 健康评分: {health_score} | 内核固化: {kernel_write_status}")
    print(f"锁档凭证: {locked_count} | 哈希链: {'PASS' if chain_ok else 'FAIL'} | 根哈希: {chain['root_hash'][:16]}...")
    print(f"统一资产: {len(manifest['assets'])} (活跃={total_active}, 删除={total_deleted}) | 业务活跃={business_view['total_business_active']}")
    print(f"报告: {report_path}")
    print(f"{'=' * 60}")

    print("\n=== JSON_SUMMARY ===")
    print(json.dumps({
        "status": report["status"],
        "engine_version": "2.0",
        "node_status": hb["status"],
        "new_count": len(new_assets),
        "modified_count": len(modified_assets),
        "deleted_flag_count": len(deleted_ids),
        "true_deletion_count": len(true_deletions),
        "fluctuation_deletion_count": len(fluctuation_deletions),
        "unchanged_count": len(unchanged),
        "locked_credential_count": locked_count,
        "scan_confidence": scan_confidence,
        "health_score": health_score,
        "kernel_write_status": kernel_write_status,
        "gate_passed": gate_passed,
        "hash_chain_integrity": "PASS" if chain_ok else "FAIL",
        "new_root_hash": chain["root_hash"],
        "total_asset_unified": len(manifest["assets"]),
        "business_active": business_view["total_business_active"],
        "efuse_total": efuse["counter"],
        "alarms_count": len(all_alarms),
        "did": DID,
        "trace": TRACE
    }, ensure_ascii=False, indent=2))
    return report

if __name__ == "__main__":
    _lock_fd = acquire_lock()
    try:
        main()
    finally:
        release_lock(_lock_fd)
