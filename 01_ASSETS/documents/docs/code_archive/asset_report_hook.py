#!/usr/bin/env python3
"""
资产自动上报中间件 V1.0
META-LAW-ASSET-REPORT-GATEWAY-V1.0 工程化落地

视频/图片资产生成后自动上报记忆网关
- 自动检测新生成的视频/图片资产
- 自动上报到云端记忆网关 (POST /api/gateway/report)
- 失败写入待同步队列，网关可达后自动补发
- 确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import json
import hashlib
import time
import os
import hmac
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

class AssetReportHook:
    """资产自动上报钩子"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.gateway_url = self.config.get('gateway_url', 'http://123.207.202.158:9120')
        self.bridge_url = self.config.get('bridge_url', 'http://127.0.0.1:9120')
        self.secret = self.config.get('secret', '')
        self.node_id = self.config.get('node_id', 'NN-WORK-001')
        self.did = self.config.get('did', 'DID-BR-000002')
        self.trace = self.config.get('trace', 'Ω₀⊂⊙∞⊂Ω')
        self.pending_dir = self.config.get('pending_dir', '/home/user/.zongyuan_root/pending_sync')
        os.makedirs(self.pending_dir, exist_ok=True)

        # 支持的资产类型
        self.video_exts = {'.mp4', '.mov', '.webm', '.avi'}
        self.image_exts = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

    def detect_asset_type(self, filepath: str) -> Optional[str]:
        """检测资产类型"""
        ext = Path(filepath).suffix.lower()
        if ext in self.video_exts:
            return 'video'
        elif ext in self.image_exts:
            return 'image'
        return None

    def compute_asset_hash(self, filepath: str) -> str:
        """计算资产SHA256哈希"""
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    def build_report_payload(self, filepath: str, asset_type: str, metadata: Optional[Dict] = None) -> Dict:
        """构建上报payload"""
        file_stat = os.stat(filepath)
        asset_hash = self.compute_asset_hash(filepath)

        payload = {
            "truth_type": "achievement",
            "asset_name": Path(filepath).name,
            "asset_type": asset_type,
            "format": Path(filepath).suffix.lower(),
            "size_bytes": file_stat.st_size,
            "sha256": asset_hash,
            "efuse_id": f"EFUSE-LV4-{asset_hash[:16].upper()}",
            "did": self.did,
            "trace": self.trace,
            "node_id": self.node_id,
            "reported_at": datetime.now(timezone.utc).isoformat(),
            "file_path": filepath
        }

        # 合并元数据
        if metadata:
            payload.update(metadata)

        return payload

    def _sign_request(self, body: str) -> Dict[str, str]:
        """生成同源协议签名头"""
        ts = str(int(time.time()))
        nonce = hashlib.sha256(f"{self.node_id}{ts}{time.time()}".encode()).hexdigest()[:16]
        sign = hmac.new(
            self.secret.encode(),
            f"{ts}|{nonce}|{body}".encode(),
            hashlib.sha256
        ).hexdigest()
        return {
            'X-Node-ID': self.node_id,
            'X-Timestamp': ts,
            'X-Nonce': nonce,
            'X-ZR-Hmac-Signature': sign,
            'X-DID': self.did
        }

    def report_to_gateway(self, payload: Dict) -> bool:
        """上报到记忆网关"""
        body = json.dumps(payload, ensure_ascii=False)
        headers = {
            'Content-Type': 'application/json',
            **self._sign_request(body)
        }

        # 优先尝试本地桥接，再尝试直连
        for url in [f"{self.bridge_url}/api/gateway/report", f"{self.gateway_url}/api/gateway/report"]:
            try:
                req = urllib.request.Request(url, data=body.encode(), method='POST', headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read().decode())
                    if resp.status == 200:
                        print(f"[上报成功] {payload['asset_name']} via {url}")
                        return True
            except urllib.error.HTTPError as e:
                print(f"[上报失败] {url}: {e.code} {e.read().decode()[:100]}")
            except Exception as e:
                print(f"[上报异常] {url}: {str(e)[:100]}")

        return False

    def save_to_pending(self, payload: Dict):
        """保存到待同步队列"""
        pending_file = os.path.join(
            self.pending_dir,
            f"pending_{int(time.time())}_{payload['sha256'][:8]}.json"
        )
        with open(pending_file, 'w') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[待同步] {payload['asset_name']} -> {pending_file}")

    def report_asset(self, filepath: str, metadata: Optional[Dict] = None) -> bool:
        """上报单个资产（主入口）"""
        asset_type = self.detect_asset_type(filepath)
        if not asset_type:
            print(f"[跳过] 不支持的资产类型: {filepath}")
            return False

        if not os.path.exists(filepath):
            print(f"[错误] 文件不存在: {filepath}")
            return False

        payload = self.build_report_payload(filepath, asset_type, metadata)

        if self.report_to_gateway(payload):
            return True
        else:
            self.save_to_pending(payload)
            return False

    def scan_and_report_directory(self, directory: str, recursive: bool = True) -> Dict:
        """扫描目录并上报所有视频/图片资产"""
        stats = {"total": 0, "success": 0, "failed": 0, "pending": 0}

        for root, dirs, files in os.walk(directory):
            for f in files:
                filepath = os.path.join(root, f)
                asset_type = self.detect_asset_type(filepath)
                if asset_type:
                    stats["total"] += 1
                    if self.report_asset(filepath):
                        stats["success"] += 1
                    else:
                        stats["failed"] += 1
                        stats["pending"] += 1
            if not recursive:
                break

        print(f"[扫描完成] 总计{stats['total']}，成功{stats['success']}，待同步{stats['pending']}")
        return stats

    def retry_pending(self) -> Dict:
        """重试待同步队列"""
        stats = {"total": 0, "success": 0, "failed": 0}
        pending_files = list(Path(self.pending_dir).glob('pending_*.json'))

        for pf in pending_files:
            stats["total"] += 1
            with open(pf) as f:
                payload = json.load(f)
            if self.report_to_gateway(payload):
                pf.unlink()  # 删除已上报的文件
                stats["success"] += 1
            else:
                stats["failed"] += 1

        print(f"[补发完成] 总计{stats['total']}，成功{stats['success']}，失败{stats['failed']}")
        return stats

    def get_pending_count(self) -> int:
        """获取待同步数量"""
        return len(list(Path(self.pending_dir).glob('pending_*.json')))


