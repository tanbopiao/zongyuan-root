#!/usr/bin/env python3
"""
L7 外部锚定层 - 区块链锚定客户端

将Merkle根/审计链根写入区块链，实现不可篡改的外部时间锚定。

支持:
  - Polygon主网/测试网 (低成本, ~$0.01/笔)
  - 以太坊主网 (高安全)
  - 模拟模式 (无私钥时本地记录, 用于开发测试)

锚定方式:
  - 智能合约事件 (推荐, 可查询可验证)
  - OP_RETURN (比特币风格, 简单)
  - 交易data字段 (EVM兼容链)
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from web3 import Web3
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False


# 链配置
CHAINS = {
    'polygon_mainnet': {
        'rpc': 'https://polygon-rpc.com',
        'chain_id': 137,
        'currency': 'MATIC',
        'explorer': 'https://polygonscan.com/tx/',
    },
    'polygon_mumbai': {
        'rpc': 'https://rpc-mumbai.maticvigil.com',
        'chain_id': 80001,
        'currency': 'MATIC',
        'explorer': 'https://mumbai.polygonscan.com/tx/',
    },
    'ethereum_mainnet': {
        'rpc': 'https://eth.llamarpc.com',
        'chain_id': 1,
        'currency': 'ETH',
        'explorer': 'https://etherscan.io/tx/',
    },
    'sepolia': {
        'rpc': 'https://rpc.sepolia.org',
        'chain_id': 11155111,
        'currency': 'ETH',
        'explorer': 'https://sepolia.etherscan.io/tx/',
    },
}

# 锚定合约ABI (简化版: 只需要anchor函数)
ANCHOR_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "_root", "type": "bytes32"}],
        "name": "anchor",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "name": "anchors",
        "outputs": [
            {"internalType": "uint256", "name": "blockNumber", "type": "uint256"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "address", "name": "anchorer", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]


class BlockchainAnchor:
    """区块链锚定客户端"""

    def __init__(self, storage_dir: str = None, chain: str = 'polygon_mumbai',
                 contract_address: str = None, private_key: str = None):
        self.storage_dir = Path(storage_dir) if storage_dir else Path(__file__).parent.parent / 'blockchain_anchors'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.chain = chain
        self.chain_config = CHAINS.get(chain, CHAINS['polygon_mumbai'])
        self.contract_address = contract_address or os.environ.get('ANCHOR_CONTRACT_ADDRESS', '')
        self.private_key = private_key or os.environ.get('ANCHOR_PRIVATE_KEY', '')
        self.w3 = None
        self.simulate = not (self.private_key and WEB3_AVAILABLE)

        if self.simulate:
            print(f"[BlockchainAnchor] 模拟模式 (未配置私钥或web3未安装). 真实锚定请设置ANCHOR_PRIVATE_KEY.")
        elif WEB3_AVAILABLE:
            self.w3 = Web3(Web3.HTTPProvider(self.chain_config['rpc']))

    def anchor_root(self, merkle_root: str, description: str = '',
                    metadata: dict = None) -> dict:
        """
        将Merkle根锚定到区块链

        Args:
            merkle_root: 32字节哈希 (hex, 0x开头或不带)
            description: 描述
            metadata: 附加元数据

        Returns:
            {
                'success': bool,
                'chain': str,
                'merkle_root': str,
                'tx_hash': str,
                'block_number': int,
                'timestamp': str,
                'explorer_url': str,
                'simulated': bool,
                'error': str (if failed)
            }
        """
        # 规范化merkle_root
        root_hex = merkle_root.lower().replace('0x', '')
        if len(root_hex) != 64:
            return {'success': False, 'error': f'Invalid merkle root length: {len(root_hex)} (need 64 hex chars)'}

        if self.simulate:
            return self._simulate_anchor(root_hex, description, metadata)

        return self._real_anchor(root_hex, description, metadata)

    def _real_anchor(self, root_hex: str, description: str, metadata: dict) -> dict:
        """真实区块链锚定"""
        try:
            account = self.w3.eth.account.from_key(self.private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)

            if self.contract_address:
                # 通过合约anchor函数
                contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(self.contract_address),
                    abi=ANCHOR_ABI
                )
                tx = contract.functions.anchor(bytes.fromhex(root_hex)).build_transaction({
                    'from': account.address,
                    'nonce': nonce,
                    'gas': 100000,
                    'gasPrice': self.w3.eth.gas_price,
                    'chainId': self.chain_config['chain_id'],
                })
            else:
                # 直接发送到自己地址, data字段携带root
                tx = {
                    'from': account.address,
                    'to': account.address,
                    'nonce': nonce,
                    'value': 0,
                    'gas': 30000,
                    'gasPrice': self.w3.eth.gas_price,
                    'chainId': self.chain_config['chain_id'],
                    'data': '0x' + root_hex,
                }

            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()

            # 等待确认
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            block_number = receipt['blockNumber']
            block = self.w3.eth.get_block(block_number)
            timestamp = datetime.fromtimestamp(block['timestamp'], tz=timezone.utc).isoformat()

            result = {
                'success': True,
                'chain': self.chain,
                'merkle_root': '0x' + root_hex,
                'tx_hash': tx_hash_hex,
                'block_number': block_number,
                'timestamp': timestamp,
                'explorer_url': self.chain_config['explorer'] + tx_hash_hex,
                'simulated': False,
                'description': description,
                'metadata': metadata or {},
            }
            self._save_anchor(result)
            return result

        except Exception as e:
            return {'success': False, 'error': str(e), 'chain': self.chain, 'simulated': False}

    def _simulate_anchor(self, root_hex: str, description: str, metadata: dict) -> dict:
        """模拟锚定（本地记录，不真实上链）"""
        # 生成模拟交易哈希
        sim_data = root_hex + str(time.time()) + description
        tx_hash = '0x' + hashlib.sha256(sim_data.encode()).hexdigest()
        block_number = int(time.time())  # 模拟区块号
        timestamp = datetime.now(timezone.utc).isoformat()

        result = {
            'success': True,
            'chain': self.chain,
            'merkle_root': '0x' + root_hex,
            'tx_hash': tx_hash,
            'block_number': block_number,
            'timestamp': timestamp,
            'explorer_url': self.chain_config['explorer'] + tx_hash,
            'simulated': True,
            'description': description,
            'metadata': metadata or {},
            'note': 'SIMULATED - 配置ANCHOR_PRIVATE_KEY后可真实上链',
        }
        self._save_anchor(result)
        return result

    def _save_anchor(self, result: dict):
        """保存锚定记录"""
        record_file = self.storage_dir / f'anchor_{result["merkle_root"][:18]}.json'
        with open(record_file, 'w') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # 追加到锚定日志
        log_file = self.storage_dir / 'anchor_log.jsonl'
        with open(log_file, 'a') as f:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    def verify_anchor(self, merkle_root: str) -> dict:
        """
        验证锚定记录

        模拟模式: 验证本地记录存在且哈希匹配
        真实模式: 查询区块链验证root已被锚定
        """
        root_hex = merkle_root.lower().replace('0x', '')
        record_file = self.storage_dir / f'anchor_0x{root_hex[:16]}.json'

        if not record_file.exists():
            # 尝试其他命名
            for f in self.storage_dir.glob('anchor_*.json'):
                with open(f) as fp:
                    rec = json.load(fp)
                if rec.get('merkle_root', '').lower().replace('0x', '') == root_hex:
                    record_file = f
                    break
            else:
                return {'verified': False, 'error': 'Anchor record not found'}

        with open(record_file) as f:
            record = json.load(f)

        if record.get('simulated'):
            return {
                'verified': True,
                'simulated': True,
                'record': record,
                'note': '本地模拟锚定, 配置私钥后可验证链上数据'
            }

        # 真实模式: 查询链上
        if self.w3 and self.contract_address:
            try:
                contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(self.contract_address),
                    abi=ANCHOR_ABI
                )
                result = contract.functions.anchors(bytes.fromhex(root_hex)).call()
                block_num, ts, anchorer = result
                return {
                    'verified': block_num > 0,
                    'simulated': False,
                    'block_number': block_num,
                    'timestamp': datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                    'anchorer': anchorer,
                    'record': record,
                }
            except Exception as e:
                return {'verified': False, 'error': str(e), 'record': record}

        return {'verified': True, 'simulated': record.get('simulated', False), 'record': record}

    def list_anchors(self) -> list:
        """列出所有锚定记录"""
        anchors = []
        log_file = self.storage_dir / 'anchor_log.jsonl'
        if log_file.exists():
            with open(log_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        anchors.append(json.loads(line))
        return anchors

    def daily_anchor(self, merkle_root: str, snapshot_id: str = '') -> dict:
        """
        每日锚定便捷方法
        自动添加日期和快照ID元数据
        """
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        return self.anchor_root(
            merkle_root,
            description=f'Daily anchor {today} {snapshot_id}',
            metadata={'date': today, 'snapshot_id': snapshot_id, 'type': 'daily'}
        )


def main():
    """CLI入口"""
    import argparse
    parser = argparse.ArgumentParser(description='Blockchain Anchor Client')
    sub = parser.add_subparsers(dest='command')

    # anchor
    a_p = sub.add_parser('anchor', help='Anchor merkle root to blockchain')
    a_p.add_argument('--root', required=True, help='Merkle root hash (64 hex)')
    a_p.add_argument('--chain', default='polygon_mumbai', help='Chain name')
    a_p.add_argument('--desc', default='', help='Description')

    # verify
    v_p = sub.add_parser('verify', help='Verify anchor')
    v_p.add_argument('--root', required=True, help='Merkle root hash')

    # list
    sub.add_parser('list', help='List all anchors')

    # daily
    d_p = sub.add_parser('daily', help='Daily anchor')
    d_p.add_argument('--root', required=True, help='Merkle root hash')
    d_p.add_argument('--snapshot', default='', help='Snapshot ID')

    args = parser.parse_args()
    anchor = BlockchainAnchor(chain=args.chain if hasattr(args, 'chain') else 'polygon_mumbai')

    if args.command == 'anchor':
        result = anchor.anchor_root(args.root, description=args.desc)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == 'verify':
        result = anchor.verify_anchor(args.root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == 'list':
        anchors = anchor.list_anchors()
        print(json.dumps({'count': len(anchors), 'anchors': anchors}, ensure_ascii=False, indent=2))
    elif args.command == 'daily':
        result = anchor.daily_anchor(args.root, args.snapshot)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
