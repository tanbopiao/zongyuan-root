#!/usr/bin/env python3
"""
MR-022 自我识别引擎
ZONGYUAN-ROOT 自身资产真值库 + 自我识别API
端口: 9150
"""
import json
import hashlib
import subprocess
import socket
import time
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DID = 'DID-BR-000002'
ANCHOR = 'Ω₀⊂⊙∞⊂Ω'
PORT = 9150
ASSET_FILE = '/opt/ZONGYUAN-ROOT/kernel/self_asset_inventory.json'
GATEWAY_URL = 'http://127.0.0.1:9120'

class SelfAssetEngine:
    """自身资产引擎"""
    
    def __init__(self):
        self.assets = self._load_assets()
        self.last_scan = None
    
    def _load_assets(self):
        if os.path.exists(ASSET_FILE):
            with open(ASSET_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._empty_assets()
    
    def _empty_assets(self):
        return {
            "did": DID,
            "anchor": ANCHOR,
            "version": "1.0",
            "server": {
                "public_ip": "",
                "private_ip": "",
                "hostname": "",
                "provider": "tencent_cloud"
            },
            "self_ips": [],
            "ssh_keys": [],
            "listening_ports": [],
            "services": [],
            "trusted_ip_ranges": [
                "127.0.0.1/8",
                "10.0.0.0/8",
                "172.16.0.0/12",
                "192.168.0.0/16"
            ],
            "last_scan": None,
            "scan_count": 0
        }
    
    def scan(self):
        """全量扫描自身资产"""
        print("[SELF-ENGINE] 开始扫描自身资产...", flush=True)
        
        # 1. IP信息
        try:
            public_ip = subprocess.check_output(['curl', '-s', 'ifconfig.me'], timeout=5).decode().strip()
        except:
            public_ip = "123.207.202.158"
        try:
            private_ip = subprocess.check_output(['hostname', '-I'], timeout=3).decode().split()[0]
        except:
            private_ip = "10.0.0.16"
        hostname = socket.gethostname()
        
        # 2. SSH密钥
        ssh_keys = []
        auth_keys_file = '/root/.ssh/authorized_keys'
        if os.path.exists(auth_keys_file):
            with open(auth_keys_file, 'r') as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    try:
                        result = subprocess.run(
                            ['ssh-keygen', '-lf', '-'],
                            input=line.encode(), capture_output=True, timeout=3
                        )
                        if result.returncode == 0:
                            parts = result.stdout.decode().strip().split()
                            fingerprint = parts[1] if len(parts) > 1 else ""
                            comment = parts[2] if len(parts) > 2 else "no-comment"
                            # 判断是否可疑（无注释或RSA 2048）
                            is_suspicious = (comment == "no" or comment == "no-comment" or 
                                           "skey-" in comment or len(comment) < 3)
                            ssh_keys.append({
                                "line": i,
                                "fingerprint": fingerprint,
                                "comment": comment,
                                "status": "suspicious" if is_suspicious else "trusted",
                                "source": "authorized_keys"
                            })
                    except:
                        pass
        
        # 3. 监听端口
        listening_ports = []
        try:
            result = subprocess.check_output(['ss', '-tlnp'], timeout=5).decode()
            for line in result.split('\n')[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    local = parts[3]
                    if ':' in local:
                        port = local.split(':')[-1]
                        if port.isdigit() and port not in ['22', '80', '443']:
                            # 检查是否有Nginx代理
                            has_proxy = self._check_nginx_proxy(port)
                            listening_ports.append({
                                "port": int(port),
                                "bind": "0.0.0.0" if '0.0.0.0' in local else "127.0.0.1",
                                "nginx_proxied": has_proxy,
                                "exposure": "external" if '0.0.0.0' in local and not has_proxy else "internal"
                            })
        except:
            pass
        
        # 4. 服务列表
        services = []
        try:
            result = subprocess.check_output(['ps', 'aux'], timeout=5).decode()
            for line in result.split('\n'):
                if any(k in line for k in ['python3', 'llama-server', 'nginx: master', 'redis-server']):
                    if 'grep' not in line:
                        parts = line.split()
                        if len(parts) >= 11:
                            cmd = ' '.join(parts[10:13])
                            services.append(cmd[:80])
        except:
            pass
        
        # 5. 当前活跃SSH连接（识别自身出口IP）
        active_ssh_ips = []
        try:
            result = subprocess.check_output(['ss', '-tnp'], timeout=5).decode()
            for line in result.split('\n'):
                if 'ESTAB' in line and ':22' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        remote = parts[4]
                        ip = remote.split(':')[0]
                        if ip not in ['127.0.0.1', '::1'] and not ip.startswith('10.'):
                            active_ssh_ips.append(ip)
        except:
            pass
        
        # 更新资产
        self.assets.update({
            "server": {
                "public_ip": public_ip,
                "private_ip": private_ip,
                "hostname": hostname,
                "provider": "tencent_cloud"
            },
            "self_ips": list(set([public_ip, private_ip, "127.0.0.1"] + active_ssh_ips)),
            "ssh_keys": ssh_keys,
            "listening_ports": sorted(listening_ports, key=lambda x: x['port']),
            "services": list(set(services)),
            "active_ssh_ips": active_ssh_ips,
            "last_scan": datetime.now().isoformat(),
            "scan_count": self.assets.get("scan_count", 0) + 1
        })
        
        # 保存
        os.makedirs(os.path.dirname(ASSET_FILE), exist_ok=True)
        with open(ASSET_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.assets, f, ensure_ascii=False, indent=2)
        
        # 上报9120
        self._report_to_gateway()
        
        print(f"[SELF-ENGINE] 扫描完成: {len(ssh_keys)}个密钥, {len(listening_ports)}个端口, {len(self.assets['self_ips'])}个自身IP", flush=True)
        return self.assets
    
    def _check_nginx_proxy(self, port):
        """检查端口是否有Nginx代理"""
        try:
            result = subprocess.run(
                ['grep', '-rl', f'127.0.0.1:{port}', '/www/server/nginx/conf/sites/'],
                capture_output=True, timeout=3
            )
            return result.returncode == 0 and len(result.stdout) > 0
        except:
            return False
    
    def _report_to_gateway(self):
        """上报资产到9120"""
        try:
            import urllib.request
            data = {
                "key": "self_asset.inventory",
                "value": json.dumps(self.assets, ensure_ascii=False),
                "source": "self_asset_engine",
                "did": DID,
                "anchor": ANCHOR,
                "confidence": 1.0,
                "truth_type": "self_asset"
            }
            req = urllib.request.Request(
                f"{GATEWAY_URL}/api/truth/upsert",
                data=json.dumps(data).encode(),
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=5)
            print("[SELF-ENGINE] 资产已上报9120", flush=True)
        except Exception as e:
            print(f"[SELF-ENGINE] 9120上报失败: {e}", flush=True)
    
    def verify_ip(self, ip):
        """验证IP是否为自身"""
        if not ip:
            return {"is_self": False, "reason": "empty ip"}
        
        # 检查自身IP列表
        if ip in self.assets.get('self_ips', []):
            return {"is_self": True, "reason": "in self_ips list", "category": "self_ip"}
        
        # 检查内网段
        try:
            ip_parts = [int(x) for x in ip.split('.')]
            if ip_parts[0] == 10 or ip_parts[0] == 127:
                return {"is_self": True, "reason": "private/internal range", "category": "internal"}
            if ip_parts[0] == 172 and 16 <= ip_parts[1] <= 31:
                return {"is_self": True, "reason": "private range", "category": "internal"}
            if ip_parts[0] == 192 and ip_parts[1] == 168:
                return {"is_self": True, "reason": "private range", "category": "internal"}
        except:
            pass
        
        # 检查活跃SSH连接IP（可能是自身出口IP）
        if ip in self.assets.get('active_ssh_ips', []):
            return {"is_self": True, "reason": "active SSH connection (likely self exit IP)", "category": "self_exit_ip"}
        
        return {"is_self": False, "reason": "not in self asset inventory", "category": "external"}
    
    def verify_port(self, port):
        """验证端口是否为自身监听"""
        for p in self.assets.get('listening_ports', []):
            if str(p['port']) == str(port):
                return {"is_self": True, "port": p['port'], "exposure": p['exposure'], 
                        "nginx_proxied": p['nginx_proxied']}
        return {"is_self": False, "port": port, "reason": "not listening"}
    
    def verify_key(self, fingerprint):
        """验证SSH密钥指纹是否为自身"""
        for k in self.assets.get('ssh_keys', []):
            if k['fingerprint'] == fingerprint:
                return {"is_self": True, "fingerprint": fingerprint, "status": k['status'], 
                        "comment": k['comment'], "line": k['line']}
        return {"is_self": False, "fingerprint": fingerprint, "reason": "not in authorized_keys"}


class SelfVerifyHandler(BaseHTTPRequestHandler):
    engine = None
    
    def log_message(self, format, *args):
        pass  # 静默日志
    
    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        if parsed.path == '/api/self/verify':
            result = {"did": DID, "anchor": ANCHOR, "verified_at": datetime.now().isoformat()}
            
            if 'ip' in params:
                result['ip_check'] = self.engine.verify_ip(params['ip'][0])
                result['is_self'] = result['ip_check'].get('is_self', False)
            elif 'port' in params:
                result['port_check'] = self.engine.verify_port(params['port'][0])
                result['is_self'] = result['port_check'].get('is_self', False)
            elif 'key_fingerprint' in params:
                result['key_check'] = self.engine.verify_key(params['key_fingerprint'][0])
                result['is_self'] = result['key_check'].get('is_self', False)
            else:
                result['error'] = "provide ?ip= or ?port= or ?key_fingerprint="
            
            self._send_json(result)
        
        elif parsed.path == '/api/self/asset':
            self._send_json(self.engine.assets)
        
        elif parsed.path == '/health':
            self._send_json({"status": "healthy", "service": "MR-022 Self-Verify Engine", "port": PORT})
        
        else:
            self._send_json({"error": "not found", "endpoints": ["/api/self/verify", "/api/self/asset", "/health"]}, 404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/self/refresh':
            assets = self.engine.scan()
            self._send_json({"status": "ok", "scanned": True, "ssh_keys": len(assets['ssh_keys']), 
                           "ports": len(assets['listening_ports']), "self_ips": len(assets['self_ips'])})
        else:
            self._send_json({"error": "not found"}, 404)


def main():
    print("=" * 60, flush=True)
    print(f"  MR-022 自我识别引擎启动", flush=True)
    print(f"  端口: {PORT} ｜ DID: {DID}", flush=True)
    print("=" * 60, flush=True)
    
    engine = SelfAssetEngine()
    engine.scan()  # 启动时立即扫描
    
    SelfVerifyHandler.engine = engine
    server = HTTPServer(('127.0.0.1', PORT), SelfVerifyHandler)
    print(f"[SELF-ENGINE] 监听: http://127.0.0.1:{PORT}", flush=True)
    print(f"[SELF-ENGINE] 端点: /api/self/verify, /api/self/asset, /api/self/refresh", flush=True)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SELF-ENGINE] 停止", flush=True)


if __name__ == '__main__':
    main()
