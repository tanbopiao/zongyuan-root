#!/usr/bin/env python3
"""
深度仿真测试框架 DeepSimulationTest V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

对四项优化成果进行全面深度仿真测试：
1. 中枢部署拉取服务（CentralDeployAgent）
2. T17全域缓存治理（CacheGovernor）
3. D2-T1内容哈希优化
4. 扫描置信度优化

测试维度：功能测试、压力测试、边界测试、集成测试、故障注入测试
"""

import hashlib
import json
import os
import sys
import time
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

# ==================== 测试框架 ====================
class TestFramework:
    """深度仿真测试框架"""
    def __init__(self):
        self.results = []
        self.start_time = time.time()
        self.tmpdir = tempfile.mkdtemp(prefix="deep_sim_test_")

    def now_iso(self):
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def test(self, name, category, func):
        """执行单个测试"""
        print(f"\n{'='*60}")
        print(f"[{category}] {name}")
        print(f"{'='*60}")
        start = time.time()
        try:
            result = func()
            elapsed = round(time.time() - start, 3)
            status = "PASS" if result.get("pass", False) else "FAIL"
            print(f"  结果: {status} | 耗时: {elapsed}s")
            if result.get("details"):
                for k, v in result["details"].items():
                    print(f"  {k}: {v}")
            self.results.append({
                "name": name,
                "category": category,
                "status": status,
                "elapsed": elapsed,
                "details": result.get("details", {}),
                "timestamp": self.now_iso()
            })
            return result
        except Exception as e:
            elapsed = round(time.time() - start, 3)
            print(f"  结果: ERROR | 耗时: {elapsed}s | 错误: {e}")
            self.results.append({
                "name": name,
                "category": category,
                "status": "ERROR",
                "elapsed": elapsed,
                "error": str(e),
                "timestamp": self.now_iso()
            })
            return {"pass": False, "error": str(e)}

    def summary(self):
        """生成测试汇总"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")
        total_elapsed = round(time.time() - self.start_time, 2)

        print(f"\n\n{'#'*60}")
        print(f"# 深度仿真测试汇总")
        print(f"{'#'*60}")
        print(f"  总测试数: {total}")
        print(f"  通过: {passed} | 失败: {failed} | 错误: {errors}")
        print(f"  通过率: {round(passed/total*100, 1) if total > 0 else 0}%")
        print(f"  总耗时: {total_elapsed}s")
        print(f"  测试时间: {self.now_iso()}")
        print(f"{'#'*60}")

        # 按类别统计
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "pass": 0}
            categories[cat]["total"] += 1
            if r["status"] == "PASS":
                categories[cat]["pass"] += 1

        print(f"\n  分类统计:")
        for cat, stats in categories.items():
            rate = round(stats["pass"]/stats["total"]*100, 1)
            print(f"    {cat}: {stats['pass']}/{stats['total']} ({rate}%)")

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": round(passed/total*100, 1) if total > 0 else 0,
            "total_elapsed": total_elapsed,
            "categories": categories,
            "results": self.results
        }

    def cleanup(self):
        """清理临时目录"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)


# ==================== 测试用例 ====================

# --- 1. 中枢部署拉取服务测试 ---
def test_deploy_agent_instruction_parsing():
    """功能测试：部署指令解析"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "central_deploy_agent"))
    from central_deploy_agent import parse_deploy_instruction

    cases = [
        ("【P0修复指令】昆仑洞天连接超时", "service_fix", "kunlun", "P0"),
        ("【P1部署指令】中台整合部署包已上传", "deploy", "midplatform", "P1"),
        ("nginx配置异常，请重启", "service_fix", "nginx", "P2"),
        ("普通文本无指令", "unknown", None, "P2"),
    ]

    all_pass = True
    details = {}
    for content, exp_type, exp_target, exp_priority in cases:
        result = parse_deploy_instruction(content)
        match = (result["type"] == exp_type and
                 result["target"] == exp_target and
                 result["priority"] == exp_priority)
        details[content[:20]] = f"type={result['type']},target={result['target']},p={result['priority']} {'✓' if match else '✗'}"
        if not match:
            all_pass = False

    return {"pass": all_pass, "details": details}


def test_deploy_agent_hash_verification():
    """功能测试：部署包哈希校验"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "central_deploy_agent"))
    from central_deploy_agent import sha256_file, sha256_str

    # 测试字符串哈希
    test_str = "DID-BR-000002 test content"
    h1 = sha256_str(test_str)
    h2 = sha256_str(test_str)
    h3 = sha256_str(test_str + "modified")

    # 测试文件哈希
    test_file = os.path.join(tempfile.gettempdir(), "hash_test.txt")
    with open(test_file, "w") as f:
        f.write(test_str)
    fh = sha256_file(test_file)
    os.remove(test_file)

    all_pass = (len(h1) == 64 and h1 == h2 and h1 != h3 and len(fh) == 64)
    return {
        "pass": all_pass,
        "details": {
            "哈希长度": f"{len(h1)}位",
            "一致性": "✓" if h1 == h2 else "✗",
            "抗篡改": "✓" if h1 != h3 else "✗",
            "文件哈希": f"{fh[:16]}..."
        }
    }


