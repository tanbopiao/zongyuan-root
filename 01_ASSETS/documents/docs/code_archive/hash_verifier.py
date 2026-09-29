"""
SHA256哈希校验模块
基于KERNEL-ENTRY-0199规范：跨模式资产自动中转阶段2-哈希校验与固化
"""
import os
import hashlib
from typing import Optional
from dataclasses import dataclass


@dataclass
class HashVerificationResult:
    """哈希校验结果"""
    success: bool
    file_path: str = ""
    computed_hash: str = ""
    expected_hash: str = ""
    file_size: int = 0
    error_message: str = ""
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "file_path": self.file_path,
            "computed_hash": self.computed_hash,
            "expected_hash": self.expected_hash,
            "file_size": self.file_size,
            "error_message": self.error_message
        }


class HashVerifier:
    """SHA256哈希校验器"""
    
    CHUNK_SIZE = 8192  # 8KB分块读取
    
    @staticmethod
    def compute_file_hash(file_path: str) -> tuple[str, int]:
        """
        计算文件的SHA256哈希
        返回：(哈希值, 文件大小)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        h = hashlib.sha256()
        file_size = 0
        
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(HashVerifier.CHUNK_SIZE)
                if not chunk:
                    break
                h.update(chunk)
                file_size += len(chunk)
        
        return h.hexdigest().upper(), file_size
    
    @staticmethod
    def compute_data_hash(data: bytes) -> str:
        """计算字节数据的SHA256哈希"""
        return hashlib.sha256(data).hexdigest().upper()
    
    @staticmethod
    def compute_string_hash(text: str) -> str:
        """计算字符串的SHA256哈希"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest().upper()
    
    @staticmethod
    def verify_file(file_path: str, expected_hash: str) -> HashVerificationResult:
        """
        校验文件哈希是否匹配
        """
        try:
            computed_hash, file_size = HashVerifier.compute_file_hash(file_path)
            expected_upper = expected_hash.upper()
            
            if computed_hash == expected_upper:
                return HashVerificationResult(
                    success=True,
                    file_path=file_path,
                    computed_hash=computed_hash,
                    expected_hash=expected_upper,
                    file_size=file_size
                )
            else:
                return HashVerificationResult(
                    success=False,
                    file_path=file_path,
                    computed_hash=computed_hash,
                    expected_hash=expected_upper,
                    file_size=file_size,
                    error_message=f"哈希不匹配：期望={expected_upper[:16]}...，实际={computed_hash[:16]}..."
                )
        except FileNotFoundError as e:
            return HashVerificationResult(
                success=False,
                file_path=file_path,
                error_message=str(e)
            )
        except Exception as e:
            return HashVerificationResult(
                success=False,
                file_path=file_path,
                error_message=f"校验异常: {str(e)}"
            )
    
    @staticmethod
    def verify_data(data: bytes, expected_hash: str) -> bool:
        """校验字节数据哈希是否匹配"""
        computed = HashVerifier.compute_data_hash(data)
        return computed == expected_hash.upper()
    
    @staticmethod
    def batch_compute_hashes(file_paths: list[str]) -> dict[str, tuple[str, int]]:
        """
        批量计算文件哈希
        返回：{文件路径: (哈希值, 文件大小)}
        """
        results = {}
        for path in file_paths:
            try:
                hash_value, size = HashVerifier.compute_file_hash(path)
                results[path] = (hash_value, size)
            except Exception as e:
                results[path] = ("", 0)
        return results
    
    @staticmethod
    def generate_merkle_hash(items: list[str]) -> str:
        """
        生成简单Merkle哈希（用于批次凭证）
        items: 哈希值列表
        """
        if not items:
            return hashlib.sha256(b"empty").hexdigest().upper()
        
        # 排序后拼接
        sorted_items = sorted(items)
        combined = ":".join(sorted_items)
        return hashlib.sha256(combined.encode('utf-8')).hexdigest().upper()
