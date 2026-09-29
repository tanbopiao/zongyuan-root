#!/usr/bin/env python3
"""
本地对象存储模块
按日期/类型分类存储文件，支持缩略图生成、去重、查询
"""
import os
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

# 支持的文件类型
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'}

class LocalObjectStorage:
    """本地对象存储"""
    
    def __init__(self, base_path: str = "/opt/storage/media"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.thumb_path = self.base_path / "thumbnails"
        self.thumb_path.mkdir(exist_ok=True)
    
    def _get_file_type(self, filename: str) -> str:
        """获取文件类型"""
        ext = Path(filename).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            return "image"
        elif ext in VIDEO_EXTENSIONS:
            return "video"
        elif ext in AUDIO_EXTENSIONS:
            return "audio"
        else:
            return "other"
    
    def _get_storage_path(self, filename: str, file_type: str, date_str: str = None) -> Path:
        """获取存储路径：base/type/date/filename"""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        storage_dir = self.base_path / file_type / date_str
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir / filename
    
    def calculate_hash(self, file_path: str) -> str:
        """计算文件SHA256哈希"""
        h = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest().upper()
    
    def save_file(self, source_path: str, original_filename: str = None, 
                  date_str: str = None) -> Tuple[str, str, str]:
        """
        保存文件到对象存储
        返回：(存储路径, 文件类型, SHA256哈希)
        """
        if original_filename is None:
            original_filename = os.path.basename(source_path)
        
        file_type = self._get_file_type(original_filename)
        file_hash = self.calculate_hash(source_path)
        
        # 用哈希前缀+原文件名避免重名
        ext = Path(original_filename).suffix
        safe_name = f"{file_hash[:8]}_{original_filename}"
        storage_path = self._get_storage_path(safe_name, file_type, date_str)
        
        # 如果文件已存在（相同哈希），不重复存储
        if not storage_path.exists():
            shutil.copy2(source_path, str(storage_path))
        
        return str(storage_path), file_type, file_hash
    
    def save_bytes(self, data: bytes, filename: str, 
                   date_str: str = None) -> Tuple[str, str, str]:
        """
        直接保存字节数据
        返回：(存储路径, 文件类型, SHA256哈希)
        """
        file_type = self._get_file_type(filename)
        file_hash = hashlib.sha256(data).hexdigest().upper()
        
        safe_name = f"{file_hash[:8]}_{filename}"
        storage_path = self._get_storage_path(safe_name, file_type, date_str)
        
        if not storage_path.exists():
            with open(storage_path, 'wb') as f:
                f.write(data)
        
        return str(storage_path), file_type, file_hash
    
    def get_file(self, file_hash: str) -> Optional[str]:
        """根据哈希查找文件路径"""
        for root, dirs, files in os.walk(self.base_path):
            for f in files:
                if f.startswith(file_hash[:8]):
                    return os.path.join(root, f)
        return None
    
    def list_files(self, file_type: str = None, date_str: str = None, 
                   limit: int = 100, offset: int = 0) -> list:
        """列出文件"""
        files = []
        search_path = self.base_path
        if file_type:
            search_path = search_path / file_type
            if date_str:
                search_path = search_path / date_str
        
        if not search_path.exists():
            return files
        
        for root, dirs, filenames in os.walk(search_path):
            for f in filenames:
                full_path = os.path.join(root, f)
                stat = os.stat(full_path)
                files.append({
                    'filename': f,
                    'path': full_path,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'type': self._get_file_type(f)
                })
        
        # 按修改时间倒序
        files.sort(key=lambda x: x['modified'], reverse=True)
        return files[offset:offset+limit]
    
    def get_stats(self) -> dict:
        """获取存储统计"""
        total_files = 0
        total_size = 0
        type_counts = {'image': 0, 'video': 0, 'audio': 0, 'other': 0}
        
        for root, dirs, files in os.walk(self.base_path):
            for f in files:
                if 'thumbnails' in root:
                    continue
                full_path = os.path.join(root, f)
                total_files += 1
                total_size += os.path.getsize(full_path)
                ftype = self._get_file_type(f)
                type_counts[ftype] = type_counts.get(ftype, 0) + 1
        
        return {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'type_counts': type_counts
        }
    
    def delete_file(self, file_hash: str) -> bool:
        """删除文件"""
        file_path = self.get_file(file_hash)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False


if __name__ == "__main__":
    # 测试
    storage = LocalObjectStorage("/tmp/test-storage")
    print("存储统计:", storage.get_stats())
    print("支持的图片类型:", IMAGE_EXTENSIONS)
    print("支持的视频类型:", VIDEO_EXTENSIONS)