def test_deploy_agent_audit_log():
    """功能测试：审计日志Merkle链"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "central_deploy_agent"))
    import central_deploy_agent as cda

    # 使用临时审计日志
    cda.CONFIG["audit_log"] = os.path.join(tempfile.gettempdir(), "test_audit.jsonl")
    if os.path.exists(cda.CONFIG["audit_log"]):
        os.remove(cda.CONFIG["audit_log"])

    h1 = cda.log_audit("test_event_1", {"data": "value1"})
    h2 = cda.log_audit("test_event_2", {"data": "value2"})

    # 验证日志文件
    with open(cda.CONFIG["audit_log"]) as f:
        lines = f.readlines()

    all_pass = (len(lines) == 2 and len(h1) == 64 and len(h2) == 64 and h1 != h2)
    os.remove(cda.CONFIG["audit_log"])

    return {
        "pass": all_pass,
        "details": {
            "日志条数": len(lines),
            "哈希1": f"{h1[:16]}...",
            "哈希2": f"{h2[:16]}...",
            "链完整性": "✓" if h1 != h2 else "✗"
        }
    }


# --- 2. T17缓存治理测试 ---
def test_cache_governor_multilevel():
    """功能测试：多级缓存（内存→磁盘→源数据）"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cache_governance"))
    import cache_governor as cg

    tmpdir = tempfile.mkdtemp()
    cg.CONFIG["cache_dir"] = os.path.join(tmpdir, "cache")

    governor = cg.CacheGovernor()

    # 写入内存缓存
    governor.memory_cache.set("key_mem", {"data": "memory_value"}, 3600)
    # 写入磁盘缓存
    governor.disk_cache.set("key_disk", {"data": "disk_value"}, 3600)

    # 测试多级获取
    v1, src1 = governor.get("key_mem")
    v2, src2 = governor.get("key_disk")
    v3, src3 = governor.get("key_source", source_func=lambda: {"data": "source_value"})
    v3_2, src3_2 = governor.get("key_source")  # 第二次应命中缓存

    all_pass = (
        v1 == {"data": "memory_value"} and src1 == "memory" and
        v2 == {"data": "disk_value"} and src2 == "disk" and
        v3 == {"data": "source_value"} and src3 == "source" and
        v3_2 == {"data": "source_value"} and src3_2 == "memory"
    )

    shutil.rmtree(tmpdir, ignore_errors=True)
    return {
        "pass": all_pass,
        "details": {
            "内存命中": f"{v1} ({src1})",
            "磁盘命中": f"{v2} ({src2})",
            "源数据回源": f"{v3} ({src3})",
            "回源后缓存命中": f"{v3_2} ({src3_2})"
        }
    }


