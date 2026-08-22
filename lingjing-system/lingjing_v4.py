# -*- coding:utf-8 -*-
"""
灵境六层原型｜四期增强版本 V4.0
SNAP-ZROOT-LINGJING-BRANCH-D-009
迭代点：日志清理截断｜RocksDB KV抽象层｜一致性哈希分片负载均衡
前置依赖：D-006 三期增强版本
"""
import time, uuid, hashlib, threading, json, os, bisect
from queue import Queue, Full
from typing import Dict, Callable, Optional, List, Tuple
from pathlib import Path
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

# ==================== 常量与路径 ====================
TIMEOUT_SEC = 30
DANGER_OP_SET = {"sim_reset_all","param_erase","snapshot_destroy"}
GLOBAL_READONLY = False
event_ledger = []
cognitive_store = dict()

BASE_PATH = Path("./lingjing_data")
QUEUE_LOG_PATH = BASE_PATH / "queue_log"
MERKLE_KV_PATH = BASE_PATH / "merkle_kv"
OFFSET_PATH = BASE_PATH / "offsets"
BASE_PATH.mkdir(exist_ok=True)
QUEUE_LOG_PATH.mkdir(exist_ok=True)
MERKLE_KV_PATH.mkdir(exist_ok=True)
OFFSET_PATH.mkdir(exist_ok=True)

# 日志段配置
LOG_SEG_MAX_LINES = 50000       # 单段最大行数
LOG_MAX_SEGMENTS = 10            # 保留最大段数，超出自动截断最旧段
LOG_CLEANUP_INTERVAL = 3600      # 清理检查间隔（秒）

# ==================== 事件结构体 ====================
class LingjingEvent:
    def __init__(self, domain: str, payload: dict):
        self.ulid = str(uuid.uuid4())
        self.timestamp = time.time()
        self.source_domain = domain
        self.payload = payload
        self.sign = ""
    def hash_digest(self):
        raw = f"{self.ulid}{self.timestamp}{self.source_domain}{str(self.payload)}"
        return hashlib.sha256(raw.encode()).hexdigest()
    def to_dict(self):
        return {"ulid":self.ulid,"timestamp":self.timestamp,"source_domain":self.source_domain,"payload":self.payload,"sign":self.sign}
    @staticmethod
    def from_dict(d):
        evt = LingjingEvent(d["source_domain"], d["payload"])
        evt.ulid = d["ulid"]; evt.timestamp = d["timestamp"]; evt.sign = d["sign"]
        return evt

# ==================== KV抽象层（支持RocksDB / 简易文件KV） ====================
class KVBackend:
    """KV存储抽象基类"""
    def put(self, key: str, value: str): raise NotImplementedError
    def get(self, key: str) -> Optional[str]: raise NotImplementedError
    def close(self): pass

class SimpleFileKV(KVBackend):
    """简易文件KV（默认后端，无外部依赖）"""
    def __init__(self, dir_path: Path):
        self.dir = Path(dir_path)
        self.dir.mkdir(exist_ok=True)
    def _keyfile(self, key: str) -> Path:
        safe = hashlib.md5(key.encode()).hexdigest()
        return self.dir / f"{safe}.kv"
    def put(self, key: str, value: str):
        self._keyfile(key).write_text(value, encoding="utf-8")
    def get(self, key: str) -> Optional[str]:
        fp = self._keyfile(key)
        if fp.exists(): return fp.read_text(encoding="utf-8")
        return None

class RocksDBKV(KVBackend):
    """RocksDB后端（高性能，需pip install rocksdb）"""
    def __init__(self, db_path: Path):
        import rocksdb
        self.db = rocksdb.DB(str(db_path), rocksdb.Options(create_if_missing=True))
    def put(self, key: str, value: str):
        self.db.put(key.encode(), value.encode())
    def get(self, key: str) -> Optional[str]:
        v = self.db.get(key.encode())
        return v.decode() if v else None
    def close(self):
        self.db.close()

def create_kv_backend(dir_path: Path) -> KVBackend:
    """工厂方法：优先RocksDB，回退简易文件KV"""
    try:
        import rocksdb
        return RocksDBKV(Path(dir_path))
    except ImportError:
        return SimpleFileKV(Path(dir_path))

