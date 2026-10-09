"""
四端归档模块
基于KERNEL-ENTRY-0199规范：跨模式资产自动中转阶段5-四端归档与审计
四端：本地存储 + 云端存储 + 飞书云盘 + 飞书Base台账
"""
import os
import json
import subprocess
import tempfile
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

import requests

from .metadata import AssetMetadata
from .hash_verifier import HashVerifier


@dataclass
class ArchiveResult:
    """归档结果"""
    success: bool
    asset_id: str = ""
    local: dict = field(default_factory=dict)
    cloud: dict = field(default_factory=dict)
    feishu_drive: dict = field(default_factory=dict)
    feishu_base: dict = field(default_factory=dict)
    merkle_proof: str = ""
    archive_batch: str = ""
    error_message: str = ""
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "asset_id": self.asset_id,
            "local": self.local,
            "cloud": self.cloud,
            "feishu_drive": self.feishu_drive,
            "feishu_base": self.feishu_base,
            "merkle_proof": self.merkle_proof,
            "archive_batch": self.archive_batch,
            "error_message": self.error_message
        }


class FourEndArchiver:
    """
    四端归档器
    端1：本地持久化存储（已在阶段2完成）
    端2：云端存储（/opt/storage，通过/api/upload上传）
    端3：飞书云盘（lark-cli drive +upload）
    端4：飞书Base台账（lark-cli base +record-batch-create）
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.cloud_config = config.get("cloud_api", {})
        self.feishu_config = config.get("feishu", {})
        self.did = config.get("identity", {}).get("did", "DID-BR-000002")
        self.trace_symbol = config.get("identity", {}).get("trace_symbol", "Ω₀⊂⊙∞⊂Ω")
    
    def archive(self, metadata: AssetMetadata, 
                archive_batch: str = "") -> ArchiveResult:
        """
        执行四端归档
        """
        result = ArchiveResult(
            asset_id=metadata.asset_id,
            archive_batch=archive_batch or f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        
        # 端1：本地存储（确认已存在）
        result.local = self._verify_local(metadata)
        
        # 端2：云端存储
        result.cloud = self._upload_to_cloud(metadata)
        
        # 端3：飞书云盘
        result.feishu_drive = self._upload_to_feishu_drive(metadata)
        
        # 端4：飞书Base台账
        result.feishu_base = self._register_to_feishu_base(metadata, result)
        
        # 生成Merkle凭证
        all_hashes = [
            metadata.sha256,
            result.cloud.get("sha256", ""),
        ]
        result.merkle_proof = HashVerifier.generate_merkle_hash([h for h in all_hashes if h])
        
        # 判断整体成功（至少本地+云端成功）
        result.success = (
            result.local.get("success", False) and
            result.cloud.get("success", False)
        )
        
        if not result.success:
            result.error_message = "四端归档部分失败，请检查各端详情"
        
        return result
    
    def _verify_local(self, metadata: AssetMetadata) -> dict:
        """端1：验证本地存储"""
        try:
            if os.path.exists(metadata.storage_path):
                sha256, size = HashVerifier.compute_file_hash(metadata.storage_path)
                return {
                    "success": sha256 == metadata.sha256,
                    "path": metadata.storage_path,
                    "sha256": sha256,
                    "file_size": size
                }
            return {"success": False, "error": "本地文件不存在"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _upload_to_cloud(self, metadata: AssetMetadata) -> dict:
        """端2：上传到云端存储"""
        try:
            upload_url = self.cloud_config.get("upload_url", "")
            token = self.cloud_config.get("capture_token", "")
            auth_header = self.cloud_config.get("auth_header", "X-Capture-Token")
            public_url_base = self.cloud_config.get("public_url_base", "")
            
            if not upload_url or not token:
                return {"success": False, "error": "云端上传配置缺失"}
            
            if not os.path.exists(metadata.storage_path):
                return {"success": False, "error": "本地文件不存在，无法上传"}
            
            # 确定bucket和subdir
            bucket = self._get_cloud_bucket(metadata.asset_type)
            subdir = datetime.now().strftime("%Y-%m-%d")
            
            with open(metadata.storage_path, 'rb') as f:
                files = {'file': (metadata.asset_name, f)}
                data = {
                    'bucket': bucket,
                    'subdir': subdir
                }
                headers = {auth_header: token}
                
                response = requests.post(upload_url, files=files, data=data, 
                                        headers=headers, timeout=60)
            
            if response.status_code == 200:
                resp_data = response.json()
                public_url = f"{public_url_base}/{bucket}/{subdir}/{metadata.asset_name}"
                return {
                    "success": True,
                    "bucket": bucket,
                    "subdir": subdir,
                    "public_url": public_url,
                    "response": resp_data
                }
            else:
                return {
                    "success": False,
                    "http_status": response.status_code,
                    "error": response.text[:500]
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_cloud_bucket(self, asset_type: str) -> str:
        """获取云端存储桶"""
        mapping = {
            "image": "images",
            "成品图": "images",
            "关键帧": "images",
            "概念图": "images",
            "video": "videos",
            "视频": "videos",
        }
        return mapping.get(asset_type, "archive")
    
    def _upload_to_feishu_drive(self, metadata: AssetMetadata) -> dict:
        """端3：上传到飞书云盘"""
        try:
            folder_token = self.feishu_config.get("drive_folder_token", "")
            cli_path = self.feishu_config.get("cli_path", "lark-cli")
            
            if not folder_token:
                return {"success": False, "error": "飞书云盘配置缺失"}
            
            if not os.path.exists(metadata.storage_path):
                return {"success": False, "error": "本地文件不存在"}
            
            # 复制到/tmp（飞书CLI安全限制）
            tmp_path = os.path.join(tempfile.gettempdir(), metadata.asset_name)
            import shutil
            shutil.copy2(metadata.storage_path, tmp_path)
            
            try:
                result = subprocess.run(
                    [cli_path, 'drive', '+upload',
                     '--file', tmp_path,
                     '--folder-token', folder_token,
                     '--as', 'user'],
                    capture_output=True, text=True, timeout=60
                )
                
                if result.returncode == 0:
                    # 解析返回的URL
                    try:
                        resp_data = json.loads(result.stdout)
                        file_token = resp_data.get('data', {}).get('file_token', '')
                        url = resp_data.get('data', {}).get('url', '')
                        return {
                            "success": True,
                            "file_token": file_token,
                            "url": url
                        }
                    except json.JSONDecodeError:
                        return {"success": True, "raw_output": result.stdout[:500]}
                else:
                    return {
                        "success": False,
                        "error": result.stderr[:500] or result.stdout[:500]
                    }
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _register_to_feishu_base(self, metadata: AssetMetadata,
                                   archive_result: ArchiveResult) -> dict:
        """端4：登记到飞书Base台账"""
        try:
            base_token = self.feishu_config.get("base_token", "")
            table_id = self.feishu_config.get("base_table_id", "")
            cli_path = self.feishu_config.get("cli_path", "lark-cli")
            
            if not base_token or not table_id:
                return {"success": False, "error": "飞书Base配置缺失"}
            
            # 构造记录数据
            record_data = {
                "作品名称": metadata.asset_name,
                "资产类型": metadata.asset_type,
                "SHA256": metadata.sha256,
                "日期": datetime.now().strftime("%Y-%m-%d"),
                "云端路径": archive_result.cloud.get("public_url", metadata.storage_path),
                "公网URL": archive_result.cloud.get("public_url", ""),
                "飞书云盘URL": archive_result.feishu_drive.get("url", ""),
                "DID": self.did,
                "对账状态": "四端归档完成" if archive_result.success else "部分归档",
                "溯源符号": self.trace_symbol,
                "归档批次": archive_result.archive_batch
            }
            
            payload = {"create_records": [record_data]}
            
            result = subprocess.run(
                [cli_path, 'base', '+record-batch-create',
                 '--base-token', base_token,
                 '--table-id', table_id,
                 '--as', 'user',
                 '--json', json.dumps(payload, ensure_ascii=False)],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode == 0:
                try:
                    resp_data = json.loads(result.stdout)
                    record_ids = resp_data.get('data', {}).get('record_id_list', [])
                    return {
                        "success": True,
                        "record_id": record_ids[0] if record_ids else "",
                        "record_ids": record_ids
                    }
                except json.JSONDecodeError:
                    return {"success": True, "raw_output": result.stdout[:500]}
            else:
                return {
                    "success": False,
                    "error": result.stderr[:500] or result.stdout[:500]
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