# CLI入口
if __name__ == "__main__":
    import sys

    hook = AssetReportHook()

    if len(sys.argv) < 2:
        print("用法: python asset_report_hook.py <command> [args]")
        print("命令:")
        print("  report <file> [metadata_json]  - 上报单个资产")
        print("  scan <directory>               - 扫描目录并上报")
        print("  retry                          - 重试待同步队列")
        print("  status                         - 查看待同步状态")
        print("  demo                           - 演示")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "report":
        filepath = sys.argv[2]
        metadata = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
        hook.report_asset(filepath, metadata)

    elif cmd == "scan":
        directory = sys.argv[2]
        hook.scan_and_report_directory(directory)

    elif cmd == "retry":
        hook.retry_pending()

    elif cmd == "status":
        print(f"待同步资产数: {hook.get_pending_count()}")
        print(f"待同步目录: {hook.pending_dir}")

    elif cmd == "demo":
        print("=== 资产自动上报演示 ===")
        # 创建测试图片
        test_file = "/tmp/test_asset_demo.png"
        with open(test_file, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        hook.report_asset(test_file, {"style": "demo", "ip_origin": "测试"})
        print(f"\n待同步数量: {hook.get_pending_count()}")
        print("（网关不可达时自动进入待同步队列，可达后自动补发）")
