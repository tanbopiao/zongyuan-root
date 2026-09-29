"""
文件操作算子 - ZONGYUAN-ROOT 算子化架构
标准化文件操作：读取、写入、复制、移动、删除、哈希计算

算子ID: OP-FILE-OPERATION-001
算子名称: file_operation
类别: 文件/IO
版本: V1.0

溯源标识：Ω₀⊂⊙∞⊂Ω
确权编码：DID-BR-000002
"""

import hashlib
import json
import os
import shutil
import time
from typing import Any, Dict, List, Optional

from operator_base import BaseOperator, OperatorMetadata


class FileOperationOperator(BaseOperator):
    """文件操作算子 - 标准化文件操作"""

    def __init__(self):
        metadata = OperatorMetadata(
            operator_id="OP-FILE-OPERATION-001",
            operator_name="file_operation",
            version="V1.0",
            description="标准化文件操作：读取、写入、复制、移动、删除、哈希计算",
            category="file_operation",
            inputs_schema={
                "operation": "操作类型：read/write/copy/move/delete/hash/list（必需）",
                "path": "目标文件路径（必需）",
                "source": "源文件路径（copy/move时必需）",
                "content": "写入内容（write时必需）",
                "encoding": "文件编码（默认utf-8）",
                "hash_algorithm": "哈希算法：sha256/md5（默认sha256）",
                "recursive": "是否递归（list时，默认False）",
            },
            outputs_schema={
                "result": "操作结果字典",
                "success": "是否成功",
                "path": "操作的文件路径",
            },
        )
        super().__init__(metadata)

    def _compute_file_hash(self, filepath: str, algorithm: str = "sha256") -> str:
        """计算文件哈希"""
        hash_obj = hashlib.new(algorithm)
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行文件操作"""
        operation = inputs.get("operation", "")
        path = inputs.get("path", "")
        source = inputs.get("source", "")
        content = inputs.get("content", "")
        encoding = inputs.get("encoding", "utf-8")
        hash_algorithm = inputs.get("hash_algorithm", "sha256")
        recursive = inputs.get("recursive", False)

        if not operation or not path:
            return {
                "result": {"error": "operation和path为必需参数"},
                "success": False,
                "path": path,
            }

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        result = {
            "operation": operation,
            "path": path,
            "executed_at": timestamp,
        }

        try:
            if operation == "read":
                if not os.path.exists(path):
                    raise FileNotFoundError(f"文件不存在: {path}")
                with open(path, "r", encoding=encoding) as f:
                    file_content = f.read()
                result["content"] = file_content
                result["size_bytes"] = len(file_content.encode(encoding))
                result["success"] = True

            elif operation == "write":
                # 确保目录存在
                dir_path = os.path.dirname(path)
                if dir_path and not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                with open(path, "w", encoding=encoding) as f:
                    f.write(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=2))
                result["size_bytes"] = os.path.getsize(path)
                result["success"] = True

            elif operation == "copy":
                if not source:
                    raise ValueError("copy操作需要source参数")
                if not os.path.exists(source):
                    raise FileNotFoundError(f"源文件不存在: {source}")
                dir_path = os.path.dirname(path)
                if dir_path and not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                shutil.copy2(source, path)
                result["source"] = source
                result["size_bytes"] = os.path.getsize(path)
                result["success"] = True

            elif operation == "move":
                if not source:
                    raise ValueError("move操作需要source参数")
                if not os.path.exists(source):
                    raise FileNotFoundError(f"源文件不存在: {source}")
                dir_path = os.path.dirname(path)
                if dir_path and not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                shutil.move(source, path)
                result["source"] = source
                result["success"] = True

            elif operation == "delete":
                if os.path.exists(path):
                    if os.path.isfile(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                    result["deleted"] = True
                else:
                    result["deleted"] = False
                    result["message"] = "文件不存在，无需删除"
                result["success"] = True

            elif operation == "hash":
                if not os.path.exists(path):
                    raise FileNotFoundError(f"文件不存在: {path}")
                file_hash = self._compute_file_hash(path, hash_algorithm)
                result["hash"] = file_hash
                result["hash_algorithm"] = hash_algorithm
                result["size_bytes"] = os.path.getsize(path)
                result["success"] = True

            elif operation == "list":
                if not os.path.exists(path):
                    raise FileNotFoundError(f"目录不存在: {path}")
                files = []
                if recursive:
                    for root, dirs, filenames in os.walk(path):
                        for filename in filenames:
                            full_path = os.path.join(root, filename)
                            files.append({
                                "path": full_path,
                                "name": filename,
                                "size_bytes": os.path.getsize(full_path),
                                "modified_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(full_path))),
                            })
                else:
                    for item in os.listdir(path):
                        full_path = os.path.join(path, item)
                        files.append({
                            "path": full_path,
                            "name": item,
                            "is_dir": os.path.isdir(full_path),
                            "size_bytes": os.path.getsize(full_path) if os.path.isfile(full_path) else 0,
                        })
                result["files"] = files
                result["count"] = len(files)
                result["success"] = True

            else:
                raise ValueError(f"不支持的操作类型: {operation}")

        except Exception as e:
            result["success"] = False
            result["error"] = f"{type(e).__name__}: {str(e)}"
            return {
                "result": result,
                "success": False,
                "path": path,
                "error": result["error"],
            }

        return {
            "result": result,
            "success": result.get("success", False),
            "path": path,
        }


# 算子单例
file_operation_operator = FileOperationOperator()
