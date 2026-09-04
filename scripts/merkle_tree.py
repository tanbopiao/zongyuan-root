#!/usr/bin/env python3
"""
P2-2: 标准Merkle树实现
支持SPV验证、Merkle证明、根哈希计算
"""
import hashlib
import json
from typing import List, Dict, Any, Tuple

class MerkleTree:
    """标准Merkle树（二叉）"""
    
    def __init__(self, leaves: List[str] = None):
        self.leaves = leaves or []
        self.tree = self._build_tree()
    
    def _hash_pair(self, left: str, right: str) -> str:
        return hashlib.sha256((left + right).encode()).hexdigest()
    
    def _build_tree(self) -> List[List[str]]:
        if not self.leaves:
            return [[]]
        tree = [sorted(self.leaves)]  # 叶子层排序
        while len(tree[-1]) > 1:
            layer = tree[-1]
            if len(layer) % 2 == 1:
                layer.append(layer[-1])  # 奇数复制最后一个
            next_layer = [
                self._hash_pair(layer[i], layer[i+1])
                for i in range(0, len(layer), 2)
            ]
            tree.append(next_layer)
        return tree
    
    @property
    def root(self) -> str:
        return self.tree[-1][0] if self.tree and self.tree[-1] else ""
    
    def get_proof(self, leaf: str) -> List[Dict[str, str]]:
        """获取Merkle证明（SPV）"""
        if leaf not in self.leaves:
            return []
        proof = []
        idx = sorted(self.leaves).index(leaf)
        for layer in self.tree[:-1]:
            if len(layer) % 2 == 1:
                layer = layer + [layer[-1]]
            if idx % 2 == 0:
                proof.append({"direction": "right", "hash": layer[idx + 1]})
            else:
                proof.append({"direction": "left", "hash": layer[idx - 1]})
            idx //= 2
        return proof
    
    def verify_proof(self, leaf: str, proof: List[Dict[str, str]], root: str) -> bool:
        """验证Merkle证明"""
        current = leaf
        for p in proof:
            if p["direction"] == "left":
                current = self._hash_pair(p["hash"], current)
            else:
                current = self._hash_pair(current, p["hash"])
        return current == root
    
    def to_dict(self) -> dict:
        return {
            "leaf_count": len(self.leaves),
            "root": self.root,
            "depth": len(self.tree),
            "tree_layers": [len(layer) for layer in self.tree]
        }

def build_merkle_from_files(directory: str) -> MerkleTree:
    """从目录文件构建Merkle树"""
    from pathlib import Path
    leaves = []
    for fp in Path(directory).rglob("*"):
        if fp.is_file() and "cache" not in str(fp):
            h = hashlib.sha256()
            with open(fp, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            leaves.append(h.hexdigest())
    return MerkleTree(leaves)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        directory = sys.argv[2] if len(sys.argv) > 2 else "."
        tree = build_merkle_from_files(directory)
        print(json.dumps(tree.to_dict(), ensure_ascii=False, indent=2))
    else:
        # 演示
        tree = MerkleTree(["a", "b", "c", "d"])
        print(json.dumps(tree.to_dict(), ensure_ascii=False, indent=2))
        proof = tree.get_proof("b")
        print(f"证明验证: {tree.verify_proof('b', proof, tree.root)}")