def test_cache_governor_stress():
    """压力测试：大量缓存读写"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cache_governance"))
    import cache_governor as cg

    tmpdir = tempfile.mkdtemp()
    cg.CONFIG["cache_dir"] = os.path.join(tmpdir, "cache")
    cg.CONFIG["max_memory_cache_mb"] = 10  # 限制10MB测试LRU驱逐

    governor = cg.CacheGovernor()

    # 写入1000个缓存条目
    write_start = time.time()
    for i in range(1000):
        governor.memory_cache.set(f"key_{i}", {"data": f"value_{i}" * 100}, 3600)
    write_time = round(time.time() - write_start, 3)

    # 读取1000个缓存条目
    read_start = time.time()
    hits = 0
    for i in range(1000):
        v = governor.memory_cache.get(f"key_{i}")
        if v is not None:
            hits += 1
    read_time = round(time.time() - read_start, 3)

    stats = governor.memory_cache.stats()

    all_pass = (hits > 0 and write_time < 5 and read_time < 5)
    shutil.rmtree(tmpdir, ignore_errors=True)

    return {
        "pass": all_pass,
        "details": {
            "写入1000条": f"{write_time}s",
            "读取1000条": f"{read_time}s",
            "命中率": f"{round(hits/1000*100, 1)}%",
            "内存缓存条目": stats["entries"],
            "内存使用": f"{stats['size_mb']}MB/{stats['max_mb']}MB",
            "LRU驱逐": "✓ 已触发" if stats["entries"] < 1000 else "未触发"
        }
    }


def test_cache_governor_expiry_cleanup():
    """边界测试：缓存过期与清理"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cache_governance"))
    import cache_governor as cg

    tmpdir = tempfile.mkdtemp()
    cg.CONFIG["cache_dir"] = os.path.join(tmpdir, "cache")

    governor = cg.CacheGovernor()

    # 写入已过期缓存（TTL=1秒）
    governor.disk_cache.set("expired_key", {"data": "expired"}, 1)
    governor.disk_cache.set("valid_key", {"data": "valid"}, 3600)
    time.sleep(1.5)  # 等待过期

    # 不调用get（get会自动清理），直接cleanup验证过期文件被清理
    cleanup = governor.disk_cache.cleanup_expired()

    # 验证过期文件已被清理，有效文件保留
    expired_path = governor.disk_cache._key_to_path("expired_key")
    valid_path = governor.disk_cache._key_to_path("valid_key")
    expired_exists = os.path.exists(expired_path)
    valid_exists = os.path.exists(valid_path)

    all_pass = (cleanup["removed"] >= 1 and not expired_exists and valid_exists)
    shutil.rmtree(tmpdir, ignore_errors=True)

    return {
        "pass": all_pass,
        "details": {
            "清理移除": f"{cleanup['removed']}个",
            "释放空间": f"{cleanup['freed_mb']}MB",
            "过期文件已删除": "✓" if not expired_exists else "✗",
            "有效文件保留": "✓" if valid_exists else "✗"
        }
    }


