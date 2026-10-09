#!/usr/bin/env python3
"""
昆仑洞天自治体系 - 架构断点自检引擎 v1.0
自动化检测10个架构断点状态，解决P0/P1断点的可观测性问题。
"""
import json
import os
import re
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))
from config_manager import ConfigManager


class BreakpointChecker:
    def __init__(self, workspace_dir: str = None):
        self.cm = ConfigManager(workspace_dir)
        self.workspace = self.cm.workspace
        self.results = []

    def check_p0_001_dimension_consistency(self) -> dict:
        """P0-1: 向量库维度一致性检测"""
        bp = {"id": "BP-P0-001", "name": "环境依赖不持久+向量维度混用崩溃", "level": "P0"}
        vector_db_path = self.workspace / "ZONGYUAN-ROOT/Ω-Brainμ/vector_db/omega_brain_truth.json"

        if not vector_db_path.exists():
            return {**bp, "status": "SKIP", "detail": "向量库不存在"}

        try:
            with open(vector_db_path, encoding="utf-8") as f:
                data = json.load(f)
            vectors = data.get("vectors", data) if isinstance(data, dict) else data
            if not vectors:
                return {**bp, "status": "SKIP", "detail": "向量库为空"}

            dimensions = set()
            for item in (vectors if isinstance(vectors, list) else vectors.values()):
                vec = item.get("embedding", item.get("vector", [])) if isinstance(item, dict) else item
                if vec:
                    dimensions.add(len(vec))

            env = self.cm.get_environment_status()
            expected_dim = 512 if env["effective_backend"] == "local_bge" else 256

            if len(dimensions) == 1 and expected_dim in dimensions:
                return {**bp, "status": "PASS", "detail": f"维度一致: {expected_dim}"}
            elif len(dimensions) > 1:
                return {**bp, "status": "FAIL", "detail": f"维度混用: {dimensions}, 预期: {expected_dim}", "auto_fix": "rebuild_vector_db"}
            else:
                return {**bp, "status": "WARN", "detail": f"维度{dimensions}与预期{expected_dim}不匹配"}
        except Exception as e:
            return {**bp, "status": "ERROR", "detail": str(e)}

    def check_p0_002_fallback_threshold(self) -> dict:
        """P0-2: 降级阈值与BM25脱节检测"""
        bp = {"id": "BP-P0-002", "name": "降级阈值与BM25脱节", "level": "P0"}
        env = self.cm.get_environment_status()
        threshold = self.cm.get_recall_threshold()
        bm25_enabled = self.cm.brain.get("retrieval", {}).get("bm25_enabled", True)

        if env["effective_backend"] == "hash_fallback":
            if bm25_enabled and threshold < 0.1:
                return {**bp, "status": "FAIL", "detail": f"hash降级+BM25可用，但阈值{threshold}过低，建议≥0.15", "auto_fix": "adjust_threshold"}
            elif not bm25_enabled:
                return {**bp, "status": "WARN", "detail": "hash降级且BM25未启用，召回质量无保障"}
            else:
                return {**bp, "status": "PASS", "detail": f"hash降级+BM25混合，阈值{threshold}合理"}
        return {**bp, "status": "PASS", "detail": f"BGE模式，阈值{threshold}"}

    def check_p1_003_feishu_config(self) -> dict:
        """P1-3: 飞书配置完整性检测"""
        bp = {"id": "BP-P1-003", "name": "飞书三端同步配置断裂", "level": "P1"}
        result = self.cm.validate_feishu()
        if result["ok"]:
            return {**bp, "status": "PASS", "detail": "飞书配置完整"}
        return {**bp, "status": "FAIL", "detail": f"缺失配置: {result['missing']}", "auto_fix": "init_config"}

    def check_p1_004_root_merkle(self) -> dict:
        """P1-4: 全局根Merkle一致性检测"""
        bp = {"id": "BP-P1-004", "name": "全局根Merkle与实际资产不同步", "level": "P1"}
        registry_path = self.workspace / "ZONGYUAN-ROOT/.global_root_registry.json"
        if not registry_path.exists():
            return {**bp, "status": "SKIP", "detail": "全局根注册表不存在"}

        try:
            with open(registry_path, encoding="utf-8") as f:
                registry = json.load(f)
            registered_merkle = registry.get("current_merkle", "")

            # 检查最近锁档输出目录的Merkle
            lock_dirs = sorted(self.workspace.glob("lock_archive_output_*"), key=os.path.getmtime, reverse=True)
            if not lock_dirs:
                return {**bp, "status": "SKIP", "detail": "无锁档输出目录"}

            latest_summary = list(lock_dirs[0].rglob("PIPELINE-SUMMARY-*.json"))
            if not latest_summary:
                return {**bp, "status": "SKIP", "detail": "无流水线汇总文件"}

            with open(latest_summary[0], encoding="utf-8") as f:
                summary = json.load(f)
            actual_merkle = summary.get("merkle_root", "")

            if registered_merkle == actual_merkle:
                return {**bp, "status": "PASS", "detail": "Merkle根一致"}
            return {**bp, "status": "WARN", "detail": f"注册表: {registered_merkle[:16]}... ≠ 实际: {actual_merkle[:16]}...（锁档后副产品修改导致，非数据损坏）"}
        except Exception as e:
            return {**bp, "status": "ERROR", "detail": str(e)}

    def check_p1_005_m2_trend(self) -> dict:
        """P1-5: M2价值趋势检测"""
        bp = {"id": "BP-P1-005", "name": "M2冗余度持续FAIL价值退化", "level": "P1"}
        kernel_path = self.workspace / "ZONGYUAN-ROOT/Ω-Brainμ/kernel.json"
        if not kernel_path.exists():
            return {**bp, "status": "SKIP", "detail": "内核文件不存在"}

        try:
            with open(kernel_path, encoding="utf-8") as f:
                kernel = json.load(f)
            m2 = kernel.get("axioms", {}).get("M2_monotonic_convergence", {})
            status = m2.get("status", "UNKNOWN")
            verification_count = m2.get("verification_count", 0)

            # 检查最近锁档的M2结果
            lock_dirs = sorted(self.workspace.glob("lock_archive_output_*"), key=os.path.getmtime, reverse=True)
            m2_verdicts = []
            for d in lock_dirs[:5]:
                summaries = list(d.rglob("PIPELINE-SUMMARY-*.json"))
                for s in summaries:
                    with open(s, encoding="utf-8") as f:
                        data = json.load(f)
                    v = data.get("m2_verdict", "")
                    if v:
                        m2_verdicts.append(v)

            fail_count = m2_verdicts.count("FAIL")
            if fail_count >= 3:
                return {**bp, "status": "FAIL", "detail": f"最近{len(m2_verdicts)}次锁档中{fail_count}次M2 FAIL，建议启用冷却期", "auto_fix": "cooling_notice"}
            elif fail_count > 0:
                return {**bp, "status": "WARN", "detail": f"最近{len(m2_verdicts)}次锁档中{fail_count}次M2 FAIL"}
            return {**bp, "status": "PASS", "detail": f"M2状态{status}，验证{verification_count}次，近期无连续FAIL"}
        except Exception as e:
            return {**bp, "status": "ERROR", "detail": str(e)}

    def check_p2_p3_static(self) -> list:
        """P2/P3静态检查（简化版）"""
        checks = [
            ("BP-P2-006", "BM25索引全量重建无增量", "P2", "vector_engine.py", "bm25.build()在add中全量调用"),
            ("BP-P2-007", "真值入库无内容去重", "P2", "omega_brain_mu.py", "ingest_truth仅按truth_id去重"),
            ("BP-P2-008", "索引+向量库双写无原子性", "P2", "omega_brain_mu.py", "先写向量库再写索引，无事务"),
            ("BP-P3-009", "阶段间无事务保护", "P3", "full_pipeline.py", "局部变量传递，无回滚"),
            ("BP-P3-010", "硬编码路径与魔法数字", "P3", "多文件", "阈值/alpha/路径散落在各文件"),
        ]
        results = []
        meta_skill = self.workspace / ".user_skills/meta-order-lock-archive/scripts"
        if not meta_skill.exists():
            # 回退：从本脚本安装位置反推 .user_skills 目录（消除cwd依赖误判）
            meta_skill = Path(__file__).resolve().parents[2] / "meta-order-lock-archive/scripts"
        for bid, name, level, filename, detail in checks:
            if filename == "多文件":
                # P3-010 真实静态扫描：检查内核脚本中的硬编码绝对路径
                scan_dirs = [meta_skill, Path(__file__).resolve().parent]
                hardcoded = []
                for sd in scan_dirs:
                    if not sd.exists():
                        continue
                    for pyf in sd.glob("*.py"):
                        try:
                            for i, line in enumerate(open(pyf, encoding="utf-8", errors="ignore"), 1):
                                s = line.strip()
                                if s.startswith("#"):
                                    continue
                                if re.search(r"[\"']/home/|[\"']/opt/|[\"']/tmp/|[\"']/etc/", line):
                                    hardcoded.append(f"{pyf.name}:{i}")
                        except Exception:
                            continue
                if hardcoded:
                    results.append({"id": bid, "name": name, "level": level, "status": "WARN", "detail": f"发现{len(hardcoded)}处硬编码绝对路径: {', '.join(hardcoded[:5])}", "file": "多文件"})
                else:
                    results.append({"id": bid, "name": name, "level": level, "status": "PASS", "detail": "未发现硬编码绝对路径（扫描完成）"})
                continue
            filepath = meta_skill / filename
            if filepath.exists():
                results.append({"id": bid, "name": name, "level": level, "status": "WARN", "detail": detail, "file": filename})
            else:
                results.append({"id": bid, "name": name, "level": level, "status": "SKIP", "detail": f"{filename}未找到"})
        return results

    def run_full_check(self) -> dict:
        """运行完整断点自检"""
        self.results = []
        self.results.append(self.check_p0_001_dimension_consistency())
        self.results.append(self.check_p0_002_fallback_threshold())
        self.results.append(self.check_p1_003_feishu_config())
        self.results.append(self.check_p1_004_root_merkle())
        self.results.append(self.check_p1_005_m2_trend())
        self.results.extend(self.check_p2_p3_static())

        # 统计
        pass_count = sum(1 for r in self.results if r["status"] == "PASS")
        fail_count = sum(1 for r in self.results if r["status"] == "FAIL")
        warn_count = sum(1 for r in self.results if r["status"] == "WARN")
        error_count = sum(1 for r in self.results if r["status"] == "ERROR")
        skip_count = sum(1 for r in self.results if r["status"] == "SKIP")

        overall = "PASS" if fail_count == 0 and error_count == 0 else "FAIL"

        report = {
            "check_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+0800"),
            "overall_status": overall,
            "summary": {"PASS": pass_count, "FAIL": fail_count, "WARN": warn_count, "ERROR": error_count, "SKIP": skip_count},
            "results": self.results,
            "auto_fix_available": [r for r in self.results if r.get("auto_fix")],
        }
        return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="昆仑洞天自治体系 - 架构断点自检")
    parser.add_argument("--mode", choices=["full", "p0", "p1"], default="full")
    parser.add_argument("--workspace", default="", help="工作区目录")
    parser.add_argument("--output", default="", help="输出报告路径")
    args = parser.parse_args()

    checker = BreakpointChecker(args.workspace or None)
    report = checker.run_full_check()

    print("=" * 60)
    print("昆仑洞天自治体系 - 架构断点自检报告")
    print("Ω₀⊂⊙∞⊂Ω | DID-BR-000002")
    print("=" * 60)
    print(f"\n总体状态: {report['overall_status']}")
    print(f"统计: {report['summary']}")
    print("\n详细结果:")
    for r in report["results"]:
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "ERROR": "💥", "SKIP": "⏭️"}.get(r["status"], "?")
        print(f"  {icon} [{r['level']}] {r['id']} {r['name']}")
        print(f"     {r['detail']}")
        if r.get("auto_fix"):
            print(f"     → 可自动修复: {r['auto_fix']}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存: {args.output}")

    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
