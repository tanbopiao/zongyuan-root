"""
身份凭证查询API
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

节点可查询自身身份ID、角色、权限、信用分
"""
from dataclasses import dataclass, asdict
from typing import Dict, Optional


@dataclass
class IdentityInfo:
    """身份信息"""
    identity_id: str
    node_id: str
    did: str
    role: str
    role_name: str
    secondary_role: str
    secondary_role_name: str
    permissions: list
    trust_level: str
    credit_score: int
    status: str
    registered_at: str


class IdentityQueryAPI:
    """身份凭证查询API"""

    def __init__(self, registry_path: str = "/opt/ZONGYUAN-ROOT/node_registry/node_registry.json"):
        self.registry_path = registry_path

    def query_by_node_id(self, node_id: str) -> dict:
        """根据节点ID查询身份信息"""
        try:
            import json
            with open(self.registry_path) as f:
                reg = json.load(f)

            node = reg.get("nodes", {}).get(node_id)
            if not node:
                return {
                    "success": False,
                    "error": f"节点不存在: {node_id}"
                }

            return {
                "success": True,
                "identity_id": node.get("identity_id", ""),
                "node_id": node_id,
                "did": "DID-BR-000002",
                "role": node.get("role", ""),
                "role_name": node.get("role_name", ""),
                "secondary_role": node.get("secondary_role", ""),
                "secondary_role_name": node.get("secondary_role_name", ""),
                "permissions": node.get("permissions", []),
                "trust_level": node.get("trust_level", ""),
                "credit_score": node.get("credit_score", 0),
                "status": node.get("status", ""),
                "registered_at": node.get("registered_at", "")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def query_by_identity_id(self, identity_id: str) -> dict:
        """根据身份ID查询"""
        try:
            import json
            with open(self.registry_path) as f:
                reg = json.load(f)

            for nid, node in reg.get("nodes", {}).items():
                if node.get("identity_id") == identity_id:
                    return self.query_by_node_id(nid)

            return {
                "success": False,
                "error": f"身份ID不存在: {identity_id}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# FastAPI路由示例
identity_router_docs = """
GET /api/identity/me
  查询当前节点身份信息
  Header: X-Node-DID

GET /api/identity/{node_id}
  查询指定节点身份信息
  需要管理员权限
"""

if __name__ == "__main__":
    api = IdentityQueryAPI()
    result = api.query_by_node_id("ZR-NODE-88F9024A")
    print(f"查询结果: {result}")
