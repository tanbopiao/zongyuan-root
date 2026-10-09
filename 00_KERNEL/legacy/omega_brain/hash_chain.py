#!/usr/bin/env python3
"""
L2 哈希层增强 - 全局哈希链 + Merkle成员证明

全局哈希链: 每个快照包含前一个快照的哈希，形成从创世到当前的连续链。
Merkle证明: 为每个资产生成Merkle成员证明路径，第三方可独立验证"该资产在树中"。
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple


class HashChain:
    """全局哈希链（快照链）"""

    def __init__(self, chain_dir: str = None):
        self.chain_dir = Path(chain_dir) if chain_dir else Path(__file__).parent.parent / 'hash_chain'
        self.chain_dir.mkdir(parents=True, exist_ok=True)
        self.chain_file = self.chain_dir / 'chain.jsonl'
        self._init_genesis()

    def _init_genesis(self):
        if not self.chain_file.exists():
            genesis = {
                'seq': 0,
                'type': 'GENESIS',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'merkle_root': '0' * 64,
                'prev_hash': '0' * 64,
                'data': {'chain_id': 'zongyuan_root', 'created_at': datetime.now(timezone.utc).isoformat()},
            }
            genesis['hash'] = self._compute_hash(genesis)
            with open(self.chain_file, 'w') as f:
                f.write(json.dumps(genesis, ensure_ascii=False) + '\n')

    def _compute_hash(self, block: dict) -> str:
        content = {k: v for k, v in block.items() if k != 'hash'}
        return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def append(self, merkle_root: str, block_type: str = 'SNAPSHOT', data: dict = None) -> dict:
        """追加一个区块到哈希链"""
        last = self.get_last()
        block = {
            'seq': last['seq'] + 1,
            'type': block_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'merkle_root': merkle_root,
            'prev_hash': last['hash'],
            'data': data or {},
        }
        block['hash'] = self._compute_hash(block)
        with open(self.chain_file, 'a') as f:
            f.write(json.dumps(block, ensure_ascii=False) + '\n')
        return block

    def get_last(self) -> dict:
        """获取最后一个区块"""
        last = None
        with open(self.chain_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    last = json.loads(line)
        return last

    def get_block(self, seq: int) -> Optional[dict]:
        """按序号获取区块"""
        with open(self.chain_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    block = json.loads(line)
                    if block['seq'] == seq:
                        return block
        return None

    def verify_chain(self) -> dict:
        """验证哈希链完整性"""
        blocks = []
        with open(self.chain_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    blocks.append(json.loads(line))

        errors = []
        prev_hash = '0' * 64
        for i, block in enumerate(blocks):
            if block['seq'] != i:
                errors.append({'seq': i, 'error': f'seq mismatch: expected {i}'})
                continue
            if block['prev_hash'] != prev_hash:
                errors.append({'seq': i, 'error': 'prev_hash mismatch'})
                continue
            expected = self._compute_hash(block)
            if block['hash'] != expected:
                errors.append({'seq': i, 'error': 'hash mismatch'})
                continue
            prev_hash = block['hash']

        return {
            'valid': len(errors) == 0,
            'total_blocks': len(blocks),
            'errors': errors,
            'genesis_hash': blocks[0]['hash'] if blocks else None,
            'latest_hash': blocks[-1]['hash'] if blocks else None,
            'latest_seq': blocks[-1]['seq'] if blocks else -1,
        }

    def get_chain_root(self) -> str:
        """获取链根哈希（最新区块哈希）"""
        last = self.get_last()
        return last['hash'] if last else '0' * 64


class MerkleProof:
    """Merkle成员证明生成与验证"""

    @staticmethod
    def _hash_pair(left: str, right: str) -> str:
        return hashlib.sha256((left + right).encode()).hexdigest()

    @staticmethod
    def generate_proof(leaves: List[str], index: int) -> dict:
        """
        为指定叶子生成Merkle证明路径

        Args:
            leaves: 叶子哈希列表
            index: 要证明的叶子索引

        Returns:
            {
                'leaf': str,
                'index': int,
                'path': [{'hash': str, 'direction': 'left'|'right'}],
                'root': str
            }
        """
        if index >= len(leaves):
            return {'error': 'index out of range'}

        # 构建Merkle树层级
        tree = MerkleProof._build_tree(leaves)
        path = []
        current_idx = index

        for level in range(len(tree) - 1):
            level_nodes = tree[level]
            if current_idx % 2 == 0:
                # 当前节点是左孩子，兄弟是右孩子
                sibling_idx = current_idx + 1
                if sibling_idx < len(level_nodes):
                    path.append({'hash': level_nodes[sibling_idx], 'direction': 'right'})
            else:
                # 当前节点是右孩子，兄弟是左孩子
                sibling_idx = current_idx - 1
                path.append({'hash': level_nodes[sibling_idx], 'direction': 'left'})
            current_idx = current_idx // 2

        return {
            'leaf': leaves[index],
            'index': index,
            'path': path,
            'root': tree[-1][0] if tree else None,
            'tree_depth': len(tree),
        }

    @staticmethod
    def _build_tree(leaves: List[str]) -> List[List[str]]:
        """构建Merkle树各层"""
        tree = [leaves[:]]
        current = leaves[:]
        while len(current) > 1:
            next_level = []
            for i in range(0, len(current), 2):
                if i + 1 < len(current):
                    next_level.append(MerkleProof._hash_pair(current[i], current[i + 1]))
                else:
                    # 奇数个节点，最后一个提升
                    next_level.append(current[i])
            tree.append(next_level)
            current = next_level
        return tree

    @staticmethod
    def verify_proof(leaf: str, proof_path: List[dict], root: str) -> bool:
        """
        验证Merkle成员证明

        Args:
            leaf: 叶子哈希
            proof_path: 证明路径
            root: 已知的Merkle根

        Returns:
            bool: 证明是否有效
        """
        current = leaf
        for step in proof_path:
            if step['direction'] == 'left':
                current = MerkleProof._hash_pair(step['hash'], current)
            else:
                current = MerkleProof._hash_pair(current, step['hash'])
        return current == root

    @staticmethod
    def generate_non_membership_proof(leaves: List[str], target_hash: str) -> dict:
        """
        生成非成员证明（证明某个哈希不在树中）
        简化版：检查target不在leaves中，并返回树的根和叶子数
        """
        is_member = target_hash in leaves
        return {
            'target': target_hash,
            'is_member': is_member,
            'leaf_count': len(leaves),
            'root': MerkleProof._build_tree(leaves)[-1][0] if leaves else None,
            'note': 'Non-membership proof: target not in leaf set' if not is_member else 'target IS a member'
        }


def main():
    """CLI入口"""
    import argparse
    parser = argparse.ArgumentParser(description='Hash Chain + Merkle Proof')
    sub = parser.add_subparsers(dest='command')

    # chain append
    a_p = sub.add_parser('append', help='Append block to hash chain')
    a_p.add_argument('--root', required=True, help='Merkle root')
    a_p.add_argument('--type', default='SNAPSHOT', help='Block type')

    # chain verify
    sub.add_parser('verify', help='Verify hash chain')

    # chain status
    sub.add_parser('status', help='Chain status')

    # merkle proof
    m_p = sub.add_parser('proof', help='Generate Merkle proof')
    m_p.add_argument('--leaves', required=True, help='Comma-separated leaf hashes')
    m_p.add_argument('--index', type=int, required=True, help='Leaf index')

    # merkle verify
    v_p = sub.add_parser('verify-proof', help='Verify Merkle proof')
    v_p.add_argument('--leaf', required=True, help='Leaf hash')
    v_p.add_argument('--root', required=True, help='Merkle root')
    v_p.add_argument('--path', required=True, help='Proof path JSON file')

    args = parser.parse_args()

    if args.command == 'append':
        chain = HashChain()
        block = chain.append(args.root, args.type)
        print(json.dumps(block, ensure_ascii=False, indent=2))
    elif args.command == 'verify':
        chain = HashChain()
        print(json.dumps(chain.verify_chain(), ensure_ascii=False, indent=2))
    elif args.command == 'status':
        chain = HashChain()
        last = chain.get_last()
        print(json.dumps({'latest_seq': last['seq'], 'latest_hash': last['hash'], 'merkle_root': last['merkle_root']}, ensure_ascii=False, indent=2))
    elif args.command == 'proof':
        leaves = args.leaves.split(',')
        proof = MerkleProof.generate_proof(leaves, args.index)
        print(json.dumps(proof, ensure_ascii=False, indent=2))
    elif args.command == 'verify-proof':
        with open(args.path) as f:
            proof_data = json.load(f)
        valid = MerkleProof.verify_proof(args.leaf, proof_data['path'], args.root)
        print(json.dumps({'valid': valid}, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
