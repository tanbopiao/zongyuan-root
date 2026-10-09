"""
元秩序归档集成器 V1.0
所有机制通用的元秩序归档组件，支持四层结构化拆分、九大元类归类、SHA256哈希确权、链式继承、eFuse熔断。

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import os
import json
import hashlib
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ArchiveResult:
    """归档结果"""
    success: bool
    asset_id: str = ""
    asset_name: str = ""
    meta_class: str = ""
    lock_level: int = 0
    asset_hash: str = ""
    parent_hash: str = ""
    new_root_hash: str = ""
    efuse_id: str = ""
    did: str = "DID-BR-000002"
    trace_mark: str = "Ω₀⊂⊙∞⊂Ω"
    created_at: str = ""
    content_length: int = 0
    message: str = ""
    errors: List[str] = field(default_factory=list)


@dataclass
class FourLayerStructure:
    """四层结构化拆分结果"""
    layer1_metadata: Dict = field(default_factory=dict)   # L1 元数据层
    layer2_content: Dict = field(default_factory=dict)     # L2 内容层
    layer3_relations: Dict = field(default_factory=dict)   # L3 关系层
    layer4_truth: Dict = field(default_factory=dict)       # L4 真值层


class MetaOrderArchiver:
    """元秩序归档集成器"""

    # 九大元类定义
    META_CLASSES = {
        "M1": "算法架构层",
        "M2": "自治内核进化层",
        "M3": "元层协议层",
        "M4": "理论体系层",
        "M5": "产品体系层",
        "M6": "对外交付层",
        "M7": "自动化调度层",
        "M8": "行业知识层",
        "M9": "元秩序基底层",
    }

    # 元类到资产ID前缀映射
    CATEGORY_PREFIX = {
        "M1": "ALGO", "M2": "KERN", "M3": "META", "M4": "THEO",
        "M5": "PROD", "M6": "DELIV", "M7": "AUTO", "M8": "INDU", "M9": "INDEX",
    }

    # 创世根哈希
    GENESIS_ROOT = "0" * 64

    # 默认锁档引擎路径
    DEFAULT_LOCK_ENGINE = (
        "/home/user/.super_doubao/super-doubao-runtime/workspace/"
        ".user_skills/meta-order-archive/scripts/archive_lock_engine.py"
    )

    def __init__(self, lock_engine_path: str = None, output_dir: str = None,
                 config: Dict = None):
        """
        初始化元秩序归档器

        Args:
            lock_engine_path: 锁档引擎脚本路径
            output_dir: 归档输出目录
            config: 配置字典
        """
        self.config = config or {}
        self.lock_engine_path = lock_engine_path or self.DEFAULT_LOCK_ENGINE
        self.output_dir = output_dir or os.path.join(os.getcwd(), "archive_output")
        self._archive_count = 0
        self._success_count = 0
        self._root_hash = self.GENESIS_ROOT
        self._ledger: List[Dict] = []

        os.makedirs(self.output_dir, exist_ok=True)

    def archive(self, content: str, asset_name: str,
                meta_class: str = "M4", lock_level: int = 5,
                parent_hash: str = None) -> ArchiveResult:
        """
        执行完整归档锁档流程

        Args:
            content: 归档内容（文本）
            asset_name: 资产名称
            meta_class: 元类（M1-M9）
            lock_level: 锁档等级（1-8）
            parent_hash: 父块哈希，默认使用当前根哈希

        Returns:
            ArchiveResult归档结果
        """
        start_time = datetime.now()

        # 验证元类
        if meta_class not in self.META_CLASSES:
            meta_class = "M4"

        # 验证锁档等级
        lock_level = max(1, min(8, lock_level))

        # 使用当前根哈希作为父哈希
        if parent_hash is None:
            parent_hash = self._root_hash

        try:
            # 第一步：四层结构化拆分
            structure = self._four_layer_split(content, asset_name, meta_class)

            # 第二步：计算哈希
            asset_hash = self._sha256_string(content)
            new_root_hash = self._chain_hash(parent_hash, asset_hash)

            # 第三步：生成资产ID
            asset_id = self._generate_asset_id(meta_class)

            # 第四步：eFuse熔断位（Lv4+）
            efuse_id = self._generate_efuse_id(lock_level, asset_hash)

            # 第五步：保存归档文件
            archive_file = self._save_archive_file(
                content, asset_name, asset_id, meta_class,
                lock_level, asset_hash, parent_hash, new_root_hash,
                efuse_id, structure
            )

            # 第六步：尝试调用锁档引擎（如果可用）
            engine_result = self._call_lock_engine(
                content, asset_name, meta_class, lock_level, parent_hash
            )
            if engine_result:
                asset_id = engine_result.get("asset_id", asset_id)
                asset_hash = engine_result.get("asset_hash", asset_hash)
                new_root_hash = engine_result.get("new_root_hash", new_root_hash)
                efuse_id = engine_result.get("efuse_id", efuse_id)

            # 第七步：更新全局台账
            self._root_hash = new_root_hash
            ledger_entry = {
                "asset_id": asset_id,
                "asset_name": asset_name,
                "meta_class": meta_class,
                "lock_level": lock_level,
                "asset_hash": asset_hash,
                "parent_hash": parent_hash,
                "new_root_hash": new_root_hash,
                "efuse_id": efuse_id,
                "created_at": datetime.now().isoformat(),
                "content_length": len(content),
            }
            self._ledger.append(ledger_entry)
            self._archive_count += 1
            self._success_count += 1

            return ArchiveResult(
                success=True,
                asset_id=asset_id,
                asset_name=asset_name,
                meta_class=meta_class,
                lock_level=lock_level,
                asset_hash=asset_hash,
                parent_hash=parent_hash,
                new_root_hash=new_root_hash,
                efuse_id=efuse_id,
                created_at=datetime.now().isoformat(),
                content_length=len(content),
                message=f"归档成功: {asset_id} (Lv{lock_level})",
            )

        except Exception as e:
            self._archive_count += 1
            return ArchiveResult(
                success=False,
                asset_name=asset_name,
                meta_class=meta_class,
                lock_level=lock_level,
                message=f"归档失败: {str(e)}",
                errors=[str(e)],
            )

    def archive_file(self, file_path: str, asset_name: str = None,
                     meta_class: str = "M4", lock_level: int = 5) -> ArchiveResult:
        """
        归档文件

        Args:
            file_path: 文件路径
            asset_name: 资产名称（默认使用文件名）
            meta_class: 元类
            lock_level: 锁档等级

        Returns:
            ArchiveResult归档结果
        """
        if not os.path.exists(file_path):
            return ArchiveResult(
                success=False,
                message=f"文件不存在: {file_path}",
                errors=[f"File not found: {file_path}"],
            )

        if asset_name is None:
            asset_name = os.path.splitext(os.path.basename(file_path))[0]

        # 读取文件内容（文本文件）
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return ArchiveResult(
                success=False,
                message=f"文件读取失败: {str(e)}",
                errors=[str(e)],
            )

        return self.archive(content, asset_name, meta_class, lock_level)

    def _four_layer_split(self, content: str, asset_name: str,
                           meta_class: str) -> FourLayerStructure:
        """四层结构化拆分"""
        structure = FourLayerStructure()

        # L1 元数据层
        structure.layer1_metadata = {
            "asset_name": asset_name,
            "meta_class": meta_class,
            "meta_class_name": self.META_CLASSES.get(meta_class, "未知"),
            "did": "DID-BR-000002",
            "trace_mark": "Ω₀⊂⊙∞⊂Ω",
            "created_at": datetime.now().isoformat(),
            "format": "text",
            "content_length": len(content),
        }

        # L2 内容层
        structure.layer2_content = {
            "raw_content_hash": self._sha256_string(content),
            "content_preview": content[:500],
            "line_count": content.count('\n') + 1,
            "char_count": len(content),
            "sections": self._extract_sections(content),
        }

        # L3 关系层
        structure.layer3_relations = {
            "entities": self._extract_entities(content),
            "keywords": self._extract_keywords(content),
            "references": self._extract_references(content),
        }

        # L4 真值层
        structure.layer4_truth = {
            "confidence": 0.85,
            "source": "auto_archive",
            "truth_type": "data",
            "verification_status": "pending",
        }

        return structure

    def _extract_sections(self, content: str) -> List[Dict]:
        """提取章节结构"""
        sections = []
        lines = content.split('\n')
        current_section = None

        for line in lines:
            # 匹配标题
            import re
            heading_match = re.match(r'^(#{1,4})\s+(.+)$', line)
            if heading_match:
                if current_section:
                    sections.append(current_section)
                current_section = {
                    "level": len(heading_match.group(1)),
                    "title": heading_match.group(2).strip(),
                    "content_lines": 0,
                }
            elif current_section:
                if line.strip():
                    current_section["content_lines"] += 1

        if current_section:
            sections.append(current_section)

        return sections[:20]  # 最多20个章节

    def _extract_entities(self, content: str) -> List[str]:
        """简单实体提取（基于关键词）"""
        import re
        # 提取大写缩写和专有名词
        entities = re.findall(r'\b[A-Z]{2,}(?:-[A-Z]+)?\b', content)
        # 去重并限制数量
        unique_entities = list(dict.fromkeys(entities))[:20]
        return unique_entities

    def _extract_keywords(self, content: str) -> List[str]:
        """简单关键词提取"""
        import re
        # 提取中文关键词（2-6字）
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,6}', content)
        # 简单频率统计
        from collections import Counter
        freq = Counter(keywords)
        # 过滤常见词
        stop_words = {'的', '了', '是', '在', '和', '与', '及', '等', '为', '以', '由', '对', '中', '上', '下', '内', '外', '前', '后'}
        filtered = [(w, c) for w, c in freq.most_common(50) if w not in stop_words]
        return [w for w, c in filtered[:20]]

    def _extract_references(self, content: str) -> List[str]:
        """提取引用链接"""
        import re
        urls = re.findall(r'https?://[^\s\)]+', content)
        return list(dict.fromkeys(urls))[:10]

    def _call_lock_engine(self, content: str, asset_name: str,
                           meta_class: str, lock_level: int,
                           parent_hash: str) -> Optional[Dict]:
        """调用锁档引擎（如果可用）"""
        if not os.path.exists(self.lock_engine_path):
            return None

        try:
            # 将内容写入临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_file = f.name

            try:
                result = subprocess.run(
                    [
                        "python3", self.lock_engine_path,
                        "--file", temp_file,
                        "--parent-hash", parent_hash,
                        "--asset-name", asset_name,
                        "--meta-class", meta_class,
                        "--lock-level", str(lock_level),
                        "--format", "json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    # 解析JSON输出（可能包含文本和JSON混合）
                    import re
                    json_match = re.search(r'\{.*\}', result.stdout, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
            finally:
                os.unlink(temp_file)

        except Exception:
            pass

        return None

    def _save_archive_file(self, content: str, asset_name: str,
                            asset_id: str, meta_class: str,
                            lock_level: int, asset_hash: str,
                            parent_hash: str, new_root_hash: str,
                            efuse_id: str,
                            structure: FourLayerStructure) -> str:
        """保存归档文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{asset_id}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        archive_data = {
            "asset_id": asset_id,
            "asset_name": asset_name,
            "meta_class": meta_class,
            "meta_class_name": self.META_CLASSES.get(meta_class, "未知"),
            "lock_level": lock_level,
            "asset_hash": asset_hash,
            "parent_hash": parent_hash,
            "new_root_hash": new_root_hash,
            "efuse_id": efuse_id,
            "did": "DID-BR-000002",
            "trace_mark": "Ω₀⊂⊙∞⊂Ω",
            "created_at": datetime.now().isoformat(),
            "content_length": len(content),
            "four_layer_structure": {
                "layer1_metadata": structure.layer1_metadata,
                "layer2_content": structure.layer2_content,
                "layer3_relations": structure.layer3_relations,
                "layer4_truth": structure.layer4_truth,
            },
            "content": content,
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(archive_data, f, ensure_ascii=False, indent=2)

        return filepath

    def verify_hash(self, content: str, expected_hash: str) -> bool:
        """验证内容哈希"""
        actual_hash = self._sha256_string(content)
        return actual_hash.upper() == expected_hash.upper()

    def verify_chain(self, asset_hash: str, parent_hash: str,
                     expected_root_hash: str) -> bool:
        """验证链式继承"""
        computed_root = self._chain_hash(parent_hash, asset_hash)
        return computed_root.upper() == expected_root_hash.upper()

    def get_ledger(self) -> List[Dict]:
        """获取全局台账"""
        return self._ledger.copy()

    def get_root_hash(self) -> str:
        """获取当前根哈希"""
        return self._root_hash

    def get_stats(self) -> Dict:
        """获取归档器统计"""
        return {
            "total_archives": self._archive_count,
            "success_count": self._success_count,
            "fail_count": self._archive_count - self._success_count,
            "success_rate": (self._success_count / self._archive_count * 100) if self._archive_count > 0 else 0,
            "current_root_hash": self._root_hash,
            "ledger_entries": len(self._ledger),
            "output_dir": self.output_dir,
            "lock_engine_available": os.path.exists(self.lock_engine_path),
            "status": "running",
        }

    @staticmethod
    def _sha256_string(s: str) -> str:
        """计算字符串SHA256"""
        return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()

    @staticmethod
    def _chain_hash(parent_hash: str, asset_hash: str) -> str:
        """链式继承哈希"""
        combined = f"{parent_hash.upper()}:{asset_hash}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest().upper()

    @staticmethod
    def _generate_asset_id(meta_class: str) -> str:
        """生成资产ID"""
        import uuid
        prefix = MetaOrderArchiver.CATEGORY_PREFIX.get(meta_class, "ASSET")
        seq = uuid.uuid4().int % 10000
        return f"KD-{prefix}-{seq:04d}"

    @staticmethod
    def _generate_efuse_id(lock_level: int, asset_hash: str) -> str:
        """生成eFuse熔断位编号"""
        if lock_level < 4:
            return "N/A"
        short_hash = asset_hash[:8]
        return f"EFUSE-{lock_level}-{short_hash}"
