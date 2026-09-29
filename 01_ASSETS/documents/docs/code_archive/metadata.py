"""
资产元数据提取模块
基于KERNEL-ENTRY-0199规范：跨模式资产自动中转阶段3-元数据提取与索引
"""
import os
import json
import hashlib
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict

from .hash_verifier import HashVerifier
from .cdn_scanner import MIME_MAP, SUPPORTED_EXTENSIONS


@dataclass
class AssetMetadata:
    """资产元数据标准结构"""
    # 基础标识
    asset_id: str = ""
    asset_name: str = ""
    asset_type: str = "unknown"  # image | video | document | code | config | other
    sub_type: str = ""  # 成品图 | 关键帧 | 概念图 | 截图 | ...
    
    # 哈希与大小
    sha256: str = ""
    file_size: int = 0
    mime_type: str = ""
    
    # 媒体属性
    width: int = 0
    height: int = 0
    duration: float = 0.0  # 视频时长（秒）
    
    # 时间信息
    created_at: str = ""
    archived_at: str = ""
    
    # 来源信息
    source_mode: str = ""  # dialog | task
    source_session: str = ""
    source_url: str = ""  # 原始CDN链接
    source_prompt: str = ""  # 生成prompt（如有）
    generation_model: str = ""  # 生成模型
    
    # 存储信息
    storage_path: str = ""
    public_url: str = ""
    feishu_drive_url: str = ""
    feishu_base_record: str = ""
    archive_batch: str = ""
    
    # 确权信息
    did: str = "DID-BR-000002"
    trace_symbol: str = "Ω₀⊂⊙∞⊂Ω"
    merkle_proof: str = ""
    
    # 扩展
    custom_metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.asset_id:
            self.asset_id = f"ASSET-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(self.sha256 or self.asset_name) % 10000:04d}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.archived_at:
            self.archived_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AssetMetadata':
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class MetadataExtractor:
    """资产元数据提取器"""
    
    def __init__(self, did: str = "DID-BR-000002",
                 trace_symbol: str = "Ω₀⊂⊙∞⊂Ω"):
        self.did = did
        self.trace_symbol = trace_symbol
    
    def extract_from_file(self, file_path: str, asset_type: str = "auto",
                          sub_type: str = "", source_mode: str = "",
                          source_session: str = "", source_url: str = "",
                          source_prompt: str = "", generation_model: str = "",
                          custom_metadata: Optional[dict] = None) -> AssetMetadata:
        """
        从文件提取元数据
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        file_name = os.path.basename(file_path)
        _, ext = os.path.splitext(file_name)
        ext = ext.lower()
        
        # 自动检测资产类型
        if asset_type == "auto":
            asset_type = self._detect_asset_type(ext, file_name)
        
        # 计算哈希和大小
        sha256, file_size = HashVerifier.compute_file_hash(file_path)
        
        # 获取MIME类型
        mime_type = MIME_MAP.get(ext, "application/octet-stream")
        
        # 尝试获取图片尺寸（如果PIL可用）
        width, height = self._try_get_image_dimensions(file_path)
        
        # 尝试获取视频时长（如果ffprobe可用）
        duration = self._try_get_video_duration(file_path)
        
        # 自动检测子类型
        if not sub_type:
            sub_type = self._detect_sub_type(file_name, asset_type)
        
        metadata = AssetMetadata(
            asset_name=file_name,
            asset_type=asset_type,
            sub_type=sub_type,
            sha256=sha256,
            file_size=file_size,
            mime_type=mime_type,
            width=width,
            height=height,
            duration=duration,
            source_mode=source_mode,
            source_session=source_session,
            source_url=source_url,
            source_prompt=source_prompt,
            generation_model=generation_model,
            storage_path=os.path.abspath(file_path),
            did=self.did,
            trace_symbol=self.trace_symbol,
            custom_metadata=custom_metadata or {}
        )
        
        return metadata
    
    def extract_from_data(self, data: bytes, file_name: str,
                           asset_type: str = "auto", **kwargs) -> AssetMetadata:
        """
        从字节数据提取元数据（先保存到临时文件再提取）
        """
        import tempfile
        _, ext = os.path.splitext(file_name)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        
        try:
            metadata = self.extract_from_file(tmp_path, asset_type=asset_type, **kwargs)
            metadata.asset_name = file_name
            return metadata
        finally:
            os.unlink(tmp_path)
    
    def _detect_asset_type(self, ext: str, file_name: str) -> str:
        """根据扩展名和文件名检测资产类型"""
        for atype, exts in SUPPORTED_EXTENSIONS.items():
            if ext in exts:
                return atype
        return "unknown"
    
    def _detect_sub_type(self, file_name: str, asset_type: str) -> str:
        """根据文件名检测子类型"""
        name_lower = file_name.lower()
        
        if asset_type == "image":
            if "cdn_v" in name_lower or "成品" in name_lower:
                return "成品图"
            elif "key_" in name_lower or "关键帧" in name_lower:
                return "关键帧"
            elif "h_" in name_lower or "概念" in name_lower:
                return "概念图"
            elif "img_" in name_lower or "screenshot" in name_lower or "截图" in name_lower:
                return "截图"
            return "图片"
        elif asset_type == "video":
            return "视频"
        elif asset_type == "document":
            return "文档"
        return ""
    
    def _try_get_image_dimensions(self, file_path: str) -> tuple[int, int]:
        """尝试获取图片尺寸（PIL）"""
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                return img.width, img.height
        except Exception:
            return 0, 0
    
    def _try_get_video_duration(self, file_path: str) -> float:
        """尝试获取视频时长（ffprobe）"""
        try:
            import subprocess
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception:
            pass
        return 0.0
    
    def generate_merkle_proof(self, metadata_list: list[AssetMetadata]) -> str:
        """为一批资产生成Merkle凭证"""
        hashes = [m.sha256 for m in metadata_list if m.sha256]
        return HashVerifier.generate_merkle_hash(hashes)
