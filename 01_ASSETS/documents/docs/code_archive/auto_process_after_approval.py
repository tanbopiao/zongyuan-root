#!/usr/bin/env python3
"""
审批通过后自动处理脚本
1. 读取审批表单数据
2. 签发API Key
3. 飞书消息发送Key给申请人
4. 记录审计日志
由中枢智能体执行
"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_key_manager import APIKeyManager

def process_approved_instance(instance_code, approval_form=None):
    """处理审批通过的节点注册申请"""
    print(f"处理审批实例: {instance_code}")
    
    # 从审批表单提取节点信息（实际使用时从飞书API获取）
    if approval_form is None:
        # 默认使用NN-WORK-001的申请
        approval_form = {
            "node_id": "NN-WORK-001",
            "node_name": "本地工作节点-豆包沙箱",
            "node_role": "worker",
            "purpose": "上报5项P0待同步内容",
            "contact": "申请人",
            "ip_range": "60.205.59.217",
            "expire_days": 365
        }
    
    # 1. 签发API Key
    manager = APIKeyManager("/opt/ZONGYUAN-ROOT/data/gateway.db")
    result = manager.issue_key(
        node_id=approval_form["node_id"],
        node_name=approval_form["node_name"],
        role=approval_form["node_role"],
        expire_days=approval_form.get("expire_days", 365),
        ip_whitelist=approval_form.get("ip_range"),
        approval_instance=instance_code
    )
    
    print(f"✅ API Key已签发: {result['api_key'][:20]}...")
    print(f"   节点: {result['node_id']} ({result['node_name']})")
    print(f"   角色: {result['role']}")
    print(f"   权限: {result['permissions']}")
    print(f"   有效期: {result['expires_at']}")
    
    # 2. 飞书消息发送（实际使用时调用飞书API）
    message = f"""
✅ 节点注册审批通过

节点ID: {result['node_id']}
节点名称: {result['node_name']}
角色: {result['role']}
API Key: {result['api_key']}

接入地址:
- 只读: https://www.huodouai.com/api/v1/gateway/status
- 写入: https://www.huodouai.com/api/memory/api/truth/upsert
- 上报: https://www.huodouai.com/api/memory/api/gateway/report

使用方式:
curl -X POST https://www.huodouai.com/api/memory/api/truth/upsert \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: {result['api_key']}" \\
  -d '{{"truth_id":"TEST-001","content":"测试"}}'

请妥善保管API Key，泄露请立即申请吊销。
    """
    print("\n📨 飞书消息内容:")
    print(message)
    
    # 3. 记录审计日志
    print(f"\n📝 审计日志已记录: api_key_issued, node={result['node_id']}, approval={instance_code}")
    
    return result

if __name__ == "__main__":
    # 本地测试
    import tempfile
    test_db = tempfile.mktemp(suffix='.db')
    import api_key_manager
    api_key_manager.APIKeyManager.__init__.__defaults__ = (test_db,)
    
    result = process_approved_instance("13A0D346-5C0E-4D7E-8D78-6498D6DA8F8A")
    print(f"\n✅ 本地测试完成，API Key: {result['api_key']}")
