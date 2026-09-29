"""
CDN链接扫描与抓取模块
基于KERNEL-ENTRY-0199规范：跨模式资产自动中转阶段1-资产捕获
"""
import re
import os
import hashlib
import tempfile
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests


# CDN链接正则模式
CDN_PATTERNS = [
    r'https?://aka\.doubaocdn\.com/s/[a-zA-Z0-9]+',
    r'https?://[a-zA-Z0-9.-]+\.(?:png|jpg|jpeg|gif|webp|mp4|mov|avi|mkv)',
    r'https?://drama\.huodouai\.com/(?:images|videos|archive)/[^\s"\'<>]+',
]

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {
    'image': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'],
    'video': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
    'document': ['.pdf', '.doc', '.docx', '.txt', '.md', '.json'],
    'archive': ['.zip', '.tar', '.gz', '.7z']
}

# MIME类型映射
MIME_MAP = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
    '.mp4': 'video/mp4',
    '.mov': 'video/quicktime',
    '.avi': 'video/x-msvideo',
    '.mkv': 'video/x-matroska',
    '.webm': 'video/webm',
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.json': 'application/json',
    '.zip': 'application/zip',
    '.tar': 'application/x-tar',
    '.gz': 'application/gzip',
    '.7z': 'application/x-7z-compressed'
}


@dataclass
class CDNScannedAsset:
    """CDN扫描到的资产"""
    url: str
    asset_type: str = "unknown"  # image | video | document | archive | unknown
    file_extension: str = ""
    mime_type: str = ""
    file_name: str = ""
    detected_at: str = ""
    
    def __post_init__(self):
        if not self.detected_at:
            self.detected_at = datetime.now().isoformat()


@dataclass
class CDNFetchResult:
    """CDN抓取结果"""
    success: bool
    url: str
    raw_data: Optional[bytes] = None
    file_size: int = 0
    content_type: str = ""
    sha256: str = ""
    error_message: str = ""
    http_status: int = 0
    fetched_at: str = ""
    
    def __post_init__(self):
        if not self.fetched_at:
            self.fetched_at = datetime.now().isoformat()


class CDNScanner:
    """CDN链接扫描器"""
    
    def __init__(self, patterns: Optional[list[str]] = None):
        self.patterns = patterns or CDN_PATTERNS
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.patterns]
    
    def scan_text(self, text: str) -> list[CDNScannedAsset]:
        """从文本中扫描CDN链接"""
        if not text:
            return []
        
        found_urls = set()
        for pattern in self._compiled_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                found_urls.add(match)
        
        assets = []
        for url in found_urls:
            asset = self._classify_url(url)
            assets.append(asset)
        
        return assets
    
    def scan_list(self, urls: list[str]) -> list[CDNScannedAsset]:
        """从URL列表中扫描并分类"""
        assets = []
        for url in urls:
            if url and self._is_valid_url(url):
                asset = self._classify_url(url)
                assets.append(asset)
        return assets
    
    def _classify_url(self, url: str) -> CDNScannedAsset:
        """分类URL对应的资产类型"""
        parsed = urlparse(url)
        path = parsed.path
        file_name = os.path.basename(path)
        _, ext = os.path.splitext(file_name)
        ext = ext.lower()
        
        asset_type = "unknown"
        for atype, exts in SUPPORTED_EXTENSIONS.items():
            if ext in exts:
                asset_type = atype
                break
        
        mime_type = MIME_MAP.get(ext, "")
        
        return CDNScannedAsset(
            url=url,
            asset_type=asset_type,
            file_extension=ext,
            mime_type=mime_type,
            file_name=file_name or f"asset_{hash(url) % 10000}{ext}"
        )
    
    def _is_valid_url(self, url: str) -> bool:
        """检查URL是否有效"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False


class CDNFetcher:
    """CDN资源抓取器"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3,
                 user_agent: str = "ZONGYUAN-ROOT-Bridge/1.0"):
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
    
    def fetch(self, url: str) -> CDNFetchResult:
        """
        抓取CDN资源
        返回：CDNFetchResult（包含原始数据、大小、SHA256等）
        """
        last_error = ""
        
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout, stream=True)
                
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                    if response.status_code in [404, 410]:
                        # 404不重试
                        break
                    continue
                
                # 读取数据
                raw_data = response.content
                file_size = len(raw_data)
                
                if file_size == 0:
                    last_error = "文件大小为0"
                    continue
                
                # 计算SHA256
                sha256 = hashlib.sha256(raw_data).hexdigest().upper()
                
                return CDNFetchResult(
                    success=True,
                    url=url,
                    raw_data=raw_data,
                    file_size=file_size,
                    content_type=response.headers.get('Content-Type', ''),
                    sha256=sha256,
                    http_status=response.status_code
                )
                
            except requests.exceptions.Timeout:
                last_error = f"请求超时（尝试{attempt}/{self.max_retries}）"
            except requests.exceptions.ConnectionError:
                last_error = f"连接错误（尝试{attempt}/{self.max_retries}）"
            except Exception as e:
                last_error = f"抓取异常: {str(e)}"
                break
        
        return CDNFetchResult(
            success=False,
            url=url,
            error_message=last_error
        )
    
    def fetch_to_file(self, url: str, output_path: str) -> CDNFetchResult:
        """抓取CDN资源并保存到文件"""
        result = self.fetch(url)
        if result.success and result.raw_data:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(result.raw_data)
        return result
    
    def close(self):
        """关闭会话"""
        self.session.close()
