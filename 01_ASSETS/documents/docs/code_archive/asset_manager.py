"""
视频教学资产归档管理器
管理视频教学全链路资产：脚本/分镜表/关键帧/视频/配音
支持双库归档（ROOT只读根库+沙盒动态库）
对接短剧流水线元秩序归档体系
"""
import os
import sys
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from config.settings import DATA_DIR, DID, ANCHOR
from src.common.utils import (
    setup_logger, compute_hash, generate_asset_id,
    archive_to_root, archive_to_sandbox
)

logger = setup_logger("video_asset", "video_pipeline.log")


class VideoAssetManager:
    """视频教学资产管理器"""

    ASSET_TYPES = ["script", "storyboard", "keyframe", "video", "audio", "thumbnail"]

    def __init__(self):
        self.assets = []
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保资产目录存在"""
        for asset_type in self.ASSET_TYPES:
            dir_path = os.path.join(DATA_DIR, "video_assets", asset_type)
            os.makedirs(dir_path, exist_ok=True)

    def register_asset(self, asset_type, content, metadata=None, auto_archive=True):
        """
        注册视频教学资产
        asset_type: script/storyboard/keyframe/video/audio/thumbnail
        content: 资产内容（dict或文件路径）
        metadata: 元数据
        auto_archive: 是否自动双库归档
        """
        if asset_type not in self.ASSET_TYPES:
            logger.warning(f"未知资产类型: {asset_type}")
            return None

        asset_id = generate_asset_id(f"VIDEO-{asset_type.upper()}")
        content_hash = compute_hash(content)

        asset = {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "content_hash": content_hash,
            "metadata": metadata or {},
            "status": "registered",
            "created_at": datetime.now().isoformat(),
            "did": DID,
            "anchor": ANCHOR
        }

        # 保存资产内容到文件
        self._save_asset_content(asset_id, asset_type, content)

        # 自动双库归档
        if auto_archive:
            root_record = archive_to_root(asset_type, content, {**asset, "source": "video_pipeline"})
            sandbox_record = archive_to_sandbox(asset_type, content, {**asset, "source": "video_pipeline"})
            asset["root_archive_id"] = root_record["asset_id"]
            asset["sandbox_archive_id"] = sandbox_record["asset_id"]
            asset["status"] = "archived"

        self.assets.append(asset)
        logger.info(f"视频资产已注册：{asset_id}（{asset_type}），哈希={content_hash[:16]}...")
        return asset

    def _save_asset_content(self, asset_id, asset_type, content):
        """保存资产内容到文件"""
        dir_path = os.path.join(DATA_DIR, "video_assets", asset_type)
        filepath = os.path.join(dir_path, f"{asset_id}.json")

        if isinstance(content, (dict, list)):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
        elif isinstance(content, str) and os.path.exists(content):
            # content是文件路径，复制到资产目录
            import shutil
            ext = os.path.splitext(content)[1]
            dest = os.path.join(dir_path, f"{asset_id}{ext}")
            shutil.copy2(content, dest)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(str(content))

        return filepath

    def get_asset(self, asset_id):
        """按ID查询资产"""
        for asset in self.assets:
            if asset["asset_id"] == asset_id:
                return asset
        return None

    def get_assets_by_type(self, asset_type):
        """按类型查询资产"""
        return [a for a in self.assets if a["asset_type"] == asset_type]

    def get_assets_by_knowledge_point(self, knowledge_point_id):
        """按知识点查询关联资产"""
        return [a for a in self.assets
                if a["metadata"].get("knowledge_point_id") == knowledge_point_id]

    def get_asset_content(self, asset_id):
        """获取资产内容"""
        asset = self.get_asset(asset_id)
        if not asset:
            return None
        asset_type = asset["asset_type"]
        filepath = os.path.join(DATA_DIR, "video_assets", asset_type, f"{asset_id}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def update_asset_status(self, asset_id, status, note=""):
        """更新资产状态"""
        asset = self.get_asset(asset_id)
        if not asset:
            return False
        asset["status"] = status
        asset["status_note"] = note
        asset["updated_at"] = datetime.now().isoformat()
        logger.info(f"资产状态更新：{asset_id} -> {status}")
        return True

    def verify_asset_integrity(self, asset_id):
        """验证资产完整性（哈希校验）"""
        asset = self.get_asset(asset_id)
        if not asset:
            return {"verified": False, "error": "资产不存在"}

        content = self.get_asset_content(asset_id)
        if content is None:
            return {"verified": False, "error": "资产内容文件不存在"}

        actual_hash = compute_hash(content)
        expected_hash = asset["content_hash"]
        return {
            "verified": actual_hash == expected_hash,
            "asset_id": asset_id,
            "expected_hash": expected_hash,
            "actual_hash": actual_hash,
            "asset_type": asset["asset_type"],
            "status": asset["status"]
        }

    def get_asset_stats(self):
        """获取资产统计"""
        stats = {
            "total_assets": len(self.assets),
            "by_type": {},
            "by_status": {},
            "archived_count": len([a for a in self.assets if a["status"] == "archived"]),
            "verified_count": 0
        }
        for asset in self.assets:
            atype = asset["asset_type"]
            status = asset["status"]
            stats["by_type"][atype] = stats["by_type"].get(atype, 0) + 1
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        return stats

    def export_asset_manifest(self):
        """导出资产清单（台账）"""
        manifest = {
            "manifest_id": generate_asset_id("VIDEO-MANIFEST"),
            "generated_at": datetime.now().isoformat(),
            "total_assets": len(self.assets),
            "did": DID,
            "anchor": ANCHOR,
            "assets": [
                {
                    "asset_id": a["asset_id"],
                    "asset_type": a["asset_type"],
                    "content_hash": a["content_hash"],
                    "status": a["status"],
                    "created_at": a["created_at"],
                    "metadata": a["metadata"]
                }
                for a in self.assets
            ]
        }
        # 计算清单哈希
        manifest["manifest_hash"] = compute_hash(manifest)
        return manifest

    def save_all(self):
        """保存所有资产索引"""
        filepath = os.path.join(DATA_DIR, "video_assets_index.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.assets, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存{len(self.assets)}个视频资产索引至{filepath}")
        return filepath
