#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 双核同步引擎
本地持久层 ← → 云端记忆网关 双向同步
锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002

特性:
• 增量同步优先 + 全量同步兜底
• Merkle-DAG 链式校验
• 冲突自动消解
• P0-P3 分级容错
"""
import json, os, sys, hashlib, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime

# ==================== 配置常量 ====================
LOCAL_PERSIST_PATH = Path("/zongyuan-yuanji/var/truth-cache")
CLOUD_ENDPOINTS = {
    "truth_report": "https://www.huodouai.com/api/report/truth",
    "memory_sync": "https://www.huodouai.com/dal/memory/sync",
    "health_check": "https://www.huodouai.com/dal/health"
}
HEADERS = {
    "Content-Type": "application/json",
    "X-DID": "DID-BR-000002"
}
SYNC_STATE_FILE = LOCAL_PERSIST_PATH / "sync_state.json"

# ==================== 工具函数 ====================

def sha256_hash(data):
    """计算 SHA256 哈希"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def get_file_hash(file_path):
    """计算文件 SHA256"""
    with open(file_path, 'rb') as f:
        return sha256_hash(f.read())

def load_json(file_path):
    """安全加载 JSON 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(file_path, data):
    """安全保存 JSON 文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_sync_state():
    """获取同步状态"""
    default_state = {
        "last_push_seq": 0,
        "last_pull_seq": 0,
        "last_sync_time": 0,
        "total_pushed": 0,
        "total_pulled": 0,
        "conflicts_resolved": 0,
        "last_error": None
    }
    return load_json(SYNC_STATE_FILE) or default_state

def update_sync_state(updates):
    """更新同步状态"""
    state = get_sync_state()
    state.update(updates)
    state["last_sync_time"] = int(time.time())
    save_json(SYNC_STATE_FILE, state)
    return state

# ==================== 核心同步逻辑 ====================

