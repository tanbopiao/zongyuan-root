"""
成果自动识别器 V1.0
自动识别文件系统中的新成果，支持多种识别方式。

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import os
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

from interfaces.mechanism_interfaces import (
    ResultMetadata, ResultType, MetaClass, Priority, ProcessingResult
)


@dataclass
class DetectedResult:
    """检测到的成果"""
    file_path: str
    file_name: str
    file_ext: str
    file_size: int
    modified_time: float
    content_hash: str
    is_new: bool = True
    is_modified: bool = False


class ResultDetector:
    """成果自动识别器"""

    # 支持的文件扩展名到成果类型的映射
    EXT_TYPE_MAP = {
        # 代码成果
        '.py': ResultType.CODE, '.js': ResultType.CODE, '.java': ResultType.CODE,
        '.go': ResultType.CODE, '.cpp': ResultType.CODE, '.c': ResultType.CODE,
        '.rs': ResultType.CODE, '.ts': ResultType.CODE, '.php': ResultType.CODE,
        '.rb': ResultType.CODE, '.swift': ResultType.CODE, '.kt': ResultType.CODE,
        # 文档成果
        '.md': ResultType.DOCUMENT, '.markdown': ResultType.DOCUMENT,
        '.docx': ResultType.DOCUMENT, '.doc': ResultType.DOCUMENT,
        '.pdf': ResultType.DOCUMENT, '.txt': ResultType.DOCUMENT,
        '.rst': ResultType.DOCUMENT,
        # 数据成果
        '.csv': ResultType.DATA, '.json': ResultType.DATA, '.xlsx': ResultType.DATA,
        '.xls': ResultType.DATA, '.tsv': ResultType.DATA, '.db': ResultType.DATA,
        '.sqlite': ResultType.DATA, '.parquet': ResultType.DATA,
        # 模型成果
        '.pkl': ResultType.MODEL, '.onnx': ResultType.MODEL, '.h5': ResultType.MODEL,
        '.pt': ResultType.MODEL, '.pth': ResultType.MODEL, '.pb': ResultType.MODEL,
        '.joblib': ResultType.MODEL,
        # 配置成果
        '.yaml': ResultType.CONFIG, '.yml': ResultType.CONFIG,
        '.xml': ResultType.CONFIG, '.conf': ResultType.CONFIG,
        '.ini': ResultType.CONFIG, '.toml': ResultType.CONFIG,
        '.env': ResultType.CONFIG,
        # 可视化成果
        '.html': ResultType.VISUALIZATION, '.htm': ResultType.VISUALIZATION,
        '.svg': ResultType.VISUALIZATION,
        # 多媒体成果
        '.png': ResultType.MEDIA, '.jpg': ResultType.MEDIA, '.jpeg': ResultType.MEDIA,
        '.gif': ResultType.MEDIA, '.webp': ResultType.MEDIA, '.bmp': ResultType.MEDIA,
        '.mp4': ResultType.MEDIA, '.avi': ResultType.MEDIA, '.mov': ResultType.MEDIA,
        '.mkv': ResultType.MEDIA, '.mp3': ResultType.MEDIA, '.wav': ResultType.MEDIA,
        '.ogg': ResultType.MEDIA, '.flac': ResultType.MEDIA,
        '.glb': ResultType.MEDIA, '.gltf': ResultType.MEDIA, '.obj': ResultType.MEDIA,
    }

    # 排除的目录和文件
    EXCLUDE_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv',
                     'dist', 'build', '.idea', '.vscode', '*.egg-info'}
    EXCLUDE_FILES = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}

    def __init__(self, watch_path: str = None, config: Dict = None):
        """
        初始化成果识别器

        Args:
            watch_path: 监控的根路径
            config: 配置字典
        """
        self.watch_path = watch_path or os.getcwd()
        self.config = config or {}
        self._known_hashes: Set[str] = set()
        self._known_files: Dict[str, str] = {}  # path -> hash
        self._scan_count = 0
        self._detected_count = 0

    def _calculate_hash(self, file_path: str) -> str:
        """计算文件SHA256哈希"""
        h = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            return h.hexdigest().upper()
        except (IOError, OSError):
            return ""

    def _should_exclude(self, path: str) -> bool:
        """判断是否应该排除该路径"""
        basename = os.path.basename(path)
        if basename in self.EXCLUDE_FILES:
            return True
        parts = set(path.split(os.sep))
        if parts & self.EXCLUDE_DIRS:
            return True
        return False

    def _get_result_type(self, file_ext: str) -> ResultType:
        """根据文件扩展名获取成果类型"""
        return self.EXT_TYPE_MAP.get(file_ext.lower(), ResultType.DOCUMENT)

    def scan_directory(self, path: str = None, recursive: bool = True) -> ProcessingResult:
        """
        扫描目录，识别新成果

        Args:
            path: 扫描路径，默认使用watch_path
            recursive: 是否递归扫描

        Returns:
            ProcessingResult，data中包含detected_results列表
        """
        start_time = time.time()
        scan_path = path or self.watch_path
        detected: List[DetectedResult] = []
        errors: List[str] = []

        if not os.path.exists(scan_path):
            return ProcessingResult(
                success=False,
                message=f"扫描路径不存在: {scan_path}",
                errors=[f"Path not found: {scan_path}"]
            )

        try:
            if recursive:
                for root, dirs, files in os.walk(scan_path):
                    # 过滤排除目录
                    dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        if self._should_exclude(fpath):
                            continue
                        result = self._check_file(fpath)
                        if result:
                            detected.append(result)
            else:
                for fname in os.listdir(scan_path):
                    fpath = os.path.join(scan_path, fname)
                    if os.path.isfile(fpath) and not self._should_exclude(fpath):
                        result = self._check_file(fpath)
                        if result:
                            detected.append(result)

        except Exception as e:
            errors.append(f"扫描异常: {str(e)}")

        self._scan_count += 1
        self._detected_count += len(detected)
        elapsed = (time.time() - start_time) * 1000

        return ProcessingResult(
            success=True,
            message=f"扫描完成，发现 {len(detected)} 个新/变更成果",
            data={
                "detected_results": [self._detected_to_dict(r) for r in detected],
                "scan_path": scan_path,
                "scan_count": self._scan_count,
                "total_detected": self._detected_count,
            },
            errors=errors,
            processing_time_ms=elapsed
        )

    def _check_file(self, file_path: str) -> Optional[DetectedResult]:
        """检查单个文件是否为新/变更成果"""
        try:
            stat = os.stat(file_path)
            file_ext = os.path.splitext(file_path)[1]
            content_hash = self._calculate_hash(file_path)

            if not content_hash:
                return None

            is_new = file_path not in self._known_files
            is_modified = (not is_new and self._known_files.get(file_path) != content_hash)

            if is_new or is_modified:
                self._known_files[file_path] = content_hash
                self._known_hashes.add(content_hash)
                return DetectedResult(
                    file_path=file_path,
                    file_name=os.path.basename(file_path),
                    file_ext=file_ext,
                    file_size=stat.st_size,
                    modified_time=stat.st_mtime,
                    content_hash=content_hash,
                    is_new=is_new,
                    is_modified=is_modified
                )
            return None

        except (IOError, OSError):
            return None

    def _detected_to_dict(self, d: DetectedResult) -> Dict:
        """将DetectedResult转为字典"""
        return {
            "file_path": d.file_path,
            "file_name": d.file_name,
            "file_ext": d.file_ext,
            "file_size": d.file_size,
            "file_size_human": self._human_size(d.file_size),
            "modified_time": datetime.fromtimestamp(d.modified_time).isoformat(),
            "content_hash": d.content_hash,
            "is_new": d.is_new,
            "is_modified": d.is_modified,
            "result_type": self._get_result_type(d.file_ext).value,
        }

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """人类可读的文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def build_metadata(self, detected: DetectedResult) -> ResultMetadata:
        """从检测结果构建成果元数据"""
        result_type = self._get_result_type(detected.file_ext)
        # 简单的元类推断
        meta_class = self._infer_meta_class(detected.file_name, result_type)
        # 简单的优先级推断
        priority = self._infer_priority(detected.file_name, detected.file_size)

        return ResultMetadata(
            result_id=f"RESULT-{detected.content_hash[:12]}",
            result_name=os.path.splitext(detected.file_name)[0],
            result_type=result_type,
            meta_class=meta_class,
            format=detected.file_ext.lstrip('.'),
            size_bytes=detected.file_size,
            created_at=datetime.fromtimestamp(detected.modified_time).isoformat(),
            modified_at=datetime.fromtimestamp(detected.modified_time).isoformat(),
            creator="ZONGYUAN-ROOT-AutoDetect",
            source_system="filesystem",
            version="V1.0",
            tags=self._extract_tags(detected.file_name),
            priority=priority,
            confidence=0.85,
            content_hash=detected.content_hash,
        )

    def _infer_meta_class(self, file_name: str, result_type: ResultType) -> MetaClass:
        """推断元类"""
        name_lower = file_name.lower()
        if any(k in name_lower for k in ['机制', '架构', '协议', '体系', '内核', '引擎']):
            return MetaClass.M2_KERNEL
        if any(k in name_lower for k in ['理论', '白皮书', '研究', '分析']):
            return MetaClass.M4_THEORY
        if any(k in name_lower for k in ['产品', '方案', '设计', 'SOP']):
            return MetaClass.M5_PRODUCT
        if any(k in name_lower for k in ['报告', '交付', '文档']):
            return MetaClass.M6_DELIVERY
        if any(k in name_lower for k in ['自动化', '调度', '定时', '巡检']):
            return MetaClass.M7_AUTOMATION
        if result_type == ResultType.CODE:
            return MetaClass.M1_ALGORITHM
        if result_type == ResultType.DATA:
            return MetaClass.M9_FOUNDATION
        return MetaClass.M4_THEORY

    def _infer_priority(self, file_name: str, file_size: int) -> Priority:
        """推断优先级"""
        name_lower = file_name.lower()
        if any(k in name_lower for k in ['核心', '关键', '紧急', '重要', 'V1.0', '正式']):
            return Priority.P0_CRITICAL
        if any(k in name_lower for k in ['机制', '架构', '协议', '体系']):
            return Priority.P1_HIGH
        if file_size > 100 * 1024:  # >100KB
            return Priority.P1_HIGH
        return Priority.P2_MEDIUM

    def _extract_tags(self, file_name: str) -> List[str]:
        """从文件名提取标签"""
        tags = []
        keywords = ['机制', '架构', '协议', '体系', '理论', '白皮书', '研究',
                    '分析', '报告', '产品', '方案', '设计', 'SOP', '自动化',
                    '物理', '空间', '世界模型', '多模型', '场频', '边缘设备',
                    '具身', '可视化', '成果', '锁档', '归档', '断点']
        name_lower = file_name.lower()
        for kw in keywords:
            if kw.lower() in name_lower:
                tags.append(kw)
        return tags[:5]  # 最多5个标签

    def get_status(self) -> Dict:
        """获取识别器状态"""
        return {
            "watch_path": self.watch_path,
            "scan_count": self._scan_count,
            "total_detected": self._detected_count,
            "known_files_count": len(self._known_files),
            "known_hashes_count": len(self._known_hashes),
            "supported_extensions": len(self.EXT_TYPE_MAP),
            "status": "running",
        }
