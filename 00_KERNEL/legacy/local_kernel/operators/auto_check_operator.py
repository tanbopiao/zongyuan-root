"""
自动检查算子 - ZONGYUAN-ROOT 算子化架构
对系统/服务/文件执行自动化检查，输出检查报告

算子ID: OP-AUTO-CHECK-001
算子名称: auto_check
类别: 检查/诊断
版本: V1.0

溯源标识：Ω₀⊂⊙∞⊂Ω
确权编码：DID-BR-000002
"""

import os
import time
from typing import Any, Dict, List

from operator_base import BaseOperator, OperatorMetadata


class AutoCheckOperator(BaseOperator):
    """自动检查算子 - 执行系统/服务/文件自动化检查"""

    def __init__(self):
        metadata = OperatorMetadata(
            operator_id="OP-AUTO-CHECK-001",
            operator_name="auto_check",
            version="V1.0",
            description="对系统/服务/文件执行自动化检查，输出检查报告",
            category="auto_check",
            inputs_schema={
                "check_type": "检查类型：service/file/system/all（默认all）",
                "targets": "检查目标列表（可选）",
                "service_ports": "服务端口列表（可选，默认[8020, 8899]）",
            },
            outputs_schema={
                "check_report": "检查报告字典",
                "passed": "通过的检查项数",
                "failed": "失败的检查项数",
                "all_passed": "是否全部通过",
            },
        )
        super().__init__(metadata)

    def _check_port(self, port: int) -> Dict[str, Any]:
        """检查端口是否监听"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            return {
                "port": port,
                "listening": result == 0,
                "status": "正常" if result == 0 else "未监听",
            }
        except Exception as e:
            return {"port": port, "listening": False, "status": f"检查异常: {str(e)}"}

    def _check_file(self, filepath: str) -> Dict[str, Any]:
        """检查文件是否存在"""
        exists = os.path.exists(filepath)
        size = os.path.getsize(filepath) if exists else 0
        return {
            "path": filepath,
            "exists": exists,
            "size_bytes": size,
            "status": "存在" if exists else "不存在",
        }

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行自动检查"""
        check_type = inputs.get("check_type", "all")
        targets = inputs.get("targets", [])
        service_ports = inputs.get("service_ports", [8020, 8899])

        report = {
            "check_type": check_type,
            "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "items": [],
        }
        passed = 0
        failed = 0

        # 服务端口检查
        if check_type in ["service", "all"]:
            for port in service_ports:
                result = self._check_port(port)
                report["items"].append({
                    "category": "service",
                    "target": f"端口{port}",
                    **result,
                })
                if result["listening"]:
                    passed += 1
                else:
                    failed += 1

        # 文件检查
        if check_type in ["file", "all"]:
            default_files = [
                r"C:\Users\4906\.zongyuan_root\gov_ai_platform\server\gov_server.py",
                r"C:\Users\4906\.zongyuan_root\state\kernel_state.json",
            ]
            check_files = targets if targets else default_files
            for filepath in check_files:
                result = self._check_file(filepath)
                report["items"].append({
                    "category": "file",
                    "target": filepath,
                    **result,
                })
                if result["exists"]:
                    passed += 1
                else:
                    failed += 1

        # 系统检查
        if check_type in ["system", "all"]:
            # 内存检查
            try:
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                    ]
                mem = MEMORYSTATUSEX()
                mem.dwLength = ctypes.sizeof(mem)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
                memory_load = mem.dwMemoryLoad
                report["items"].append({
                    "category": "system",
                    "target": "内存使用率",
                    "value": f"{memory_load}%",
                    "status": "正常" if memory_load < 90 else "告警",
                    "passed": memory_load < 90,
                })
                if memory_load < 90:
                    passed += 1
                else:
                    failed += 1
            except Exception:
                pass

        report["summary"] = {
            "total": passed + failed,
            "passed": passed,
            "failed": failed,
            "all_passed": failed == 0,
        }

        return {
            "check_report": report,
            "passed": passed,
            "failed": failed,
            "all_passed": failed == 0,
        }


# 算子单例
auto_check_operator = AutoCheckOperator()