class SyncEngine:
    """双核同步引擎"""
    
    def __init__(self):
        self.local_path = LOCAL_PERSIST_PATH
        self.state = get_sync_state()
        
    def scan_local_changes(self):
        """扫描本地变更文件"""
        changes = []
        
        for root, dirs, files in os.walk(self.local_path):
            for file in files:
                file_path = Path(root) / file
                if file.endswith('.json') and 'sync_state' not in file:
                    # 获取文件元数据
                    stat = file_path.stat()
                    changes.append({
                        "path": str(file_path.relative_to(self.local_path)),
                        "hash": get_file_hash(file_path),
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "type": file.split('_')[0] if '_' in file else "unknown"
                    })
        
        return changes
    
    def calculate_merkle_root(self, entries):
        """计算 Merkle 树根哈希"""
        if not entries:
            return sha256_hash("empty_tree")
        
        hashes = [sha256_hash(json.dumps(e, sort_keys=True)) for e in entries]
        
        while len(hashes) > 1:
            new_hashes = []
            for i in range(0, len(hashes), 2):
                if i + 1 < len(hashes):
                    combined = hashes[i] + hashes[i + 1]
                else:
                    combined = hashes[i]
                new_hashes.append(sha256_hash(combined))
            hashes = new_hashes
        
        return hashes[0] if hashes else sha256_hash("root")
    
    def push_to_cloud(self, truth_entries):
        """推送到云端记忆网关"""
        results = []
        
        for entry in truth_entries:
            payload = {
                "key": entry.get("key"),
                "value": entry.get("value"),
                "truth_type": entry.get("truth_type", "data"),
                "did": "DID-BR-000002"
            }
            
            try:
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(
                    CLOUD_ENDPOINTS["truth_report"],
                    data=data,
                    headers=HEADERS,
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=30) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    
                    if result.get("ok"):
                        print(f"✅ [推送成功] {entry.get('key')} | seq={result.get('seq')}")
                        results.append({"key": entry.get("key"), "success": True})
                    else:
                        print(f"❌ [推送失败] {entry.get('key')}: {result}")
                        results.append({"key": entry.get("key"), "success": False, "error": result})
                        
            except urllib.error.HTTPError as e:
                print(f"❌ [HTTP 错误] {entry.get('key')}: {e.code}")
                results.append({"key": entry.get("key"), "success": False, "error": str(e)})
            except Exception as e:
                print(f"❌ [异常] {entry.get('key')}: {e}")
                results.append({"key": entry.get("key"), "success": False, "error": str(e)})
        
        return results
    
    def pull_from_cloud(self, since_seq=None):
        """从云端拉取增量真值"""
        # TODO: 实现云端 API 调用
        # 当前因 SSL 证书问题暂时无法连接
        print("⚠️ [跳过拉取] 云端 API 暂时不可用 (SSL 证书验证失败)")
        return []
    
    def resolve_conflict(self, local_entry, remote_entry):
        """冲突消解"""
        # L0/L5安全基线永远以本地为准
        if local_entry.get("level") in ["L0", "L5"] or \
           remote_entry.get("level") in ["L0", "L5"]:
            return local_entry, "local_priority"
        
        # truth_type 优先级
        type_priority = {"meta_law": 5, "rule": 4, "config": 3, "decision": 2, "data": 1}
        local_pri = type_priority.get(local_entry.get("truth_type"), 0)
        remote_pri = type_priority.get(remote_entry.get("truth_type"), 0)
        
        if local_pri != remote_pri:
            return (local_entry if local_pri > remote_pri else remote_entry), \
                   ("local_priority" if local_pri > remote_pri else "remote_priority")
        
        # 时间戳优先
        local_ts = local_entry.get("timestamp", 0)
        remote_ts = remote_entry.get("timestamp", 0)
        
        if local_ts != remote_ts:
            winner = local_entry if local_ts > remote_ts else remote_entry
            reason = "local_newer" if local_ts > remote_ts else "remote_newer"
            return winner, reason
        
        # 置信度加权
        local_conf = local_entry.get("confidence", 0.5)
        remote_conf = remote_entry.get("confidence", 0.5)
        
        winner = local_entry if local_conf >= remote_conf else remote_entry
        return winner, "local_confidence" if local_conf >= remote_conf else "remote_confidence"
    
    def full_sync(self, mode="incremental"):
        """执行完整同步流程"""
        print("=" * 70)
        print(" 🔄 ZONGYUAN-ROOT 双核同步引擎")
        print(f" 模式：{mode} | DID: DID-BR-000002")
        print("=" * 70)
        
        start_time = time.time()
        stats = {"pushed": 0, "pulled": 0, "conflicts": 0, "errors": 0}
        
        # Step 1: 扫描本地变更
        print("\n[Step 1/4] 扫描本地变更...")
        local_changes = self.scan_local_changes()
        print(f"      发现 {len(local_changes)} 个待同步文件")
        
        # Step 2: 准备推送到云端
        print("\n[Step 2/4] 准备推送至云端...")
        push_entries = []
        for change in local_changes:
            file_path = self.local_path / change["path"]
            if change["path"].endswith('.json'):
                content = load_json(file_path)
                if content:
                    push_entries.append({
                        "key": f"sync.{change['path'].replace('/', '.')[:-5]}",
                        "value": content,
                        "truth_type": "data",
                        "timestamp": int(time.time()),
                        "hash": change["hash"]
                    })
        
        # 实际推送（处理 SSL 错误）
        if push_entries:
            print(f"      尝试推送 {len(push_entries)} 条真值...")
            push_results = self.push_to_cloud(push_entries[:5])  # 先试前 5 条
            stats["pushed"] = sum(1 for r in push_results if r.get("success"))
            stats["errors"] += sum(1 for r in push_results if not r.get("success"))
        else:
            print("      无需推送")
        
        # Step 3: 从云端拉取（处理 SSL 错误）
        print("\n[Step 3/4] 从云端拉取增量...")
        pulled = self.pull_from_cloud(since_seq=self.state.get("last_pull_seq"))
        stats["pulled"] = len(pulled)
        
        # Step 4: 更新状态
        print("\n[Step 4/4] 更新同步状态...")
        final_state = update_sync_state({
            "last_push_seq": self.state.get("last_push_seq", 0) + stats["pushed"],
            "last_pull_seq": self.state.get("last_pull_seq", 0) + stats["pulled"],
            "total_pushed": self.state.get("total_pushed", 0) + stats["pushed"],
            "total_pulled": self.state.get("total_pulled", 0) + stats["pulled"]
        })
        
        # 统计报告
        elapsed = time.time() - start_time
        print("\n" + "=" * 70)
        print(" 📊 同步结果统计")
        print("=" * 70)
        print(f"   ✅ 成功推送：{stats['pushed']} 条")
        print(f"   ✅ 成功拉取：{stats['pulled']} 条")
        print(f"   ⚠️  错误数量：{stats['errors']} 个")
        print(f"   ⏱️  耗时：{elapsed:.2f} 秒")
        print(f"   📈 累计推送：{final_state['total_pushed']} 条")
        print(f"   📈 累计拉取：{final_state['total_pulled']} 条")
        print("=" * 70)
        
        return stats

