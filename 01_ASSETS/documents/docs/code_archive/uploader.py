#!/usr/bin/env python3
"""
本地媒体文件上传器
监控指定目录，自动上传新文件到云服务器媒体归档系统
支持断点续传、失败重试、批量上传
"""
import os
import sys
import json
import time
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

# 配置
DEFAULT_CONFIG = {
    "api_url": "https://www.huodouai.com/api",
    "api_token": "ZR-MEDIA-2026-OMEGA-d04bb54ba2a55a7d",
    "watch_dir": "~/Doubao/media-upload",
    "uploaded_dir": "~/Doubao/media-uploaded",
    "failed_dir": "~/Doubao/media-failed",
    "scan_interval": 30,  # 秒
    "max_retries": 3,
    "retry_delay": 10,  # 秒
    "chunk_size": 8 * 1024 * 1024,  # 8MB
    "allowed_extensions": {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp',
                            '.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv',
                            '.mp3', '.wav', '.ogg', '.flac', '.m4a'},
    "state_file": "~/.media-uploader-state.json"
}

class MediaUploader:
    """媒体文件上传器"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.state = self._load_state()
        self._ensure_dirs()
    
    def _load_config(self, config_path: str = None) -> dict:
        """加载配置"""
        config = DEFAULT_CONFIG.copy()
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                config.update(user_config)
        # 展开路径
        for key in ['watch_dir', 'uploaded_dir', 'failed_dir', 'state_file']:
            config[key] = os.path.expanduser(config[key])
        return config
    
    def _load_state(self) -> dict:
        """加载上传状态"""
        state_file = self.config['state_file']
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "uploaded": {},  # file_hash -> {path, time, result}
            "failed": {},    # file_hash -> {path, time, error, retries}
            "last_scan": None,
            "total_uploaded": 0,
            "total_failed": 0
        }
    
    def _save_state(self):
        """保存状态"""
        state_file = self.config['state_file']
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def _ensure_dirs(self):
        """确保目录存在"""
        for key in ['watch_dir', 'uploaded_dir', 'failed_dir']:
            os.makedirs(self.config[key], exist_ok=True)
    
    def calculate_hash(self, file_path: str) -> str:
        """计算文件SHA256"""
        h = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest().upper()
    
    def is_allowed_file(self, filename: str) -> bool:
        """检查是否是允许的文件类型"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.config['allowed_extensions']
    
    def scan_directory(self) -> List[str]:
        """扫描监控目录，返回待上传的文件列表"""
        watch_dir = self.config['watch_dir']
        files = []
        
        for root, dirs, filenames in os.walk(watch_dir):
            for filename in filenames:
                if not self.is_allowed_file(filename):
                    continue
                full_path = os.path.join(root, filename)
                # 跳过临时文件
                if filename.endswith(('.tmp', '.crdownload', '.part')):
                    continue
                # 检查文件是否稳定（大小不再变化）
                if self._is_file_stable(full_path):
                    files.append(full_path)
        
        return files
    
    def _is_file_stable(self, file_path: str, wait_seconds: int = 2) -> bool:
        """检查文件是否稳定（大小不再变化，避免上传正在写入的文件）"""
        try:
            size1 = os.path.getsize(file_path)
            time.sleep(wait_seconds)
            size2 = os.path.getsize(file_path)
            return size1 == size2 and size1 > 0
        except:
            return False
    
    def upload_file(self, file_path: str) -> Dict:
        """
        上传单个文件
        返回上传结果
        """
        file_hash = self.calculate_hash(file_path)
        filename = os.path.basename(file_path)
        
        # 检查是否已上传
        if file_hash in self.state['uploaded']:
            return {
                "success": True,
                "skipped": True,
                "file_hash": file_hash,
                "filename": filename,
                "message": "文件已上传，跳过"
            }
        
        # 检查失败次数
        if file_hash in self.state['failed']:
            retries = self.state['failed'][file_hash].get('retries', 0)
            if retries >= self.config['max_retries']:
                return {
                    "success": False,
                    "file_hash": file_hash,
                    "filename": filename,
                    "message": f"已达到最大重试次数 ({self.config['max_retries']})"
                }
        
        # 执行上传
        url = f"{self.config['api_url']}/upload"
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f)}
                data = {
                    'token': self.config['api_token'],
                    'source': 'doubao-app',
                    'title': filename
                }
                
                response = requests.post(
                    url,
                    files=files,
                    data=data,
                    timeout=300  # 5分钟超时
                )
            
            if response.status_code == 200:
                result = response.json()
                # 记录成功
                self.state['uploaded'][file_hash] = {
                    'path': file_path,
                    'filename': filename,
                    'time': datetime.now().isoformat(),
                    'result': result
                }
                self.state['total_uploaded'] += 1
                # 从失败列表移除
                self.state['failed'].pop(file_hash, None)
                self._save_state()
                
                # 移动到已上传目录
                self._move_to_uploaded(file_path)
                
                return {
                    "success": True,
                    "file_hash": file_hash,
                    "filename": filename,
                    "result": result
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self._record_failure(file_hash, file_path, filename, error_msg)
                return {
                    "success": False,
                    "file_hash": file_hash,
                    "filename": filename,
                    "error": error_msg
                }
        
        except Exception as e:
            error_msg = str(e)
            self._record_failure(file_hash, file_path, filename, error_msg)
            return {
                "success": False,
                "file_hash": file_hash,
                "filename": filename,
                "error": error_msg
            }
    
    def _record_failure(self, file_hash: str, file_path: str, filename: str, error: str):
        """记录上传失败"""
        retries = 0
        if file_hash in self.state['failed']:
            retries = self.state['failed'][file_hash].get('retries', 0)
        
        self.state['failed'][file_hash] = {
            'path': file_path,
            'filename': filename,
            'time': datetime.now().isoformat(),
            'error': error,
            'retries': retries + 1
        }
        self.state['total_failed'] += 1
        self._save_state()
        
        # 如果达到最大重试次数，移动到失败目录
        if retries + 1 >= self.config['max_retries']:
            self._move_to_failed(file_path)
    
    def _move_to_uploaded(self, file_path: str):
        """移动文件到已上传目录"""
        try:
            dest = os.path.join(self.config['uploaded_dir'], os.path.basename(file_path))
            # 处理重名
            if os.path.exists(dest):
                name, ext = os.path.splitext(dest)
                dest = f"{name}_{int(time.time())}{ext}"
            os.rename(file_path, dest)
        except Exception as e:
            print(f"移动文件失败: {e}")
    
    def _move_to_failed(self, file_path: str):
        """移动文件到失败目录"""
        try:
            dest = os.path.join(self.config['failed_dir'], os.path.basename(file_path))
            if os.path.exists(dest):
                name, ext = os.path.splitext(dest)
                dest = f"{name}_{int(time.time())}{ext}"
            os.rename(file_path, dest)
        except Exception as e:
            print(f"移动文件失败: {e}")
    
    def run_once(self) -> Dict:
        """执行一次扫描和上传"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始扫描...")
        
        files = self.scan_directory()
        print(f"发现 {len(files)} 个待上传文件")
        
        results = []
        for file_path in files:
            filename = os.path.basename(file_path)
            print(f"上传中: {filename}")
            result = self.upload_file(file_path)
            results.append(result)
            if result['success']:
                if result.get('skipped'):
                    print(f"  ✓ 已跳过 (已上传)")
                else:
                    print(f"  ✓ 上传成功: {result['file_hash'][:8]}")
            else:
                print(f"  ✗ 上传失败: {result.get('error', '未知错误')}")
        
        self.state['last_scan'] = datetime.now().isoformat()
        self._save_state()
        
        summary = {
            "total_found": len(files),
            "success": sum(1 for r in results if r['success']),
            "failed": sum(1 for r in results if not r['success']),
            "results": results
        }
        
        print(f"扫描完成: 成功 {summary['success']}, 失败 {summary['failed']}")
        return summary
    
    def run_daemon(self):
        """守护进程模式：持续监控并上传"""
        print("=" * 60)
        print("🔥 火斗云智媒体上传器 - 守护进程模式")
        print(f"监控目录: {self.config['watch_dir']}")
        print(f"API地址: {self.config['api_url']}")
        print(f"扫描间隔: {self.config['scan_interval']}秒")
        print("=" * 60)
        
        while True:
            try:
                self.run_once()
            except Exception as e:
                print(f"扫描异常: {e}")
            
            time.sleep(self.config['scan_interval'])
    
    def get_status(self) -> Dict:
        """获取上传器状态"""
        return {
            "config": {
                "api_url": self.config['api_url'],
                "watch_dir": self.config['watch_dir'],
                "scan_interval": self.config['scan_interval']
            },
            "state": {
                "total_uploaded": self.state['total_uploaded'],
                "total_failed": self.state['total_failed'],
                "uploaded_count": len(self.state['uploaded']),
                "failed_count": len(self.state['failed']),
                "last_scan": self.state['last_scan']
            }
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="火斗云智媒体上传器")
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--once', action='store_true', help='只执行一次扫描上传')
    parser.add_argument('--daemon', action='store_true', help='守护进程模式（持续监控）')
    parser.add_argument('--status', action='store_true', help='查看状态')
    parser.add_argument('--upload', help='上传指定文件')
    
    args = parser.parse_args()
    
    uploader = MediaUploader(args.config)
    
    if args.status:
        print(json.dumps(uploader.get_status(), ensure_ascii=False, indent=2))
    elif args.upload:
        result = uploader.upload_file(args.upload)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.once:
        uploader.run_once()
    elif args.daemon:
        uploader.run_daemon()
    else:
        # 默认执行一次
        uploader.run_once()
