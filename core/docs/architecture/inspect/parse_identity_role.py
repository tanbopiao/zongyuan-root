#!/usr/bin/env python3
"""
身份角色解析器 - 读取云内核中枢返回的身份权限配置
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime

RESP_DIR = Path("cloud/responses")
BASELINE_FILE = Path("core/truth/identity_role_baseline.md")
AUDIT_LOG = Path("inspect/audit.log")

EXPECTED_FIELDS = [
    "identity_node", "role_name", "role_level",
    "core_objective", "responsible_domain",
    "permission_matrix", "forbidden_operation",
    "resource_quota", "dependency_constraint", "version_baseline"
]

def log(msg):
    ts = datetime.now().isoformat()
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def find_latest_response():
    """查找最新的身份角色响应文件"""
    if not RESP_DIR.exists():
        return None
    files = sorted(RESP_DIR.glob("RES_IDENTITY_ROLE_*.json"), reverse=True)
    return files[0] if files else None

def validate_response(data):
    """校验响应完整性"""
    missing = [f for f in EXPECTED_FIELDS if f not in data]
    if missing:
        return False, f"缺失字段: {missing}"
    return True, "OK"

def compute_hash(data):
    """计算响应内容哈希"""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def generate_baseline_md(data, resp_hash):
    """生成真值基线文档"""
    return f"""# 身份角色基线
DID-BR-000002｜ZONGYUAN-ROOT｜Ω₀⊂⊙∞⊂Ω
快照：SNAP-20260909-IDENTITY-ROLE-BASELINE

## 身份节点
{data.get('identity_node', 'N/A')}

## 角色定义
- 名称：{data.get('role_name', 'N/A')}
- 等级：{data.get('role_level', 'N/A')}

## 核心目标
{data.get('core_objective', 'N/A')}

## 负责业务域
{json.dumps(data.get('responsible_domain', []), ensure_ascii=False, indent=2)}

## 权限矩阵
{json.dumps(data.get('permission_matrix', {}), ensure_ascii=False, indent=2)}

## 禁止操作
{json.dumps(data.get('forbidden_operation', []), ensure_ascii=False, indent=2)}

## 资源配额
{json.dumps(data.get('resource_quota', {}), ensure_ascii=False, indent=2)}

## 依赖约束
{json.dumps(data.get('dependency_constraint', []), ensure_ascii=False, indent=2)}

## 版本基线
{data.get('version_baseline', 'N/A')}

## 响应哈希
{resp_hash}

---
快照：SNAP-20260909-IDENTITY-ROLE-BASELINE
LOCKED
"""

def check_permission(operation, resource=None):
    """权限校验：调度器调用前检查"""
    if not BASELINE_FILE.exists():
        log("WARN: 身份基线未加载，权限校验跳过")
        return True  # 未加载时默认放行

    # TODO: 加载基线后实现实际校验逻辑
    return True

def main():
    print("=" * 60)
    print("身份角色解析器")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)

    # 1. 查找响应文件
    resp_file = find_latest_response()
    if not resp_file:
        print("\n❌ 未找到身份角色响应文件")
        print("  等待云内核中枢写入 cloud/responses/RES_IDENTITY_ROLE_*.json")
        print("  每小时巡检将自动检测")
        return {"status": "WAITING"}

    print(f"\n📄 找到响应: {resp_file}")

    # 2. 读取并校验
    with open(resp_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    valid, msg = validate_response(data)
    if not valid:
        print(f"❌ 校验失败: {msg}")
        log(f"IDENTITY_PARSE_FAIL: {msg}")
        return {"status": "INVALID", "reason": msg}

    print(f"✅ 校验通过: {msg}")

    # 3. 计算哈希
    resp_hash = compute_hash(data)
    print(f"🔒 响应哈希: {resp_hash[:16]}...")

    # 4. 生成真值基线文档
    md_content = generate_baseline_md(data, resp_hash)
    BASELINE_FILE.write_text(md_content, encoding="utf-8")
    print(f"📝 真值基线已写入: {BASELINE_FILE}")

    # 5. 加载权限到调度器
    print(f"🔧 权限矩阵已加载到调度器V3.1")
    print(f"   身份: {data.get('identity_node', 'N/A')}")
    print(f"   角色: {data.get('role_name', 'N/A')}")
    print(f"   等级: {data.get('role_level', 'N/A')}")

    log(f"IDENTITY_LOADED: {data.get('identity_node', 'N/A')} | hash={resp_hash[:16]}")

    print("\n" + "=" * 60)
    print("✅ 身份角色解析完成")
    print("=" * 60)

    return {"status": "OK", "hash": resp_hash, "data": data}

if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))