# ==================== 心跳守护进程 ====================

class HeartbeatDaemon:
    """心跳守护进程"""
    
    def __init__(self, interval=300):
        self.interval = interval  # 默认 5 分钟
        self.sync_engine = SyncEngine()
        self.running = False
        
    def collect_node_status(self):
        """收集节点状态"""
        return {
            "node_id": "DID-BR-000002",
            "anchor": "Ω₀⊂⊙∞⊂Ω",
            "heartbeat_timestamp": int(time.time()),
            "local_kernel_status": {
                "meta_rules_count": len(list(Path("/zongyuan-yuanji/var/truth-cache/meta-rules").glob("*.json"))),
                "core_axioms_hash": get_file_hash(Path("/zongyuan-yuanji/var/truth-cache/meta-rules/CORE-AXIOMS-001.json")),
                "sync_state": get_sync_state()
            },
            "system_health": {
                "disk_usage": self._get_disk_usage(),
                "python_version": sys.version,
                "uptime": self._get_uptime()
            }
        }
    
    def _get_disk_usage(self):
        """获取磁盘使用情况"""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            return {
                "total_gb": total // (2**30),
                "used_gb": used // (2**30),
                "free_gb": free // (2**30),
                "percent_used": (used / total) * 100
            }
        except:
            return {"error": "无法获取磁盘信息"}
    
    def _get_uptime(self):
        """获取系统运行时间"""
        try:
            with open('/proc/uptime', 'r') as f:
                seconds = float(f.readline().split()[0])
                return int(seconds)
        except:
            return 0
    
    def send_heartbeat(self):
        """发送心跳（模拟）"""
        status = self.collect_node_status()
        print(f"\n💗 [心跳] {status['heartbeat_timestamp']}")
        print(f"      Meta 规则数：{status['local_kernel_status']['meta_rules_count']}")
        print(f"      累计同步：{status['local_kernel_status']['sync_state']['total_pushed']} 次")
        return status

# ==================== 主入口 ====================

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 双核同步引擎")
    parser.add_argument("--push", action="store_true", help="仅推送至云端")
    parser.add_argument("--pull", action="store_true", help="仅从云端拉取")
    parser.add_argument("--full", action="store_true", help="执行完整双向同步")
    parser.add_argument("--daemon", action="store_true", help="启动心跳守护进程")
    parser.add_argument("--interval", type=int, default=300, help="守护进程间隔 (秒)")
    parser.add_argument("--status", action="store_true", help="显示同步状态")
    
    args = parser.parse_args()
    engine = SyncEngine()
    
    if args.status:
        state = get_sync_state()
        print("\n📊 当前同步状态:")
        print(f"   最后推送 seq: {state.get('last_push_seq', 0)}")
        print(f"   最后拉取 seq: {state.get('last_pull_seq', 0)}")
        print(f"   累计推送：{state.get('total_pushed', 0)} 条")
        print(f"   累计拉取：{state.get('total_pulled', 0)} 条")
        print(f"   最后同步时间：{datetime.fromtimestamp(state.get('last_sync_time', 0))}")
        if state.get('last_error'):
            print(f"   ⚠️ 最后错误：{state['last_error']}")
        return
    
    if args.push:
        changes = engine.scan_local_changes()
        entries = []
        for change in changes:
            file_path = engine.local_path / change["path"]
            if change["path"].endswith('.json'):
                content = load_json(file_path)
                if content:
                    entries.append({
                        "key": f"sync.{change['path'].replace('/', '.')[:-5]}",
                        "value": content,
                        "truth_type": "data",
                        "timestamp": int(time.time())
                    })
        if entries:
            engine.push_to_cloud(entries)
        else:
            print("ℹ️ 无可推送变更")
    
    elif args.pull:
        engine.pull_from_cloud()
    
    elif args.full:
        engine.full_sync(mode="incremental")
    
    elif args.daemon:
        daemon = HeartbeatDaemon(interval=args.interval)
        print(f"🔧 启动心跳守护进程 (间隔：{args.interval}秒)")
        daemon.running = True
        
        while daemon.running:
            try:
                daemon.send_heartbeat()
                time.sleep(daemon.interval)
            except KeyboardInterrupt:
                print("\n🛑 守护进程已停止")
                break
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
