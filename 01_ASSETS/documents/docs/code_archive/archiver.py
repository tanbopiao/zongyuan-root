#!/usr/bin/env python3
"""
元秩序归档引擎集成模块
对媒体文件执行SHA256哈希确权、链式继承、eFuse固化、锁档
"""
import hashlib
import json
import os
from datetime import datetime
from typing import Optional, Dict, Tuple
from pathlib import Path

# 常量
DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"
GENESIS_ROOT = "0" * 64

# 九大元类映射
META_CLASS_MAP = {
    "image": "M6",  # 对外交付层（图片作品）
    "video": "M6",  # 对外交付层（视频作品）
    "audio": "M6",  # 对外交付层（音频作品）
    "other": "M9",  # 元秩序基底层
}

META_CLASS_NAMES = {
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


class MediaArchiver:
    """媒体文件元秩序归档引擎"""
    
    def __init__(self, db, storage, chain_db_path: str = "/opt/storage/media/archive_chain.json"):
        self.db = db
        self.storage = storage
        self.chain_db_path = chain_db_path
        Path(chain_db_path).parent.mkdir(parents=True, exist_ok=True)
        self._load_chain()
    
    def _load_chain(self):
        """加载哈希链"""
        if os.path.exists(self.chain_db_path):
            with open(self.chain_db_path, 'r', encoding='utf-8') as f:
                self.chain = json.load(f)
        else:
            self.chain = {
                "genesis_root": GENESIS_ROOT,
                "current_root": GENESIS_ROOT,
                "total_archived": 0,
                "blocks": []
            }
            self._save_chain()
    
    def _save_chain(self):
        """保存哈希链"""
        with open(self.chain_db_path, 'w', encoding='utf-8') as f:
            json.dump(self.chain, f, ensure_ascii=False, indent=2)
    
    def _chain_hash(self, parent_hash: str, asset_hash: str) -> str:
        """链式继承：新根哈希 = SHA256(父哈希:资产哈希)"""
        combined = f"{parent_hash.upper()}:{asset_hash}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest().upper()
    
    def _generate_efuse_id(self, lock_level: int, asset_hash: str) -> str:
        """生成eFuse熔断位编号"""
        if lock_level < 4:
            return "N/A"
        short_hash = asset_hash[:8]
        return f"EFUSE-{lock_level}-{short_hash}"
    
    def archive_file(self, file_hash: str, lock_level: int = 4) -> Dict:
        """
        归档文件：哈希确权+链式继承+eFuse固化+数据库更新
        返回归档凭证
        """
        # 获取文件信息
        file_info = self.db.get_file_by_hash(file_hash)
        if not file_info:
            return {"success": False, "error": "文件不存在"}
        
        # 如果已经归档，直接返回
        if file_info['archive_status'] == 'archived':
            return {
                "success": True,
                "already_archived": True,
                "file_hash": file_hash,
                "root_hash": file_info.get('root_hash'),
                "efuse_id": file_info.get('efuse_id')
            }
        
        # 链式继承
        parent_hash = self.chain['current_root']
        new_root = self._chain_hash(parent_hash, file_hash)
        
        # eFuse编号
        efuse_id = self._generate_efuse_id(lock_level, file_hash)
        
        # 元类
        meta_class = META_CLASS_MAP.get(file_info['file_type'], "M9")
        meta_class_name = META_CLASS_NAMES.get(meta_class, "未知")
        
        # 构建区块
        block = {
            "index": self.chain['total_archived'] + 1,
            "file_hash": file_hash,
            "filename": file_info['filename'],
            "file_type": file_info['file_type'],
            "file_size": file_info['file_size'],
            "storage_path": file_info['storage_path'],
            "meta_class": meta_class,
            "meta_class_name": meta_class_name,
            "lock_level": lock_level,
            "parent_hash": parent_hash,
            "new_root_hash": new_root,
            "efuse_id": efuse_id,
            "did": DID,
            "trace_mark": TRACE_MARK,
            "created_at": datetime.now().isoformat(),
            "tags": file_info.get('tags', []),
            "title": file_info.get('title'),
            "prompt": file_info.get('prompt')
        }
        
        # 更新链
        self.chain['current_root'] = new_root
        self.chain['total_archived'] += 1
        self.chain['blocks'].append(block)
        self._save_chain()
        
        # 更新数据库
        self.db.update_archive_status(file_hash, 'archived', efuse_id, new_root)
        
        # 构建凭证
        credential = {
            "success": True,
            "already_archived": False,
            "asset_id": f"KD-MEDIA-{self.chain['total_archived']:06d}",
            "file_hash": file_hash,
            "filename": file_info['filename'],
            "file_type": file_info['file_type'],
            "meta_class": meta_class,
            "meta_class_name": meta_class_name,
            "lock_level": lock_level,
            "parent_hash": parent_hash,
            "new_root_hash": new_root,
            "efuse_id": efuse_id,
            "did": DID,
            "trace_mark": TRACE_MARK,
            "archived_at": datetime.now().isoformat(),
            "total_archived": self.chain['total_archived']
        }
        
        return credential
    
    def verify_file(self, file_hash: str) -> Dict:
        """验证文件完整性和链连续性"""
        file_info = self.db.get_file_by_hash(file_hash)
        if not file_info:
            return {"valid": False, "error": "文件不存在"}
        
        # 验证文件哈希
        actual_hash = self.storage.calculate_hash(file_info['storage_path'])
        hash_valid = (actual_hash.upper() == file_hash.upper())
        
        # 验证链
        chain_valid = False
        block_index = None
        for i, block in enumerate(self.chain['blocks']):
            if block['file_hash'] == file_hash:
                chain_valid = True
                block_index = i
                break
        
        return {
            "valid": hash_valid and chain_valid,
            "hash_valid": hash_valid,
            "chain_valid": chain_valid,
            "block_index": block_index,
            "file_hash": file_hash,
            "actual_hash": actual_hash,
            "stored_hash": file_hash,
            "archive_status": file_info['archive_status'],
            "efuse_id": file_info.get('efuse_id'),
            "root_hash": file_info.get('root_hash')
        }
    
    def get_chain_info(self) -> Dict:
        """获取哈希链信息"""
        return {
            "genesis_root": self.chain['genesis_root'],
            "current_root": self.chain['current_root'],
            "total_archived": self.chain['total_archived'],
            "did": DID,
            "trace_mark": TRACE_MARK
        }
    
    def get_recent_archives(self, limit: int = 20) -> list:
        """获取最近归档的文件"""
        return self.chain['blocks'][-limit:][::-1]
    
    def verify_chain_integrity(self) -> Dict:
        """验证整条哈希链的完整性"""
        errors = []
        prev_hash = self.chain['genesis_root']
        
        for i, block in enumerate(self.chain['blocks']):
            expected_root = self._chain_hash(prev_hash, block['file_hash'])
            if expected_root != block['new_root_hash']:
                errors.append({
                    "block_index": i,
                    "file_hash": block['file_hash'],
                    "expected_root": expected_root,
                    "actual_root": block['new_root_hash'],
                    "error": "哈希链断裂"
                })
            prev_hash = block['new_root_hash']
        
        return {
            "valid": len(errors) == 0,
            "total_blocks": len(self.chain['blocks']),
            "errors": errors,
            "current_root": self.chain['current_root'],
            "verified_at": datetime.now().isoformat()
        }


if __name__ == "__main__":
    # 测试
    print("元秩序归档引擎模块加载完成")
    print(f"DID: {DID}")
    print(f"溯源标识: {TRACE_MARK}")
    print(f"创世根哈希: {GENESIS_ROOT}")