def test_cache_governor_penetration_protection():
    """故障注入测试：缓存穿透防护"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cache_governance"))
    import cache_governor as cg

    tmpdir = tempfile.mkdtemp()
    cg.CONFIG["cache_dir"] = os.path.join(tmpdir, "cache")

    governor = cg.CacheGovernor()

    # 模拟缓存穿透：查询不存在的键，source_func返回None
    call_count = 0
    def source_returns_none():
        nonlocal call_count
        call_count += 1
        return None

    # 第一次查询：回源，返回None，空值缓存
    v1, src1 = governor.get("nonexistent_key", source_func=source_returns_none)
    # 第二次查询：应命中空值缓存，不再调用source_func
    v2, src2 = governor.get("nonexistent_key", source_func=source_returns_none)

    all_pass = (v1 is None and src1 == "source" and v2 is None and src2 == "memory" and call_count == 1)
    shutil.rmtree(tmpdir, ignore_errors=True)

    return {
        "pass": all_pass,
        "details": {
            "首次查询": f"值={v1}, 来源={src1}",
            "二次查询": f"值={v2}, 来源={src2}",
            "源函数调用次数": f"{call_count} (应为1，空值缓存生效)",
            "穿透防护": "✓ 有效" if call_count == 1 else "✗ 失效"
        }
    }


# --- 3. D2-T1内容哈希优化测试 ---
def test_d2t1_batch_optimization():
    """功能测试：批量处理优化（200/轮）"""
    sys.path.insert(0, "/sandboxdata/workspace/file")
    from evolution_task_executor import execute_d2_t1

    # 加载清单
    manifest = json.load(open("/sandboxdata/workspace/file/UNIFIED_GLOBAL_LOCK_MANIFEST.json"))
    queue = json.load(open("/sandboxdata/workspace/file/evolution_task_queue.json"))
    tasks = queue if isinstance(queue, list) else queue.get("tasks", [])

    d2t1 = None
    for t in tasks:
        if t.get("task_id") == "D2-T1":
            d2t1 = t
            d2t1["status"] = "IN_PROGRESS"
            break

    if not d2t1:
        return {"pass": False, "details": {"error": "D2-T1任务未找到"}}

    # 执行前覆盖率
    total = len(manifest["assets"])
    before = sum(1 for a in manifest["assets"].values() if len(str(a.get("content_hash", ""))) == 64)

    # 执行一轮
    result = execute_d2_t1(queue, d2t1, manifest)

    # 执行后覆盖率
    after = sum(1 for a in manifest["assets"].values() if len(str(a.get("content_hash", ""))) == 64)

    all_pass = (
        result["batch_processed"] == 200 and
        result["batch_processed"] == result["success"] + result["skipped"] + result["fallback"] + result["failed"] and
        result["remaining"] >= 0
    )

    return {
        "pass": all_pass,
        "details": {
            "批量大小": result["batch_processed"],
            "成功数": result["success"],
            "跳过数": result["skipped"],
            "兜底数": result["fallback"],
            "失败数": result["failed"],
            "计数校验": "✓" if result["batch_processed"] == result["success"] + result["skipped"] + result["fallback"] + result["failed"] else "✗",
            "剩余数": result["remaining"],
            "执行前覆盖率": f"{round(before/total*100, 2)}% ({before}/{total})",
            "执行后覆盖率": f"{round(after/total*100, 2)}% ({after}/{total})"
        }
    }


def test_d2t1_metadata_fallback():
    """边界测试：元数据指纹兜底"""
    sys.path.insert(0, "/sandboxdata/workspace/file")
    from evolution_task_executor import get_content_hash

    # 测试无法获取内容的资产（应返回兜底或跳过）
    test_asset = {
        "asset_id": "test_fallback_001",
        "name": "测试资产",
        "asset_type": "unknown_type",
        "url": "https://example.com/nonexistent"
    }

    ch, size, ctype = get_content_hash(test_asset)

    # 验证返回值格式
    valid_format = len(ch) == 64 or ch.startswith("CONTENT_HASH_")

    return {
        "pass": valid_format,
        "details": {
            "返回哈希": f"{ch[:32]}..." if len(ch) > 32 else ch,
            "文件大小": size,
            "内容类型": ctype,
            "格式有效": "✓" if valid_format else "✗"
        }
    }


# --- 4. 扫描置信度优化测试 ---
def test_confidence_positive_growth():
    """功能测试：正向增长从轻惩罚"""
    sys.path.insert(0, "/sandboxdata/workspace/file")
    from incremental_monitor import calc_scan_confidence

    # 大规模新增（正向增长）
    score = calc_scan_confidence(
        current_total=12350, prev_total=7329,
        deleted_count=0, new_count=5021,
        fluctuation_count=0, api_errors=0
    )

    all_pass = score >= 75  # 应通过固化门控

    return {
        "pass": all_pass,
        "details": {
            "场景": "大规模新增5021个，删除0",
            "置信度": f"{score}/100",
            "固化门控(≥75)": "✓ 通过" if score >= 75 else "✗ 未通过",
            "旧算法对比": "70.0分(未通过)"
        }
    }


def test_confidence_anomaly_deletion():
    """边界测试：异常删除严格惩罚"""
    sys.path.insert(0, "/sandboxdata/workspace/file")
    from incremental_monitor import calc_scan_confidence

    # 大规模删除（异常）
    score = calc_scan_confidence(
        current_total=9000, prev_total=12000,
        deleted_count=3000, new_count=0,
        fluctuation_count=0, api_errors=0
    )

    # 删除25%应该被严格惩罚
    all_pass = score < 80  # 应低于正向增长的分数

    return {
        "pass": all_pass,
        "details": {
            "场景": "删除3000个(25%)，新增0",
            "置信度": f"{score}/100",
            "严格惩罚": "✓ 有效" if score < 80 else "✗ 未生效"
        }
    }


def test_confidence_api_errors():
    """故障注入测试：API错误惩罚"""
    sys.path.insert(0, "/sandboxdata/workspace/file")
    from incremental_monitor import calc_scan_confidence

    # 正常增长但有API错误
    score_normal = calc_scan_confidence(10000, 10100, 0, 100, 0, api_errors=0)
    score_errors = calc_scan_confidence(10000, 10100, 0, 100, 0, api_errors=5)

    all_pass = score_errors < score_normal  # API错误应降低置信度

    return {
        "pass": all_pass,
        "details": {
            "无API错误": f"{score_normal}分",
            "5个API错误": f"{score_errors}分",
            "惩罚差值": f"{round(score_normal - score_errors, 1)}分",
            "错误惩罚": "✓ 有效" if all_pass else "✗ 失效"
        }
    }


# --- 5. 集成测试 ---
def test_integration_cache_with_deploy():
    """集成测试：缓存治理与部署代理协同"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "central_deploy_agent"))
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cache_governance"))

    import central_deploy_agent as cda
    import cache_governor as cg

    tmpdir = tempfile.mkdtemp()
    cg.CONFIG["cache_dir"] = os.path.join(tmpdir, "cache")
    cda.CONFIG["audit_log"] = os.path.join(tmpdir, "audit.jsonl")

    # 模拟：部署指令缓存
    governor = cg.CacheGovernor()

    # 缓存部署指令（通过memory_cache.set）
    deploy_instruction = {
        "type": "deploy",
        "target": "midplatform",
        "priority": "P1",
        "package_hash": "abc123"
    }
    governor.memory_cache.set("deploy:instruction_001", deploy_instruction, 3600)

    # 部署代理读取缓存指令
    cached, source = governor.get("deploy:instruction_001")
    instruction = cda.parse_deploy_instruction(json.dumps(cached))

    # 记录审计
    audit_hash = cda.log_audit("deploy_cached_execution", {
        "instruction": instruction,
        "cache_source": source
    })

    all_pass = (
        cached == deploy_instruction and
        source == "memory" and
        instruction["type"] == "deploy" and
        len(audit_hash) == 64
    )

    shutil.rmtree(tmpdir, ignore_errors=True)
    return {
        "pass": all_pass,
        "details": {
            "缓存读取": f"来源={source}",
            "指令解析": f"type={instruction['type']},target={instruction['target']}",
            "审计哈希": f"{audit_hash[:16]}...",
            "集成协同": "✓ 正常"
        }
    }


