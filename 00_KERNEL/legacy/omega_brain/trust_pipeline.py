#!/usr/bin/env python3
"""
可信真值源七层进化流水线

一键执行 L1→L7 全流程:
  L1 CAS存储 → L2 Merkle+哈希链 → L3 时间戳 → L4 BFT共识 → L5 计算审计 → L6 审计日志 → L7 区块链锚定

每次快照自动走七层全流程，生成完整的可信凭证包。
"""

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

# 导入七层组件
sys.path.insert(0, str(Path(__file__).parent))
from cas_store import CASStore
from hash_chain import HashChain, MerkleProof
from timestamp_client import TimestampClient
from consensus_engine import ConsensusEngine, Node
from replay_verifier import ComputeAuditLog, ReplayVerifier, deterministic
from audit_log import AuditLog
from blockchain_anchor import BlockchainAnchor


class TrustPipeline:
    """可信真值源七层流水线"""

    def __init__(self, pipeline_dir: str = None, node_count: int = 4,
                 blockchain: str = 'polygon_mumbai'):
        self.pipeline_dir = Path(pipeline_dir) if pipeline_dir else Path(__file__).parent.parent / 'trust_pipeline'
        self.pipeline_dir.mkdir(parents=True, exist_ok=True)

        # 初始化七层组件
        self.cas = CASStore(store_dir=str(self.pipeline_dir / 'cas'))
        self.hash_chain = HashChain(chain_dir=str(self.pipeline_dir / 'hash_chain'))
        self.timestamp = TimestampClient(storage_dir=str(self.pipeline_dir / 'timestamps'))
        nodes = [Node(f'node-{i+1}') for i in range(node_count)]
        self.consensus = ConsensusEngine(nodes=nodes, consensus_dir=str(self.pipeline_dir / 'consensus'))
        self.compute_audit = ComputeAuditLog(log_dir=str(self.pipeline_dir / 'compute_audit'))
        self.audit = AuditLog(log_dir=str(self.pipeline_dir / 'audit_logs'), chain_id='trust_pipeline')
        self.anchor = BlockchainAnchor(storage_dir=str(self.pipeline_dir / 'blockchain_anchors'),
                                        chain=blockchain)

        self.run_count = 0

    @deterministic(version='1.0.0')
    def _compute_merkle_root(self, leaves: list) -> str:
        """计算Merkle根（纯函数，自动审计）"""
        if not leaves:
            return '0' * 64
        current = leaves[:]
        while len(current) > 1:
            next_level = []
            for i in range(0, len(current), 2):
                if i + 1 < len(current):
                    combined = current[i] + current[i + 1]
                else:
                    combined = current[i] + current[i]
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            current = next_level
        return current[0]

    def execute(self, data: bytes, data_type: str = 'snapshot',
                metadata: dict = None, description: str = '') -> Dict[str, Any]:
        """
        执行七层全流程

        Args:
            data: 要锚定的数据
            data_type: 数据类型 (snapshot/truth_formula/asset/etc)
            metadata: 附加元数据
            description: 描述

        Returns:
            七层执行结果凭证包
        """
        self.run_count += 1
        run_id = f'RUN-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}-{self.run_count:04d}'
        start_time = time.time()
        results = {'run_id': run_id, 'data_type': data_type, 'started_at': datetime.now(timezone.utc).isoformat()}

        try:
            # ===== L1: 内容寻址存储 =====
            l1_start = time.time()
            cid = self.cas.put(data, {'type': data_type, **(metadata or {})})
            self.cas.set_ref(f'HEAD/{data_type}-{self.run_count:04d}', cid)
            l1_ok = self.cas.get(cid) == data
            results['L1_cas'] = {
                'content_id': cid,
                'size': len(data),
                'ref': f'HEAD/{data_type}-{self.run_count:04d}',
                'verified': l1_ok,
                'duration_ms': round((time.time() - l1_start) * 1000, 2),
            }

            # ===== L2: Merkle树 + 哈希链 =====
            l2_start = time.time()
            # 用CID和元数据构建叶子
            leaves = [cid, hashlib.sha256(json.dumps(metadata or {}, sort_keys=True).encode()).hexdigest(),
                      hashlib.sha256(data_type.encode()).hexdigest(),
                      hashlib.sha256(description.encode()).hexdigest(),
                      hashlib.sha256(str(time.time()).encode()).hexdigest()]
            # 补全到8个叶子
            while len(leaves) < 8:
                leaves.append(hashlib.sha256(f'padding-{len(leaves)}'.encode()).hexdigest())

            merkle_root = self._compute_merkle_root(leaves)
            proof = MerkleProof.generate_proof(leaves, 0)
            proof_valid = MerkleProof.verify_proof(leaves[0], proof['path'], merkle_root)

            block = self.hash_chain.append(merkle_root, 'SNAPSHOT',
                                           {'cid': cid, 'run_id': run_id, 'data_type': data_type})
            chain_valid = self.hash_chain.verify_chain()['valid']

            results['L2_hash'] = {
                'merkle_root': merkle_root,
                'leaf_count': len(leaves),
                'merkle_proof_valid': proof_valid,
                'chain_seq': block['seq'],
                'chain_hash': block['hash'],
                'chain_valid': chain_valid,
                'duration_ms': round((time.time() - l2_start) * 1000, 2),
            }

            # ===== L3: RFC3161时间戳 =====
            l3_start = time.time()
            ts_result = self.timestamp.timestamp_merkle_root(merkle_root, f'{run_id} {description}')
            results['L3_timestamp'] = {
                'tsa_count': ts_result['tsa_count'],
                'success_count': ts_result['success_count'],
                'timestamps': [
                    {'tsa': t['tsa'], 'time': t.get('timestamp_time'), 'success': t['success']}
                    for t in ts_result['timestamps']
                ],
                'duration_ms': round((time.time() - l3_start) * 1000, 2),
            }

            # ===== L4: BFT共识 =====
            l4_start = time.time()
            consensus_result = self.consensus.reach_consensus(
                merkle_root,
                {'cid': cid, 'run_id': run_id, 'data_type': data_type, 'merkle_root': merkle_root}
            )
            proof_ok = self.consensus.verify_consensus_proof(consensus_result['consensus_proof'])
            results['L4_consensus'] = {
                'success': consensus_result['success'],
                'nodes': len(self.consensus.nodes),
                'byzantine_tolerance': self.consensus.f,
                'quorum': self.consensus.quorum,
                'votes': consensus_result['votes'],
                'block_number': consensus_result['block_number'],
                'proof_valid': proof_ok,
                'duration_ms': round((time.time() - l4_start) * 1000, 2),
            }

            # ===== L5: 计算审计（已在_compute_merkle_root中自动记录） =====
            l5_start = time.time()
            log_integrity = ReplayVerifier(self.compute_audit).verify_log_integrity()
            sample = ReplayVerifier(self.compute_audit).sample_replay_test(3)
            results['L5_compute_audit'] = {
                'total_computations': self.compute_audit.stats()['total_computations'],
                'log_integrity': log_integrity['valid'],
                'sample_pass_rate': sample.get('pass_rate', 0),
                'duration_ms': round((time.time() - l5_start) * 1000, 2),
            }

            # ===== L6: append-only审计 =====
            l6_start = time.time()
            audit_entry = self.audit.append(
                op_type='TRUST_PIPELINE',
                operator='pipeline',
                data_hash=merkle_root,
                details={
                    'run_id': run_id, 'cid': cid, 'data_type': data_type,
                    'consensus_block': consensus_result['block_number'],
                    'timestamp_count': ts_result['success_count'],
                }
            )
            audit_valid = self.audit.verify_chain()['valid']
            results['L6_audit'] = {
                'seq': audit_entry['seq'],
                'hash': audit_entry['hash'],
                'chain_valid': audit_valid,
                'chain_root': self.audit.export_chain_hash(),
                'duration_ms': round((time.time() - l6_start) * 1000, 2),
            }

            # ===== L7: 区块链锚定 =====
            l7_start = time.time()
            anchor_result = self.anchor.daily_anchor(merkle_root, run_id)
            anchor_verified = self.anchor.verify_anchor(merkle_root)['verified']
            results['L7_blockchain'] = {
                'success': anchor_result['success'],
                'chain': anchor_result['chain'],
                'tx_hash': anchor_result['tx_hash'],
                'block_number': anchor_result['block_number'],
                'simulated': anchor_result.get('simulated', False),
                'verified': anchor_verified,
                'duration_ms': round((time.time() - l7_start) * 1000, 2),
            }

            # ===== 汇总 =====
            all_pass = all([
                results['L1_cas']['verified'],
                results['L2_hash']['merkle_proof_valid'] and results['L2_hash']['chain_valid'],
                results['L3_timestamp']['success_count'] > 0,
                results['L4_consensus']['success'] and results['L4_consensus']['proof_valid'],
                results['L5_compute_audit']['log_integrity'],
                results['L6_audit']['chain_valid'],
                results['L7_blockchain']['success'],
            ])

            results['summary'] = {
                'all_pass': all_pass,
                'total_duration_ms': round((time.time() - start_time) * 1000, 2),
                'merkle_root': merkle_root,
                'content_id': cid,
                'run_id': run_id,
            }
            results['completed_at'] = datetime.now(timezone.utc).isoformat()

            # 保存凭证包
            self._save_credential(results)
            return results

        except Exception as e:
            results['error'] = str(e)
            results['summary'] = {'all_pass': False, 'error': str(e)}
            self._save_credential(results)
            return results

    def _save_credential(self, results: dict):
        """保存执行凭证包"""
        cred_file = self.pipeline_dir / 'credentials' / f'{results["run_id"]}.json'
        cred_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cred_file, 'w') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    def verify_credential(self, run_id: str) -> dict:
        """验证历史执行凭证"""
        cred_file = self.pipeline_dir / 'credentials' / f'{run_id}.json'
        if not cred_file.exists():
            return {'valid': False, 'error': 'credential not found'}

        with open(cred_file) as f:
            cred = json.load(f)

        # 验证各层
        checks = {}
        checks['L1_cas_exists'] = self.cas.exists(cred.get('L1_cas', {}).get('content_id', ''))
        checks['L2_chain_valid'] = self.hash_chain.verify_chain()['valid']
        checks['L4_proof_valid'] = self.consensus.verify_consensus_proof(
            cred.get('L4_consensus', {}).get('consensus_proof', {})) if 'consensus_proof' in cred.get('L4_consensus', {}) else False
        checks['L6_audit_valid'] = self.audit.verify_chain()['valid']
        checks['L7_anchor_verified'] = self.anchor.verify_anchor(
            cred.get('summary', {}).get('merkle_root', ''))['verified']

        return {
            'run_id': run_id,
            'valid': all(checks.values()),
            'checks': checks,
            'all_pass': cred.get('summary', {}).get('all_pass'),
        }

    def list_runs(self, limit: int = 10) -> list:
        """列出历史执行"""
        creds = []
        cred_dir = self.pipeline_dir / 'credentials'
        if cred_dir.exists():
            for fp in sorted(cred_dir.glob('RUN-*.json'), reverse=True)[:limit]:
                with open(fp) as f:
                    cred = json.load(f)
                creds.append({
                    'run_id': cred['run_id'],
                    'data_type': cred.get('data_type'),
                    'all_pass': cred.get('summary', {}).get('all_pass'),
                    'merkle_root': cred.get('summary', {}).get('merkle_root', '')[:16],
                    'completed_at': cred.get('completed_at'),
                })
        return creds


