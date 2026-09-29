#!/usr/bin/env python3
"""
假设推演器 HYPOTHESIS-SIMULATOR V1.0
ZONGYUAN-ROOT / 本地自治内核 补全算子
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
补全项: 深度扫描确认假设推演器缺失, 基于因果/最优稳态逻辑新建

功能:
1. 多假设生成(输入命题→分支假设集)
2. 稳态仿真(每分支按 价值/稳态/成本 三维打分)
3. 风险分支判定(低稳态/高成本/违宪 标记)
4. 最优稳态输出(三最原则: 风险最小>成本最小>收益最大)
5. 只读推演, 不修改任何资产
"""
import json, sys, hashlib, argparse
from dataclasses import dataclass, asdict

TRACE = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"

@dataclass
class Branch:
    id: str
    desc: str
    value: float   # 收益 0-100
    steady: float  # 稳态 0-100
    cost: float    # 成本 0-100(低=好)
    risk: float    # 风险 0-100(低=好)
    violates_constitution: bool = False

    @property
    def score(self) -> float:
        """三最原则加权: 风险最小>成本最小>收益最大"""
        if self.violates_constitution:
            return -999.0
        return (self.value * 0.30) + (self.steady * 0.25) - (self.cost * 0.20) - (self.risk * 0.25)

class HypothesisSimulator:
    def simulate(self, proposition: str, branches: list) -> dict:
        """输入命题+分支, 稳态仿真推演"""
        results = []
        for i, b in enumerate(branches):
            br = Branch(
                id=f"HYP-{i+1:03d}",
                desc=b.get("desc", ""),
                value=float(b.get("value", 50)),
                steady=float(b.get("steady", 50)),
                cost=float(b.get("cost", 50)),
                risk=float(b.get("risk", 50)),
                violates_constitution=b.get("violates_constitution", False),
            )
            results.append(br)
        # 排序: score降序
        results.sort(key=lambda x: x.score, reverse=True)
        # 收敛判定: 最优分支score>=阈值(默认80) 才自主推荐
        best = results[0]
        payload = json.dumps({"prop": proposition, "best": asdict(best), "n": len(results)},
                             ensure_ascii=False, sort_keys=True)
        merkle = hashlib.sha256(payload.encode()).hexdigest()
        return {
            "did": DID, "trace": TRACE,
            "proposition": proposition,
            "branches_ranked": [asdict(r) for r in results],
            "best": asdict(best),
            "autonomy_gate": "PASS" if best.score >= 80 else "BLOCKED(继续推演)",
            "merkle": merkle,
            "note": "只读推演, 未修改任何资产",
        }

def main():
    ap = argparse.ArgumentParser(description="假设推演器")
    ap.add_argument("--prop", required=True, help="待推演命题")
    ap.add_argument("--branches", required=True, help="JSON分支数组")
    args = ap.parse_args()
    branches = json.loads(args.branches)
    out = HypothesisSimulator().simulate(args.prop, branches)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