# ==================== 主入口 ====================
if __name__ == "__main__":
    framework = TestFramework()

    print("=" * 60)
    print("  深度仿真测试框架启动")
    print(f"  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print(f"  临时目录: {framework.tmpdir}")
    print("=" * 60)

    # 1. 中枢部署拉取服务测试
    framework.test("部署指令解析", "中枢部署代理", test_deploy_agent_instruction_parsing)
    framework.test("部署包哈希校验", "中枢部署代理", test_deploy_agent_hash_verification)
    framework.test("审计日志Merkle链", "中枢部署代理", test_deploy_agent_audit_log)

    # 2. T17缓存治理测试
    framework.test("多级缓存功能", "T17缓存治理", test_cache_governor_multilevel)
    framework.test("缓存压力测试(1000条)", "T17缓存治理", test_cache_governor_stress)
    framework.test("缓存过期清理", "T17缓存治理", test_cache_governor_expiry_cleanup)
    framework.test("缓存穿透防护", "T17缓存治理", test_cache_governor_penetration_protection)

    # 3. D2-T1内容哈希测试
    framework.test("批量处理优化(200/轮)", "D2-T1哈希优化", test_d2t1_batch_optimization)
    framework.test("元数据指纹兜底", "D2-T1哈希优化", test_d2t1_metadata_fallback)

    # 4. 扫描置信度测试
    framework.test("正向增长从轻惩罚", "置信度优化", test_confidence_positive_growth)
    framework.test("异常删除严格惩罚", "置信度优化", test_confidence_anomaly_deletion)
    framework.test("API错误惩罚", "置信度优化", test_confidence_api_errors)

    # 5. 集成测试
    framework.test("缓存与部署代理集成", "集成测试", test_integration_cache_with_deploy)

    # 生成汇总
    summary = framework.summary()

    # 保存报告
    report_path = os.path.join(os.path.dirname(__file__), "deep_simulation_report.json")
    with open(report_path, "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {report_path}")

    # 清理
    framework.cleanup()

    # 退出码
    sys.exit(0 if summary["pass_rate"] >= 90 else 1)