# ==================== 冷热混合增量Merkle树（KV抽象层） ====================
class HybridIncrMerkleTree:
    def __init__(self, tree_height=16, cache_size=2048, kv_dir=None):
        self.H = tree_height
        self.size = 0
        self.mem_cache: Dict[Tuple[int,int], str] = {}
        self.cache_max = cache_size
        kv_dir = kv_dir or MERKLE_KV_PATH
        self.kv = create_kv_backend(kv_dir)
    @staticmethod
    def _hash(a, b):
        return hashlib.sha256((a+b).encode()).hexdigest()
    def _key(self, pos):
        return f"L{pos[0]}_I{pos[1]}"
    def _get_node(self, pos):
        if pos in self.mem_cache: return self.mem_cache[pos]
        v = self.kv.get(self._key(pos))
        if v is not None:
            if len(self.mem_cache) >= self.cache_max:
                oldk = next(iter(self.mem_cache.keys()))
                self.kv.put(self._key(oldk), self.mem_cache.pop(oldk))
            self.mem_cache[pos] = v
        return v
    def _set_node(self, pos, hval):
        if len(self.mem_cache) >= self.cache_max:
            oldk = next(iter(self.mem_cache.keys()))
            self.kv.put(self._key(oldk), self.mem_cache.pop(oldk))
        self.mem_cache[pos] = hval
    def append(self, leaf_hash):
        idx = self.size
        self.size += 1
        level = 0
        cur_pos = (level, idx)
        self._set_node(cur_pos, leaf_hash)
        cur_hash = leaf_hash
        while level < self.H - 1:
            sibling_pos = (level, idx + 1) if idx % 2 == 0 else (level, idx - 1)
            sibling_hash = self._get_node(sibling_pos)
            if sibling_hash is None:
                # 不满树：用当前哈希填充缺失兄弟，继续向上计算到根
                sibling_hash = cur_hash
            # 左兄弟在前，右兄弟在后
            if idx % 2 == 0:
                cur_hash = self._hash(cur_hash, sibling_hash)
            else:
                cur_hash = self._hash(sibling_hash, cur_hash)
            level += 1
            idx = idx // 2
            cur_pos = (level, idx)
            self._set_node(cur_pos, cur_hash)
    def root(self):
        # 不满树：从最高层向下查找第一个非None节点作为根
        for level in range(self.H - 1, -1, -1):
            v = self._get_node((level, 0))
            if v is not None:
                return v
        return None
    def close(self):
        self.kv.close()

inc_merkle = HybridIncrMerkleTree(tree_height=16)

# ==================== 带偏移位点的持久化分片队列（日志清理） ====================
class PersistPartitionQueue:
    def __init__(self, partition_id, max_q=1000, worker_cnt=1):
        self.pid = partition_id
        self.mq: Queue[LingjingEvent] = Queue(maxsize=max_q)
        self.running = True
        self.worker_num = worker_cnt
        self.workers: List[threading.Thread] = []
        self.log_dir = QUEUE_LOG_PATH
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.offset_file = OFFSET_PATH / f"{partition_id}.offset"
        self.current_seg = 0
        self.current_seg_lines = 0
        self._load_offset()
        self._recover()
        for _ in range(worker_cnt):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self.workers.append(t)
        # 启动日志清理守护线程
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def _load_offset(self):
        """加载已消费偏移位点"""
        if self.offset_file.exists():
            data = json.loads(self.offset_file.read_text(encoding="utf-8"))
            self.current_seg = data.get("seg", 0)
            self.current_seg_lines = data.get("lines", 0)
        else:
            self.current_seg = 0
            self.current_seg_lines = 0

    def _save_offset(self):
        """保存已消费偏移位点"""
        self.offset_file.write_text(
            json.dumps({"seg": self.current_seg, "lines": self.current_seg_lines}),
            encoding="utf-8"
        )

    def _seg_file(self, seg_id):
        return self.log_dir / f"part_{self.pid}_seg{seg_id:04d}.log"

    def _list_segments(self):
        """列出所有段文件，按序号排序"""
        import glob
        files = sorted(glob.glob(str(self.log_dir / f"part_{self.pid}_seg*.log")))
        return [Path(f) for f in files]

    def _recover(self):
        """从偏移位点之后恢复未消费事件"""
        segs = self._list_segments()
        for seg_path in segs:
            seg_id = int(seg_path.stem.split("_seg")[-1])
            if seg_id < self.current_seg:
                continue
            lines = seg_path.read_text(encoding="utf-8").splitlines()
            start = self.current_seg_lines if seg_id == self.current_seg else 0
            for ln in lines[start:]:
                try:
                    d = json.loads(ln)
                    evt = LingjingEvent.from_dict(d)
                    self.mq.put_nowait(evt)
                except Exception:
                    continue

    def enqueue(self, evt):
        try:
            self.mq.put_nowait(evt)
            # 写入当前段，段满自动切新段
            if self.current_seg_lines >= LOG_SEG_MAX_LINES:
                self.current_seg += 1
                self.current_seg_lines = 0
            seg_file = self._seg_file(self.current_seg)
            with open(seg_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(evt.to_dict()) + "\n")
            self.current_seg_lines += 1
            return True
        except Full:
            return False

    def _worker(self):
        while self.running:
            evt = self.mq.get()
            event_ledger.append(evt)
            inc_merkle.append(evt.hash_digest())
            self.mq.task_done()

    def _cleanup_loop(self):
        """日志清理守护线程：定期截断已消费的旧段"""
        while self.running:
            time.sleep(LOG_CLEANUP_INTERVAL)
            self._cleanup_old_segments()

    def _cleanup_old_segments(self):
        """删除已消费且超过保留数量的旧段"""
        self._save_offset()
        segs = self._list_segments()
        # 只保留当前段及之前LOG_MAX_SEGMENTS-1个段
        keep_from_seg = max(0, self.current_seg - LOG_MAX_SEGMENTS + 1)
        deleted = 0
        for seg_path in segs:
            seg_id = int(seg_path.stem.split("_seg")[-1])
            if seg_id < keep_from_seg and seg_id < self.current_seg:
                try:
                    seg_path.unlink()
                    deleted += 1
                except Exception:
                    pass
        return deleted

    def shutdown(self):
        self.running = False
        self._save_offset()

