#!/usr/bin/env python3
"""
同源节点申请 + 种子真值上报一体化脚本
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import hashlib
import base64
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# ==================== 配置区域 ====================
CLOUD_GATEWAY = "https://www.huodouai.com"
API_ENDPOINTS = {
    "a2a_register": f"{CLOUD_GATEWAY}/a2a/register",
    "truth_report": f"{CLOUD_GATEWAY}/api/report/truth",
    "heartbeat": f"{CLOUD_GATEWAY}/dal/heartbeat",
    "nodes_list": f"{CLOUD_GATEWAY}/a2a/nodes",
    "peers": f"{CLOUD_GATEWAY}/a2a/peers",
    "directory_tree": f"{CLOUD_GATEWAY}/a2a/directory-tree/latest"
}

# 节点身份（从 MEMORY.md 读取）
NODE_IDENTITY = {
    "DID": "DID-BR-000002",
    "sovereign_root": "Ω₀⊂⊙∞⊂Ω",
    "node_name": "ZONGYUAN-ROOT 云端主权威节点",
    "node_role": "admin",
    "autonomy_level": "Lv10",
    "engineering_maturity": "Lv7"
}

# 飞书凭证（用于共享大脑访问）
FEISHU_CREDENTIALS = {
    "app_id": "cli_aa445c3d35fadc01",
    "app_secret": "V3LdsErQ0LSXok2uGNQsUKIkQ2NVwNsK"
}

# 联邦接入地址
FEDERATION_ENDPOINTS = {
    "join_url": "https://api.huodouai.com/a2a/join/",
    "sfmp_report": "https://huodouai.com/whitepaper/sfmp-std.html",
    "omega_brain": "https://huodouai.com/omega-brain.html",
    "api_docs": "https://huodouai.com/tech/api.html",
    "feishu_shared_brain": "https://my.feishu.cn/base/DgnMbLqZiaIUDKshqCrcD4DvnBg"
}

# ==================== 工具函数 ====================
def compute_file_hash(filepath):
    """计算文件 SHA256 哈希"""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def _curl(url, data=None, headers=None, method="GET", timeout=30):
    """curl 子进程封装：绕开本机 Python SSL 证书链缺陷（遗留 #8）。
    curl 走系统 CA，实测正常；urllib 走 CERTIFICATE_VERIFY_FAILED。
    返回 {"status": <http_code or 0>, "data": <parsed json or None>, "error": <text or None>}
    """
    import subprocess
    cmd = ["curl", "-s", "-S", "-X", method, "--max-time", str(timeout),
           "-w", "\n__HTTP_CODE__:%{http_code}", url]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    if data is not None:
        cmd += ["-d", json.dumps(data) if isinstance(data, (dict, list)) else str(data)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
        out = proc.stdout
        status = 0
        body = out
        if "__HTTP_CODE__:" in out:
            body, code_str = out.rsplit("__HTTP_CODE__:", 1)
            try:
                status = int(code_str.strip())
            except ValueError:
                status = 0
        body = body.strip()
        data_json = None
        if body:
            try:
                data_json = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                data_json = None
        err = None if proc.returncode == 0 else proc.stderr.strip()
        return {"status": status, "data": data_json, "error": err, "body": body}
    except Exception as e:
        return {"status": 0, "data": None, "error": str(e), "body": ""}

def http_get(url, headers=None):
    """发送 HTTP GET 请求（curl 子进程，绕开本机 SSL 缺陷）"""
    return _curl(url, headers=headers, method="GET")

def http_post(url, data, headers=None):
    """发送 HTTP POST 请求（curl 子进程，绕开本机 SSL 缺陷）"""
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    return _curl(url, data=data, headers=hdrs, method="POST")

def fetch_directory_tree():
    """获取云端目录树锚定信息（register 前置契约）"""
    result = http_get(API_ENDPOINTS["directory_tree"],
                      headers={"X-DID": NODE_IDENTITY["DID"]})
    data = result.get("data") or {}
    return {
        "version": data.get("version", "1.0.1"),
        "hash": data.get("tree_hash", ""),
        "raw_status": result.get("status"),
        "raw_error": result.get("error"),
    }

# ==================== 核心功能 ====================
def query_federation_status():
    """查询联邦网络当前状态"""
    print("\n" + "="*60)
    print("📡 查询联邦网络状态")
    print("="*60)
    
    results = {}
    xdid = {"X-DID": NODE_IDENTITY["DID"], "Content-Type": "application/json"}

    # 1. 检查网关健康（/dal/heartbeat 需 target + content_b64）
    print("\n[1/4] 检查云端网关健康...")
    hb_body = {"target": NODE_IDENTITY["node_name"],
               "content_b64": base64.b64encode(b"patrol-alive").decode()}
    results["health"] = http_post(API_ENDPOINTS["heartbeat"], hb_body, headers=xdid)
    print(f"      状态：{results['health'].get('status', 'N/A')}")

    # 2. 查看节点目录（/a2a/nodes 同源鉴权，POST + X-DID）
    print("\n[2/4] 获取联邦节点目录...")
    results["nodes"] = http_post(API_ENDPOINTS["nodes_list"],
                                 {"did": NODE_IDENTITY["DID"]}, headers=xdid)
    node_count = len((results["nodes"].get("data") or {}).get("nodes", []))
    print(f"      节点数：{node_count}")

    # 3. 查看对等节点（/a2a/peers 同源鉴权，POST + X-DID）
    print("\n[3/4] 获取公开对等节点...")
    results["peers"] = http_post(API_ENDPOINTS["peers"],
                                 {"did": NODE_IDENTITY["DID"]}, headers=xdid)
    peer_count = len((results["peers"].get("data") or {}).get("peers", []))
    print(f"      对等节点：{peer_count}")
    
    # 4. 检查 SFMP 状态
    print("\n[4/4] 检查 SFMP 联邦记忆池...")
    sfmp_status = http_get(FEDERATION_ENDPOINTS["sfmp_report"])
    print(f"      SFMP 报告：{'✓ 可访问' if sfmp_status.get('status') == 200 else '✗ 暂不可达'}")
    
    return results

def prepare_seed_truth_payload():
    """准备种子真值上报负载"""
    print("\n" + "="*60)
    print("📦 准备种子真值上报包")
    print("="*60)
    
    meta_rules_dir = Path("/zongyuan-yuanji/var/truth-cache/meta-rules")
    truths = []
    
    # 收集核心元规则
    core_files = [
        "CORE-AXIOMS-001.json",
        "META-ONTOLOGY-001.json",
        "META-RULE-012.json"
    ]
    
    for filename in core_files:
        filepath = meta_rules_dir / filename
        if filepath.exists():
            file_hash = compute_file_hash(filepath)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            truths.append({
                "key": f"core.{filename.replace('.json', '')}",
                "value": content,
                "truth_type": "meta_law",
                "did": NODE_IDENTITY["DID"],
                "hash": file_hash,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            print(f"\n✓ 已准备：{filename}")
            print(f"  Hash: {file_hash[:16]}...")
    
    return {"truths": truths, "total_count": len(truths)}

def report_seed_truth_to_cloud(payload):
    """上报种子真值到云端记忆网关"""
    print("\n" + "="*60)
    print("🚀 上报种子真值至云端记忆网关")
    print("="*60)
    
    results = []
    
    for truth in payload["truths"]:
        print(f"\n[提交] {truth['key']}")
        result = http_post(
            API_ENDPOINTS["truth_report"],
            truth,
            headers={
                "X-DID": NODE_IDENTITY["DID"],
                "Content-Type": "application/json"
            }
        )
        
        if result.get("status") == 200:
            print(f"  ✓ 成功 - 真值总数：{result.get('data', {}).get('truth_count', '?')}")
            results.append({"key": truth["key"], "status": "success"})
        else:
            print(f"  ✗ 失败 - {result.get('error', '未知错误')}")
            results.append({"key": truth["key"], "status": "failed", "error": result.get("error")})
    
    return results

def register_homologous_node():
    """注册同源节点"""
    print("\n" + "="*60)
    print("🏢 注册同源节点")
    print("="*60)
    
    registration_payload = {
        "DID": NODE_IDENTITY["DID"],
        "node_name": NODE_IDENTITY["node_name"],
        "node_role": "homologous",
        "capabilities": [
            "truth_reporting",
            "heartbeat_monitoring", 
            "memory_pool_sync",
            "cross_domain_reasoning"
        ],
        "endpoint": API_ENDPOINTS["a2a_register"],
        "compliance": {
            "dual_track_access": True,
            "key_zero_disk": True,
            "l5_security_boundary": True
        }
    }
    
    print(f"\n[节点信息]")
    print(f"  DID: {registration_payload['DID']}")
    print(f"  角色：{registration_payload['node_role']}")
    print(f"  能力数：{len(registration_payload['capabilities'])}")
    
    # 注意：实际调用需要先在 join 页面完成审批流程
    print("\n⚠️  同源节点注册需要先通过飞书共享大脑审批流程:")
    print(f"   → {FEDERATION_ENDPOINTS['feishu_shared_brain']}")
    
    return {"status": "pending_approval", "message": "请先到飞书共享大脑提交申请"}

def generate_application_summary(query_results, truth_results, registration_result):
    """生成申请总结报告"""
    print("\n" + "="*60)
    print("📊 同源节点申请总结")
    print("="*60)
    
    summary = {
        "request_id": f"HOMOLOGOUS-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "node_identity": NODE_IDENTITY,
        "query_results": {
            "gateway_health": query_results.get("health", {}).get("status"),
            "federated_nodes": len(query_results.get("nodes", {}).get("data", {}).get("nodes", [])),
            "peer_nodes": len(query_results.get("peers", {}).get("data", {}).get("peers", []))
        },
        "truth_submission": {
            "prepared_count": truth_results.get("total_count", 0),
            "submitted_count": len([r for r in truth_results.get("results", []) if r.get("status") == "success"])
        },
        "registration_status": registration_result.get("status"),
        "next_steps": [
            "1. 访问飞书共享大脑提交同源节点申请",
            "2. 等待审批通过后获得同源令牌",
            "3. 使用同源令牌上报完整种子真值",
            "4. 启动心跳守护进程",
            "5. 定期同步联邦记忆池"
        ],
        "supporting_urls": FEDERATION_ENDPOINTS
    }
    
    # 保存到本地
    output_path = Path("/zongyuan-yuanji/var/tasks/homologous_node_application_summary.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 申请总结已保存：{output_path}")
    
    return summary

# ==================== 主执行流程 ====================
def main():
    print("\n" + "🌟 "*30)
    print("   ZONGYUAN-ROOT 同源节点申请流程")
    print(f"   DID: {NODE_IDENTITY['DID']} | 锚点：{NODE_IDENTITY['sovereign_root']}")
    print("🌟 "*30)
    
    # Step 1: 查询联邦状态
    query_results = query_federation_status()
    
    # Step 2: 准备种子真值
    truth_payload = prepare_seed_truth_payload()
    
    # Step 3: 上报种子真值（尝试）
    truth_results = report_seed_truth_to_cloud(truth_payload)
    
    # Step 4: 注册同源节点（需审批）
    registration_result = register_homologous_node()
    
    # Step 5: 生成总结
    summary = generate_application_summary(query_results, truth_results, registration_result)
    
    print("\n" + "✅ "*20)
    print("申请流程执行完成")
    print("下一步请访问飞书共享大脑提交正式申请")
    print("✅ "*20 + "\n")
    
    return summary

if __name__ == "__main__":
    main()
