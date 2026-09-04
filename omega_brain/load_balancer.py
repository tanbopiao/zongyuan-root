#!/usr/bin/env python3
"""
M3-5: 多实例部署+负载均衡器
支持多Ω-Brainμ实例管理、健康检查、轮询/加权路由、故障自动切换
"""
import json
import time
import hashlib
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
INSTANCES_FILE = ROOT / "omega_brain" / "instances.json"
LB_LOG = ROOT / "logs" / "load_balancer.log"

class Instance:
    """Ω-Brainμ 实例"""
    def __init__(self, instance_id: str, host: str, port: int, weight: int = 1, tags: list = None):
        self.id = instance_id
        self.host = host
        self.port = port
        self.weight = weight
        self.tags = tags or []
        self.healthy = False
        self.last_check = None
        self.request_count = 0
        self.error_count = 0
        self.start_time = datetime.now().isoformat()

    @property
    def url(self):
        return f"http://{self.host}:{self.port}"

    @property
    def health_url(self):
        return f"{self.url}/health"

    def to_dict(self):
        return {
            "id": self.id,
            "host": self.host,
            "port": self.port,
            "url": self.url,
            "weight": self.weight,
            "tags": self.tags,
            "healthy": self.healthy,
            "last_check": self.last_check,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "start_time": self.start_time
        }

class LoadBalancer:
    """负载均衡器"""

    def __init__(self):
        self.instances: List[Instance] = []
        self.current_index = 0
        self.running = False
        self._lock = threading.Lock()
        self._load_instances()

    def _load_instances(self):
        if INSTANCES_FILE.exists():
            with open(INSTANCES_FILE) as f:
                data = json.load(f)
            for inst_data in data.get("instances", []):
                # 兼容两种格式：有host/port直接用，只有url则解析
                if "host" in inst_data and "port" in inst_data:
                    host = inst_data["host"]
                    port = inst_data["port"]
                elif "url" in inst_data:
                    # 从 http://host:port 解析
                    url = inst_data["url"].replace("http://", "").replace("https://", "")
                    parts = url.split(":")
                    host = parts[0]
                    port = int(parts[1]) if len(parts) > 1 else 8765
                else:
                    continue
                inst = Instance(
                    inst_data["id"], host, port,
                    inst_data.get("weight", 1), inst_data.get("tags", [])
                )
                inst.healthy = inst_data.get("healthy", False)
                inst.last_check = inst_data.get("last_check")
                inst.request_count = inst_data.get("request_count", 0)
                inst.error_count = inst_data.get("error_count", 0)
                self.instances.append(inst)

    def _save_instances(self):
        INSTANCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(INSTANCES_FILE, "w") as f:
            json.dump({
                "instances": [i.to_dict() for i in self.instances],
                "updated_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

    def _log(self, msg):
        LB_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LB_LOG, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")

    def add_instance(self, host: str, port: int, weight: int = 1, tags: list = None) -> Instance:
        """添加实例"""
        instance_id = f"omega-{hashlib.sha256(f'{host}:{port}'.encode()).hexdigest()[:8]}"
        inst = Instance(instance_id, host, port, weight, tags)
        with self._lock:
            self.instances.append(inst)
            self._save_instances()
        self._log(f"添加实例: {instance_id} {host}:{port}")
        return inst

    def remove_instance(self, instance_id: str):
        """移除实例"""
        with self._lock:
            self.instances = [i for i in self.instances if i.id != instance_id]
            self._save_instances()
        self._log(f"移除实例: {instance_id}")

    def check_health(self, instance: Instance) -> bool:
        """健康检查"""
        try:
            import urllib.request
            with urllib.request.urlopen(instance.health_url, timeout=3) as resp:
                data = json.loads(resp.read())
                healthy = data.get("status") == "healthy"
                instance.healthy = healthy
                instance.last_check = datetime.now().isoformat()
                return healthy
        except Exception as e:
            instance.healthy = False
            instance.last_check = datetime.now().isoformat()
            instance.error_count += 1
            return False

    def health_check_all(self):
        """全量健康检查"""
        results = []
        for inst in self.instances:
            healthy = self.check_health(inst)
            results.append({"id": inst.id, "healthy": healthy})
            if not healthy:
                self._log(f"实例不健康: {inst.id} ({inst.url})")
        self._save_instances()
        return results

    def get_healthy_instances(self) -> List[Instance]:
        """获取健康实例列表"""
        return [i for i in self.instances if i.healthy]

    def round_robin(self) -> Optional[Instance]:
        """轮询路由"""
        healthy = self.get_healthy_instances()
        if not healthy:
            return None
        with self._lock:
            inst = healthy[self.current_index % len(healthy)]
            self.current_index += 1
            inst.request_count += 1
        return inst

    def weighted_round_robin(self) -> Optional[Instance]:
        """加权轮询路由"""
        healthy = self.get_healthy_instances()
        if not healthy:
            return None
        # 按权重扩展选择池
        pool = []
        for inst in healthy:
            pool.extend([inst] * inst.weight)
        with self._lock:
            inst = pool[self.current_index % len(pool)]
            self.current_index += 1
            inst.request_count += 1
        return inst

    def route_request(self, strategy: str = "round_robin") -> Optional[dict]:
        """路由请求到实例"""
        if strategy == "weighted":
            inst = self.weighted_round_robin()
        else:
            inst = self.round_robin()
        if inst:
            return {"instance": inst.to_dict(), "strategy": strategy}
        return {"error": "no_healthy_instances", "strategy": strategy}

    def health_check_loop(self, interval: int = 30):
        """健康检查循环（后台线程）"""
        while self.running:
            self.health_check_all()
            time.sleep(interval)

    def start(self):
        """启动负载均衡器"""
        self.running = True
        self._log("负载均衡器启动")
        # 初始健康检查
        self.health_check_all()
        # 启动后台健康检查线程
        checker = threading.Thread(target=self.health_check_loop, daemon=True)
        checker.start()
        print(f"🚀 负载均衡器已启动 ({len(self.instances)}个实例)")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.running = False
        self._log("负载均衡器停止")
        print("负载均衡器已停止")

    def get_status(self) -> dict:
        """获取状态"""
        return {
            "total_instances": len(self.instances),
            "healthy_instances": len(self.get_healthy_instances()),
            "instances": [i.to_dict() for i in self.instances],
            "current_index": self.current_index,
            "running": self.running
        }

if __name__ == "__main__":
    import sys
    lb = LoadBalancer()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            print(json.dumps(lb.get_status(), ensure_ascii=False, indent=2))
        elif cmd == "add" and len(sys.argv) > 3:
            host = sys.argv[2]
            port = int(sys.argv[3])
            weight = int(sys.argv[4]) if len(sys.argv) > 4 else 1
            inst = lb.add_instance(host, port, weight)
            print(json.dumps(inst.to_dict(), ensure_ascii=False, indent=2))
        elif cmd == "remove" and len(sys.argv) > 2:
            lb.remove_instance(sys.argv[2])
            print("已移除")
        elif cmd == "check":
            results = lb.health_check_all()
            print(json.dumps(results, ensure_ascii=False, indent=2))
        elif cmd == "route":
            result = lb.route_request("weighted")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif cmd == "start":
            lb.start()
    else:
        # 默认：添加本地实例并显示状态
        if not lb.instances:
            lb.add_instance("127.0.0.1", 8765, weight=2, tags=["primary", "local"])
        print(json.dumps(lb.get_status(), ensure_ascii=False, indent=2))