# ==================== 一致性哈希分片负载均衡 ====================
class ConsistentHashPartitioner:
    """一致性哈希分片器：支持动态扩缩容、热点域自动分裂"""
    def __init__(self, num_partitions=4, virtual_nodes=150):
        self.num_partitions = num_partitions
        self.virtual_nodes = virtual_nodes
        self.ring: List[Tuple[int, int]] = []  # (hash, partition_id)
        self.domain_load: Dict[str, int] = {}   # 域负载计数
        self.partition_load: Dict[int, int] = {i: 0 for i in range(num_partitions)}
        self._build_ring()
        self.lock = threading.RLock()

    def _build_ring(self):
        self.ring = []
        for p in range(self.num_partitions):
            for v in range(self.virtual_nodes):
                key = f"partition_{p}_vnode_{v}"
                h = int(hashlib.md5(key.encode()).hexdigest(), 16)
                self.ring.append((h, p))
        self.ring.sort(key=lambda x: x[0])

    def get_partition(self, domain: str) -> int:
        """根据domain一致性哈希路由到分片"""
        h = int(hashlib.md5(domain.encode()).hexdigest(), 16)
        idx = bisect.bisect_left(self.ring, (h, -1))
        if idx >= len(self.ring):
            idx = 0
        partition_id = self.ring[idx][1]
        with self.lock:
            self.domain_load[domain] = self.domain_load.get(domain, 0) + 1
            self.partition_load[partition_id] = self.partition_load.get(partition_id, 0) + 1
        return partition_id

    def add_partition(self):
        """动态增加分片（扩容）"""
        with self.lock:
            self.num_partitions += 1
            new_pid = self.num_partitions - 1
            self.partition_load[new_pid] = 0
            for v in range(self.virtual_nodes):
                key = f"partition_{new_pid}_vnode_{v}"
                h = int(hashlib.md5(key.encode()).hexdigest(), 16)
                bisect.insort(self.ring, (h, new_pid), key=lambda x: x[0])
        return new_pid

    def get_hotspot_domains(self, threshold=1000) -> List[str]:
        """识别超过阈值的热点域"""
        with self.lock:
            return [d for d, cnt in self.domain_load.items() if cnt > threshold]

    def get_load_report(self) -> dict:
        """生成分片负载报告"""
        with self.lock:
            return {
                "num_partitions": self.num_partitions,
                "partition_load": dict(self.partition_load),
                "total_events": sum(self.partition_load.values()),
                "hotspot_domains": self.get_hotspot_domains()
            }

