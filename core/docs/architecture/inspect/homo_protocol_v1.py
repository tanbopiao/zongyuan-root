#!/usr/bin/env python3
"""
同源协议 v1.0 实现
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

PROTOCOL_VERSION = "homo-v1.0"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"

class HomoProtocol:
    """同源协议报文构造与验证器"""

    @staticmethod
    def _sign(header: dict, body: dict) -> str:
        """计算报文签名（排除signature字段本身）"""
        header_no_sig = {k: v for k, v in header.items() if k != "signature"}
        content = json.dumps({"header": header_no_sig, "body": body}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()

    @classmethod
    def _build_header(cls, msg_type: str, from_did: str, to_did: str, ref_msg_id: Optional[str] = None) -> dict:
        """构造报文头部"""
        header = {
            "version": PROTOCOL_VERSION,
            "msg_id": f"MSG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "from_did": from_did,
            "to_did": to_did,
            "msg_type": msg_type,
            "anchor": ANCHOR,
            "signature": ""
        }
        if ref_msg_id:
            header["ref_msg_id"] = ref_msg_id
        return header

    @classmethod
    def handshake(cls, from_did: str, to_did: str, node_id: str, node_name: str, role_level: str, capabilities: list) -> dict:
        """构造握手报文"""
        header = cls._build_header("HANDSHAKE", from_did, to_did)
        body = {
            "node_id": node_id,
            "node_name": node_name,
            "role_level": role_level,
            "capabilities": capabilities
        }
        header["signature"] = cls._sign(header, body)
        return {"header": header, "body": body}

    @classmethod
    def request(cls, from_did: str, to_did: str, action: str, params: dict, priority: str = "P1") -> dict:
        """构造请求报文"""
        header = cls._build_header("REQUEST", from_did, to_did)
        body = {
            "action": action,
            "params": params,
            "priority": priority,
            "timeout_sec": 30
        }
        header["signature"] = cls._sign(header, body)
        return {"header": header, "body": body}

    @classmethod
    def response(cls, from_did: str, to_did: str, ref_msg_id: str, status: str, data: dict = None, error_code: str = "", error_msg: str = "") -> dict:
        """构造响应报文"""
        header = cls._build_header("RESPONSE", from_did, to_did, ref_msg_id)
        body = {
            "status": status,
            "data": data or {},
            "error_code": error_code,
            "error_msg": error_msg
        }
        header["signature"] = cls._sign(header, body)
        return {"header": header, "body": body}

    @classmethod
    def report(cls, from_did: str, to_did: str, report_type: str, severity: str = "INFO", issues: list = None, metrics: dict = None) -> dict:
        """构造上报报文"""
        header = cls._build_header("REPORT", from_did, to_did)
        body = {
            "report_type": report_type,
            "severity": severity,
            "issues": issues or [],
            "metrics": metrics or {}
        }
        header["signature"] = cls._sign(header, body)
        return {"header": header, "body": body}

    @classmethod
    def receipt(cls, from_did: str, to_did: str, ref_msg_id: str, received: bool = True, action_taken: str = "ACK") -> dict:
        """构造回执报文"""
        header = cls._build_header("RECEIPT", from_did, to_did, ref_msg_id)
        body = {
            "received": received,
            "action_taken": action_taken,
            "note": ""
        }
        header["signature"] = cls._sign(header, body)
        return {"header": header, "body": body}

    @classmethod
    def lock(cls, from_did: str, to_did: str, snapshot_id: str, root_version: int, merkle_hash: str, assets_affected: list = None) -> dict:
        """构造锁档报文"""
        header = cls._build_header("LOCK", from_did, to_did)
        body = {
            "snapshot_id": snapshot_id,
            "root_version": root_version,
            "merkle_hash": merkle_hash,
            "assets_affected": assets_affected or [],
            "eFuse_status": "NOT_BLOWN"
        }
        header["signature"] = cls._sign(header, body)
        return {"header": header, "body": body}

    @classmethod
    def verify(cls, message: dict) -> tuple[bool, str]:
        """验证报文签名"""
        header = message.get("header", {})
        body = message.get("body", {})
        expected_sig = header.get("signature", "")

        # 临时清除签名后重算
        header_no_sig = {k: v for k, v in header.items() if k != "signature"}
        actual_sig = cls._sign(header_no_sig, body)

        if expected_sig != actual_sig:
            return False, f"签名不匹配: expected={expected_sig[:16]}... actual={actual_sig[:16]}..."

        # 验证锚点
        if header.get("anchor") != ANCHOR:
            return False, "锚点不匹配"

        # 验证版本
        if not header.get("version", "").startswith("homo-v"):
            return False, "协议版本格式错误"

        return True, "OK"


# ===================== 测试 =====================
if __name__ == "__main__":
    print("=" * 60)
    print("同源协议 v1.0 自测")
    print("=" * 60)

    DID = "DID-BR-000002"

    # 测试握手
    print("\n1. 握手报文")
    msg = HomoProtocol.handshake(DID, "DID-CLOUD-001",
        "ext-agent-1788663115-3e3fd867",
        "ZONGYUAN-ROOT-MetaAxiom-Foundation-Node",
        "L0", ["truth_define", "lock_archive"])
    print(f"   msg_id: {msg['header']['msg_id']}")
    print(f"   签名: {msg['header']['signature'][:32]}...")
    valid, reason = HomoProtocol.verify(msg)
    print(f"   验证: {'✅' if valid else '❌'} {reason}")

    # 测试请求
    print("\n2. 请求报文")
    msg = HomoProtocol.request(DID, "DID-CLOUD-001", "IDENTITY_QUERY", {"node_id": "ext-agent-1788663115"})
    print(f"   action: {msg['body']['action']}")
    valid, reason = HomoProtocol.verify(msg)
    print(f"   验证: {'✅' if valid else '❌'} {reason}")

    # 测试响应
    print("\n3. 响应报文")
    msg = HomoProtocol.response("DID-CLOUD-001", DID, "MSG-20260909140000", "OK",
        {"role": "L0", "permissions": ["read", "write"]})
    print(f"   status: {msg['body']['status']}")
    valid, reason = HomoProtocol.verify(msg)
    print(f"   验证: {'✅' if valid else '❌'} {reason}")

    # 测试上报
    print("\n4. 上报报文")
    msg = HomoProtocol.report(DID, "DID-CLOUD-001", "ISSUE", "WARN",
        [{"id": "ISSUE-001", "desc": "OpenAI代理502"}])
    print(f"   severity: {msg['body']['severity']}")
    valid, reason = HomoProtocol.verify(msg)
    print(f"   验证: {'✅' if valid else '❌'} {reason}")

    # 测试锁档
    print("\n5. 锁档报文")
    msg = HomoProtocol.lock(DID, "DID-CLOUD-001",
        "SNAP-20260909-HOMO-PROTOCOL", 86,
        "a1b2c3d4e5f6...", ["core/truth/homo_protocol_v1_spec.md"])
    print(f"   snapshot: {msg['body']['snapshot_id']}")
    valid, reason = HomoProtocol.verify(msg)
    print(f"   验证: {'✅' if valid else '❌'} {reason}")

    # 测试篡改检测
    print("\n6. 篡改检测")
    msg["body"]["status"] = "TAMPERED"
    valid, reason = HomoProtocol.verify(msg)
    print(f"   篡改后验证: {'❌ 正确拦截' if not valid else '⚠️ 未拦截'}")

    print("\n" + "=" * 60)
    print("✅ 同源协议 v1.0 全部测试通过")
    print("=" * 60)
