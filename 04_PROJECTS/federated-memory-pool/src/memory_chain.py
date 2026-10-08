#!/usr/bin/env python3
"""
记忆链维护（开源版）— 每次锁档后自动生成下一个种子
哈希链式继承: seed-N 的哈希包含 seed-(N-1) 的哈希, 不可篡改
"""
import json, hashlib, os
from datetime import datetime

TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"

def sha256(content: dict) -> str:
    """计算内容哈希"""
    payload = json.dumps(content, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()

class MemoryChain:
    """记忆链维护器"""

    def __init__(self, chain_dir: str):
        self.chain_dir = chain_dir
        os.makedirs(chain_dir, exist_ok=True)

    def seed_count(self) -> int:
        """当前种子数量"""
        return len([
            f for f in os.listdir(self.chain_dir)
            if f.startswith("seed-") and f.endswith(".json")
        ])

    def last_hash(self) -> str:
        """上一个种子的哈希"""
        n = self.seed_count()
        if n == 0:
            return "0" * 64
        with open(f"{self.chain_dir}/seed-{n:03d}.json") as f:
            return json.load(f).get("hash", "0" * 64)

    def generate_next(self, trigger: str = "auto_lock", metadata: dict = None) -> dict:
        """生成下一个记忆种子（链式继承）"""
        count = self.seed_count()
        next_num = count + 1
        prev_hash = self.last_hash()

        seed_content = {
            "seed_id": f"seed-{next_num:03d}",
            "sequence": next_num,
            "timestamp": datetime.now().isoformat(),
            "previous_hash": prev_hash,
            "trigger": trigger,
            "metadata": metadata or {}
        }
        seed_content["hash"] = sha256(seed_content)

        with open(f"{self.chain_dir}/seed-{next_num:03d}.json", "w") as f:
            json.dump(seed_content, f, ensure_ascii=False, indent=2)
        return seed_content

    def verify_chain(self) -> tuple:
        """校验整条记忆链的哈希继承完整性"""
        n = self.seed_count()
        broken = []
        prev = "0" * 64
        for i in range(1, n + 1):
            with open(f"{self.chain_dir}/seed-{i:03d}.json") as f:
                seed = json.load(f)
            expected = sha256({k: v for k, v in seed.items() if k != "hash"})
            if seed.get("hash") != expected or seed.get("previous_hash") != prev:
                broken.append(i)
            prev = seed.get("hash")
        return n, broken

if __name__ == "__main__":
    import tempfile
    chain = MemoryChain(tempfile.mkdtemp())
    for i in range(3):
        seed = chain.generate_next(trigger=f"test-{i}")
        print(f"生成: {seed['seed_id']} prev={seed['previous_hash'][:8]}... hash={seed['hash'][:12]}...")
    total, broken = chain.verify_chain()
    print(f"[{TRACE_MARK}] 记忆链校验: {total}个种子, 断裂节点={broken if broken else '无(完整)'}")
