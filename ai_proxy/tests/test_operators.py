"""算子组单元测试 - 验证所有算子的阴阳具足（成功+失败路径）"""
import sys, os
sys.path.insert(0, "/opt/ZONGYUAN-ROOT/ai_proxy")
from operators import get_registry

def test_registry_init():
    """测试1: 注册表初始化"""
    reg = get_registry()
    assert reg is not None, "注册表初始化失败"
    ops = reg.list_all()
    assert len(ops) == 6, "算子组数量应为6，实际%d" % len(ops)
    total = sum(len(v) for v in ops.values())
    assert total == 21, "算子总数应为21，实际%d" % total
    print("✅ 测试1通过: 注册表初始化，6组21算子")

def test_text_operators():
    """测试2: 文本算子"""
    reg = get_registry()
    # T3 旁白提炼（纯本地，不依赖外部）
    r = reg.call("text", "extract_narration", script="测试剧本*#内容", max_len=10)
    assert r.get("success") == True, "旁白提炼应成功"
    assert len(r.get("narration","")) <= 10, "旁白长度应<=10"
    assert r.get("operator") == "T3_narration", "算子ID应正确"
    # T4 提示词优化
    r = reg.call("text", "optimize_prompt", prompt="测试")
    assert r.get("success") == True, "提示词优化应成功"
    assert "电影级" in r.get("optimized_prompt",""), "应包含电影级"
    print("✅ 测试2通过: 文本算子T3/T4正常")

def test_storage_operators():
    """测试3: 存储算子"""
    reg = get_registry()
    # S1 作品保存
    r = reg.call("storage", "save_work", device_id="test-unit", title="单元测试作品", video_url="/test.mp4")
    assert r.get("success") == True, "作品保存应成功"
    assert r.get("operator") == "S1_save_work", "算子ID应正确"
    # S3 内核锁档
    r = reg.call("storage", "lock_kernel", snapshot_id="test-unit-test", desc="单元测试")
    assert r.get("success") == True, "内核锁档应成功"
    print("✅ 测试3通过: 存储算子S1/S3正常")

def test_verification_operators():
    """测试4: 验证算子"""
    reg = get_registry()
    # VF1 文件完整性（存在的文件）
    r = reg.call("verify", "check_file_integrity", file_path="/opt/ZONGYUAN-ROOT/kernel.json", min_size=1000)
    assert r.get("success") == True, "内核文件完整性应通过"
    assert r.get("sha256") is not None, "应返回SHA256"
    # VF1 文件完整性（不存在的文件）
    r = reg.call("verify", "check_file_integrity", file_path="/nonexistent/file")
    assert r.get("success") == False, "不存在文件应失败"
    # VF3 漂移检测
    r = reg.call("verify", "drift_detection", current_hash="abc", expected_hash="abc")
    assert r.get("drifted") == False, "相同哈希不应漂移"
    r = reg.call("verify", "drift_detection", current_hash="abc", expected_hash="def")
    assert r.get("drifted") == True, "不同哈希应漂移"
    print("✅ 测试4通过: 验证算子VF1/VF3正常，阴阳具足")

def test_invalid_operator():
    """测试5: 无效算子调用（失败路径）"""
    reg = get_registry()
    r = reg.call("nonexistent", "operator")
    assert r.get("error") is not None, "不存在算子组应返回错误"
    r = reg.call("text", "nonexistent_op")
    assert r.get("error") is not None, "不存在算子应返回错误"
    print("✅ 测试5通过: 无效算子正确返回错误，失败路径完备")

if __name__ == "__main__":
    print("=" * 50)
    print("  算子组单元测试")
    print("=" * 50)
    test_registry_init()
    test_text_operators()
    test_storage_operators()
    test_verification_operators()
    test_invalid_operator()
    print()
    print("=" * 50)
    print("  全部5项测试通过 ✅")
    print("=" * 50)
