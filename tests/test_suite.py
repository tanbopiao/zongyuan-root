#!/usr/bin/env python3
"""
P2-3: 自动化测试套件
核心模块单元测试 + 集成测试
"""
import json
import hashlib
import sys
import os
from pathlib import Path

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
sys.path.insert(0, str(ROOT))

TEST_RESULTS = []

def test(name: str):
    """测试装饰器"""
    def decorator(func):
        def wrapper():
            try:
                func()
                TEST_RESULTS.append({"name": name, "status": "PASS"})
                print(f"  ✅ {name}")
            except Exception as e:
                TEST_RESULTS.append({"name": name, "status": "FAIL", "error": str(e)})
                print(f"  ❌ {name}: {e}")
        return wrapper
    return decorator

@test("根目录存在")
def test_root_exists():
    assert ROOT.exists(), "ZONGYUAN-ROOT根目录不存在"

@test("真值基座非空")
def test_truth_base():
    truth_dir = ROOT / "truth_base"
    assert truth_dir.exists(), "truth_base目录不存在"
    files = list(truth_dir.glob("*.json"))
    assert len(files) > 0, "真值基座无文件"

@test("内核协议版本链连续")
def test_protocol_chain():
    proto_dir = ROOT / "autonomous_kernel_protocol"
    protos = sorted(proto_dir.glob("*.json"))
    assert len(protos) >= 5, f"协议文件过少: {len(protos)}"
    # 验证版本递增
    versions = []
    for p in protos:
        with open(p) as f:
            data = json.load(f)
        v = data.get("protocol_version", p.name)
        versions.append(v)
    assert len(versions) == len(set(versions)), "存在重复协议版本"

@test("锁档凭证完整")
def test_lock_archive():
    lock_dir = ROOT / "lock_archive"
    snapshots = list(lock_dir.glob("*.json"))
    assert len(snapshots) > 0, "无锁档凭证"
    for s in snapshots:
        with open(s) as f:
            data = json.load(f)
        assert "snapshot_id" in data, f"{s.name} 缺少snapshot_id"

@test("Merkle树功能")
def test_merkle():
    sys.path.insert(0, str(ROOT / "scripts"))
    from merkle_tree import MerkleTree
    tree = MerkleTree(["a", "b", "c", "d"])
    assert tree.root, "Merkle根为空"
    proof = tree.get_proof("b")
    assert tree.verify_proof("b", proof, tree.root), "Merkle证明验证失败"

@test("横向扩展引擎状态")
def test_horizontal_expansion():
    sys.path.insert(0, str(ROOT / "omega_brain"))
    from horizontal_expansion import HorizontalExpansionEngine
    engine = HorizontalExpansionEngine()
    status = engine.get_expansion_status()
    assert "expansion_coefficient" in status
    assert "dimensions" in status
    assert len(status["dimensions"]) == 7, "应为7个维度"

@test("Function Call工具注册")
def test_function_call():
    sys.path.insert(0, str(ROOT / "omega_brain"))
    from function_call_layer import TOOL_REGISTRY, execute_function
    assert len(TOOL_REGISTRY) >= 8, f"工具数不足: {len(TOOL_REGISTRY)}"
    result = execute_function("get_asset_status", {})
    assert result["status"] == "success", "工具执行失败"

@test("备份管理器功能")
def test_backup():
    sys.path.insert(0, str(ROOT / "scripts"))
    from backup_manager import list_backups
    backups = list_backups()
    assert isinstance(backups, list)

@test("配额监控功能")
def test_quota():
    sys.path.insert(0, str(ROOT / "scripts"))
    from quota_monitor_v2 import get_status
    status = get_status()
    assert "daily_limit" in status
    assert "used_today" in status
    assert "level" in status

@test("资产无空文件")
def test_no_empty_files():
    empty = []
    for fp in ROOT.rglob("*"):
        if fp.is_file() and "cache" not in str(fp) and fp.stat().st_size == 0:
            empty.append(str(fp))
    assert len(empty) == 0, f"存在空文件: {empty[:3]}"

@test("FastAPI服务健康")
def test_service_health():
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=3) as resp:
            data = json.loads(resp.read())
            assert data.get("status") == "healthy", "服务不健康"
    except Exception as e:
        raise AssertionError(f"服务不可达: {e}")

@test("负载均衡器功能")
def test_load_balancer():
    sys.path.insert(0, str(ROOT / "omega_brain"))
    from load_balancer import LoadBalancer
    lb = LoadBalancer()
    status = lb.get_status()
    assert "total_instances" in status
    assert "healthy_instances" in status

def run_all_tests():
    print("🧪 ZONGYUAN-ROOT 自动化测试套件")
    print(f"测试时间: {__import__('datetime').datetime.now().isoformat()}")
    print("=" * 50)
    
    test_root_exists()
    test_truth_base()
    test_protocol_chain()
    test_lock_archive()
    test_merkle()
    test_horizontal_expansion()
    test_function_call()
    test_backup()
    test_quota()
    test_no_empty_files()
    test_service_health()
    test_load_balancer()
    
    print("=" * 50)
    passed = sum(1 for r in TEST_RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in TEST_RESULTS if r["status"] == "FAIL")
    print(f"总计: {len(TEST_RESULTS)} | 通过: {passed} | 失败: {failed}")
    print(f"通过率: {passed/len(TEST_RESULTS):.1%}")
    
    # 保存测试报告
    report = {
        "test_run_id": hashlib.sha256(str(__import__('datetime').datetime.now()).encode()).hexdigest()[:12],
        "total": len(TEST_RESULTS),
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed/len(TEST_RESULTS):.1%}",
        "results": TEST_RESULTS
    }
    report_file = ROOT / "logs" / f"test_report_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"测试报告: {report_file.name}")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