def main():
    """CLI入口"""
    import argparse
    parser = argparse.ArgumentParser(description='Trust Pipeline - 七层可信真值源流水线')
    sub = parser.add_subparsers(dest='command')

    # run
    r_p = sub.add_parser('run', help='执行七层流水线')
    r_p.add_argument('--data', required=True, help='数据字符串或文件路径')
    r_p.add_argument('--type', default='snapshot', help='数据类型')
    r_p.add_argument('--desc', default='', help='描述')
    r_p.add_argument('--nodes', type=int, default=4, help='共识节点数')

    # verify
    v_p = sub.add_parser('verify', help='验证执行凭证')
    v_p.add_argument('--run-id', required=True, help='Run ID')

    # list
    sub.add_parser('list', help='列出历史执行')

    args = parser.parse_args()

    if args.command == 'run':
        # 解析数据
        if Path(args.data).is_file():
            with open(args.data, 'rb') as f:
                data = f.read()
        else:
            data = args.data.encode()

        pipeline = TrustPipeline(node_count=args.nodes)
        result = pipeline.execute(data, data_type=args.type, description=args.desc)
        # 只输出摘要
        summary = result.get('summary', {})
        print(json.dumps({
            'run_id': result['run_id'],
            'all_pass': summary.get('all_pass'),
            'merkle_root': summary.get('merkle_root'),
            'content_id': summary.get('content_id'),
            'duration_ms': summary.get('total_duration_ms'),
            'layers': {k: v.get('verified', v.get('success', v.get('chain_valid', '?')))
                       for k, v in result.items() if k.startswith('L')},
        }, ensure_ascii=False, indent=2))

    elif args.command == 'verify':
        pipeline = TrustPipeline()
        result = pipeline.verify_credential(args.run_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == 'list':
        pipeline = TrustPipeline()
        runs = pipeline.list_runs()
        print(json.dumps({'count': len(runs), 'runs': runs}, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