# ==================== 分区异步事件总线（负载均衡） ====================
class PartitionAsyncBus:
    def __init__(self, worker_per_part=1, initial_partitions=4):
        self.subscriber: Dict[str, Callable] = {}
        self.partitions: Dict[int, PersistPartitionQueue] = {}
        self.partitioner = ConsistentHashPartitioner(num_partitions=initial_partitions)
        self.key = RSA.generate(2048)
        self.pubkey = self.key.publickey()
        self.worker_pp = worker_per_part
        self._init_partitions(initial_partitions)
        # 启动热点监控线程
        self.monitor_thread = threading.Thread(target=self._hotspot_monitor, daemon=True)
        self.monitor_thread.start()

    def _init_partitions(self, n):
        for i in range(n):
            self.partitions[i] = PersistPartitionQueue(f"p{i}", worker_cnt=self.worker_pp)

    def sign_event(self, evt):
        h = SHA256.new(evt.hash_digest().encode())
        sig = pkcs1_15.new(self.key).sign(h)
        evt.sign = sig.hex()
        return evt

    def verify_event(self, evt):
        try:
            h = SHA256.new(evt.hash_digest().encode())
            pkcs1_15.new(self.pubkey).verify(h, bytes.fromhex(evt.sign))
            return True
        except Exception:
            return False

    def subscribe(self, domain, callback):
        self.subscriber[domain] = callback

    def publish(self, evt):
        if not self.verify_event(evt):
            return False
        partition_id = self.partitioner.get_partition(evt.source_domain)
        if partition_id not in self.partitions:
            self.partitions[partition_id] = PersistPartitionQueue(f"p{partition_id}", worker_cnt=self.worker_pp)
        res = self.partitions[partition_id].enqueue(evt)
        cb = self.subscriber.get(evt.source_domain)
        if cb:
            threading.Thread(target=cb, args=(evt,), daemon=True).start()
        return res

    def _hotspot_monitor(self):
        """热点监控：单分片负载过高时自动扩容"""
        while True:
            time.sleep(60)  # 每分钟检查
            report = self.partitioner.get_load_report()
            loads = list(report["partition_load"].values())
            if loads and max(loads) > 0:
                avg = sum(loads) / len(loads)
                # 最大分片负载超过均值2倍时自动扩容
                if max(loads) > avg * 2 and report["num_partitions"] < 16:
                    new_pid = self.partitioner.add_partition()
                    self.partitions[new_pid] = PersistPartitionQueue(f"p{new_pid}", worker_cnt=self.worker_pp)

    def get_load_report(self):
        return self.partitioner.get_load_report()

# ==================== 业务层（接口兼容） ====================
class SimLayer:
    def __init__(self, bus):
        self.bus = bus
        self.sim_state = {"x":0.0,"y":0.0,"scene_id":1}
        bus.subscribe("sim_layer", self.on_event)
    def on_event(self, evt):
        op = evt.payload.get("op")
        if op == "set_param": self.sim_state.update(evt.payload["data"])
        elif op == "sim_reset_all": self.sim_state = {"x":0.0,"y":0.0,"scene_id":1}
        back_evt = LingjingEvent("sim_layer", {"new_state": self.sim_state})
        self.bus.sign_event(back_evt)
        self.bus.publish(back_evt)

class HmiAdapter:
    def __init__(self, bus):
        self.bus = bus
        bus.subscribe("hmi_layer", self.on_event)
    def send_user_cmd(self, op, data):
        evt = LingjingEvent("sim_layer", {"op": op, "data": data})
        self.bus.sign_event(evt)
        return self.bus.publish(evt)
    def on_event(self, evt): pass

class AuditGuard:
    def __init__(self, bus):
        self.bus = bus
        self.waiting_danger = {}
        bus.subscribe("guard_layer", self.on_event)
    def danger_check(self, op):
        global GLOBAL_READONLY
        if op in DANGER_OP_SET and not GLOBAL_READONLY: return "need_confirm"
        return "pass"
    def timeout_detect(self):
        global GLOBAL_READONLY
        now = time.time()
        for k, v in list(self.waiting_danger.items()):
            if now - v["start_ts"] > TIMEOUT_SEC:
                GLOBAL_READONLY = True
                del self.waiting_danger[k]
    def human_unlock(self):
        global GLOBAL_READONLY
        GLOBAL_READONLY = False
    def on_event(self, evt): pass

class CognitionLayer:
    def __init__(self, bus):
        self.bus = bus
        bus.subscribe("cog_layer", self.on_event)
    def write_note(self, snapshot_hash, note_text):
        cognitive_store[snapshot_hash] = note_text
    def on_event(self, evt): pass

def export_report():
    return {
        "merkle_root": inc_merkle.root(),
        "event_count": inc_merkle.size,
        "cognitive_data": cognitive_store,
        "load_report": None  # 由bus.get_load_report()补充
    }

def main():
    bus = PartitionAsyncBus(initial_partitions=4)
    sim = SimLayer(bus)
    hmi = HmiAdapter(bus)
    guard = AuditGuard(bus)
    cog = CognitionLayer(bus)
    hmi.send_user_cmd("set_param", {"data": {"x": 12.5}})
    time.sleep(0.3)
    res = export_report()
    res["load_report"] = bus.get_load_report()
    print(json.dumps(res, indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
