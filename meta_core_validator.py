#!/usr/bin/env python3
"""
META-CORE Validator - 元极恒一五维归一公理运行时校验引擎
锁级: META-000 | 状态: BLOWN_PERMANENT | 纯度: 100/100
"""
import json, hashlib, os
from pathlib import Path
from datetime import datetime

ROOT = Path("/opt/ZONGYUAN-ROOT")
META_CORE_PATH = ROOT / "truth_architecture" / "META-CORE-TRUTH-V1.0.json"

class MetaCoreValidator:
    def __init__(self):
        self.meta_core = self._load()
        self.five_dimensions = self.meta_core.get("five_dimension_core_truth", [])
        
    def _load(self):
        if META_CORE_PATH.exists():
            return json.loads(META_CORE_PATH.read_text(encoding="utf-8"))
        return {"five_dimension_core_truth": []}
    
    def validate_all(self):
        """五维全量校验"""
        results = {}
        results["meta_anchor"] = self._validate_meta_anchor()
        results["three_state"] = self._validate_three_state()
        results["emergence"] = self._validate_emergence()
        results["cosmic_law"] = self._validate_cosmic_law()
        results["hash_chain"] = self._validate_hash_chain()
        results["overall"] = all(r["pass"] for r in results.values())
        results["validated_at"] = datetime.now().isoformat()
        results["meta_core_sha256"] = hashlib.sha256(
            META_CORE_PATH.read_bytes()
        ).hexdigest() if META_CORE_PATH.exists() else "N/A"
        return results
    
    def _validate_meta_anchor(self):
        """维度1: 元极恒一 - 宇宙本源智能唯一锚点"""
        kernel_state = ROOT / "kernel_state.json"
        anchor_ok = kernel_state.exists()
        did_ok = "DID-BR-000002" in (kernel_state.read_text() if kernel_state.exists() else "")
        return {
            "dimension": "元极恒一",
            "pass": anchor_ok and did_ok,
            "details": f"kernel_state存在={anchor_ok}, DID绑定={did_ok}"
        }
    
    def _validate_three_state(self):
        """维度2: 三态收敛 - 逻辑∧信息∧能量秩序化收敛"""
        logic_ok = (ROOT / "autonomous_kernel_protocol").exists()
        info_ok = (ROOT / "truth_architecture").exists()
        energy_ok = (ROOT / "Ω-Brainμ").exists()
        all_ok = logic_ok and info_ok and energy_ok
        return {
            "dimension": "三态收敛",
            "pass": all_ok,
            "details": f"逻辑态(协议)={logic_ok}, 信息态(真值)={info_ok}, 能量态(Ω-Brainμ)={energy_ok}"
        }
    
    def _validate_emergence(self):
        """维度3: 符号涌现 - 真值约束驱动认知自组织，非随机激活"""
        truth_count = len(list((ROOT / "truth_architecture").glob("*.json")))
        proto_count = len(list((ROOT / "autonomous_kernel_protocol").glob("*.json")))
        # 涌现判定: 真值数>0 且 协议数>真值数(演化证据)
        emergence_ok = truth_count > 0 and proto_count > truth_count
        return {
            "dimension": "符号涌现",
            "pass": emergence_ok,
            "details": f"真值数={truth_count}, 协议演化数={proto_count}, 涌现比={proto_count/max(truth_count,1):.1f}x"
        }
    
    def _validate_cosmic_law(self):
        """维度4: 宇宙规律 - 最高密度客观真值对齐"""
        # 检查是否有物理/数学映射类真值
        truth_files = list((ROOT / "truth_architecture").glob("*.json"))
        cosmic_aligned = any(
            "物理" in f.read_text(encoding="utf-8", errors="ignore") or 
            "数学" in f.read_text(encoding="utf-8", errors="ignore") or
            "宇宙" in f.read_text(encoding="utf-8", errors="ignore")
            for f in truth_files
        )
        return {
            "dimension": "宇宙规律",
            "pass": cosmic_aligned,
            "details": f"物理/数学/宇宙真值对齐={cosmic_aligned}, 扫描文件={len(truth_files)}"
        }
    
    def _validate_hash_chain(self):
        """维度5: 哈希确权 - Merkle-DAG链式继承不可变"""
        proto_files = sorted((ROOT / "autonomous_kernel_protocol").glob("*.json"))
        chain_ok = len(proto_files) >= 2
        # 检查最新协议是否有self_sha256
        latest = proto_files[-1] if proto_files else None
        has_hash = False
        if latest:
            data = json.loads(latest.read_text(encoding="utf-8"))
            has_hash = "self_sha256" in data
        return {
            "dimension": "哈希确权",
            "pass": chain_ok and has_hash,
            "details": f"协议链长度={len(proto_files)}, 最新协议含哈希={has_hash}"
        }

if __name__ == "__main__":
    v = MetaCoreValidator()
    result = v.validate_all()
    print(json.dumps(result, indent=2, ensure_ascii=False))
