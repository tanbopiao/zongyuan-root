import sys; sys.path.insert(0, "/opt/ZONGYUAN-ROOT"); from core.truth_loader import truth_loader
#!/usr/bin/env python3
"""
TruthAnchor 智能合约部署与交互脚本

功能:
  - 部署合约到指定链
  - 锚定Merkle根
  - 查询锚定记录
  - 验证锚定

依赖: pip install web3
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from web3 import Web3
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False


# 合约ABI (从TruthAnchor.sol编译)
CONTRACT_ABI = [
    {"inputs": [], "stateMutability": "nonpayable", "type": "constructor"},
    {"anonymous": False, "inputs": [
        {"indexed": True, "internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
        {"indexed": True, "internalType": "address", "name": "anchorer", "type": "address"},
        {"indexed": False, "internalType": "uint256", "name": "blockNumber", "type": "uint256"},
        {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        {"indexed": False, "internalType": "uint256", "name": "anchorCount", "type": "uint256"}
    ], "name": "Anchored", "type": "event"},
    {"inputs": [{"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"}],
     "name": "anchor", "outputs": [], "stateMutability": "payable", "type": "function"},
    {"inputs": [{"internalType": "bytes32[]", "name": "merkleRoots", "type": "bytes32[]"}],
     "name": "anchorBatch", "outputs": [], "stateMutability": "payable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
     "name": "anchors", "outputs": [
        {"internalType": "uint256", "name": "blockNumber", "type": "uint256"},
        {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        {"internalType": "address", "name": "anchorer", "type": "address"},
        {"internalType": "uint256", "name": "anchorCount", "type": "uint256"}
     ], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"}],
     "name": "getAnchor", "outputs": [
        {"internalType": "uint256", "name": "blockNumber", "type": "uint256"},
        {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        {"internalType": "address", "name": "anchorer", "type": "address"},
        {"internalType": "uint256", "name": "anchorCount", "type": "uint256"}
     ], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
                {"internalType": "uint256", "name": "index", "type": "uint256"}],
     "name": "getAnchorHistoryEntry", "outputs": [
        {"internalType": "uint256", "name": "blockNumber", "type": "uint256"},
        {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        {"internalType": "address", "name": "anchorer", "type": "address"},
        {"internalType": "uint256", "name": "anchorCount", "type": "uint256"}
     ], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"}],
     "name": "getAnchorHistoryLength", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "owner", "outputs": [{"internalType": "address", "name": "", "type": "address"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "anchorFee", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
                {"internalType": "uint256", "name": "blockNumber", "type": "uint256"}],
     "name": "verify", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "newFee", "type": "uint256"}],
     "name": "setAnchorFee", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "newOwner", "type": "address"}],
     "name": "transferOwnership", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "withdraw", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
]

# 合约Bytecode (需要用solc编译后填入)
# 编译命令: solc --optimize --bin TruthAnchor.sol
CONTRACT_BYTECODE = "0x"  # 占位，部署前需编译填入


CHAINS = {
    'polygon_mumbai': {
        'rpc': 'https://rpc-mumbai.maticvigil.com',
        'chain_id': 80001,
        'explorer': 'https://mumbai.polygonscan.com/',
        'currency': 'MATIC',
    },
    'polygon_mainnet': {
        'rpc': 'https://polygon-rpc.com',
        'chain_id': 137,
        'explorer': 'https://polygonscan.com/',
        'currency': 'MATIC',
    },
}


class AnchorContract:
    """TruthAnchor合约交互"""

    def __init__(self, chain: str = 'polygon_mumbai', private_key: str = None,
                 contract_address: str = None):
        if not WEB3_AVAILABLE:
            raise ImportError("web3 not installed. Run: pip install web3")

        self.chain = chain
        self.chain_config = CHAINS.get(chain, CHAINS['polygon_mumbai'])
        self.w3 = Web3(Web3.HTTPProvider(self.chain_config['rpc']))
        self.private_key = private_key or os.environ.get('ANCHOR_PRIVATE_KEY', '')
        self.account = self.w3.eth.account.from_key(self.private_key) if self.private_key else None
        self.contract_address = contract_address or os.environ.get('ANCHOR_CONTRACT_ADDRESS', '')
        self.contract = None
        if self.contract_address:
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.contract_address),
                abi=CONTRACT_ABI
            )

    def deploy(self) -> dict:
        """部署合约"""
        if not self.account:
            return {'success': False, 'error': 'private key required'}
        if CONTRACT_BYTECODE == '0x':
            return {'success': False, 'error': 'bytecode not set. Compile TruthAnchor.sol first.'}

        contract = self.w3.eth.contract(abi=CONTRACT_ABI, bytecode=CONTRACT_BYTECODE)
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = contract.constructor().build_transaction({
            'from': self.account.address,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': self.chain_config['chain_id'],
        })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            'success': True,
            'contract_address': receipt['contractAddress'],
            'tx_hash': tx_hash.hex(),
            'block_number': receipt['blockNumber'],
            'explorer_url': self.chain_config['explorer'] + 'address/' + receipt['contractAddress'],
        }

    def anchor(self, merkle_root: str) -> dict:
        """锚定Merkle根"""
        if not self.contract or not self.account:
            return {'success': False, 'error': 'contract not initialized'}

        root_bytes = bytes.fromhex(merkle_root.replace('0x', ''))
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = self.contract.functions.anchor(root_bytes).build_transaction({
            'from': self.account.address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': self.chain_config['chain_id'],
        })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            'success': receipt['status'] == 1,
            'tx_hash': tx_hash.hex(),
            'block_number': receipt['blockNumber'],
            'explorer_url': self.chain_config['explorer'] + 'tx/' + tx_hash.hex(),
        }

    def get_anchor(self, merkle_root: str) -> dict:
        """查询锚定记录"""
        if not self.contract:
            return {'success': False, 'error': 'contract not initialized'}

        root_bytes = bytes.fromhex(merkle_root.replace('0x', ''))
        result = self.contract.functions.getAnchor(root_bytes).call()
        return {
            'block_number': result[0],
            'timestamp': result[1],
            'anchorer': result[2],
            'anchor_count': result[3],
            'exists': result[3] > 0,
        }

    def verify(self, merkle_root: str, block_number: int = None) -> dict:
        """验证锚定"""
        if not self.contract:
            return {'success': False, 'error': 'contract not initialized'}

        root_bytes = bytes.fromhex(merkle_root.replace('0x', ''))
        if block_number is None:
            block_number = self.w3.eth.block_number
        result = self.contract.functions.verify(root_bytes, block_number).call()
        return {'verified': result, 'block_number': block_number}


def main():
    import argparse
    parser = argparse.ArgumentParser(description='TruthAnchor Contract Deployer')
    sub = parser.add_subparsers(dest='command')

    # deploy
    d_p = sub.add_parser('deploy', help='Deploy contract')
    d_p.add_argument('--chain', default='polygon_mumbai', help='Chain name')
    d_p.add_argument('--key', help='Private key')

    # anchor
    a_p = sub.add_parser('anchor', help='Anchor merkle root')
    a_p.add_argument('--root', required=True, help='Merkle root hash')
    a_p.add_argument('--contract', required=True, help='Contract address')
    a_p.add_argument('--chain', default='polygon_mumbai')
    a_p.add_argument('--key', help='Private key')

    # query
    q_p = sub.add_parser('query', help='Query anchor')
    q_p.add_argument('--root', required=True, help='Merkle root hash')
    q_p.add_argument('--contract', required=True, help='Contract address')
    q_p.add_argument('--chain', default='polygon_mumbai')

    args = parser.parse_args()
    import json as _json

    if args.command == 'deploy':
        c = AnchorContract(chain=args.chain, private_key=args.key)
        print(_json.dumps(c.deploy(), indent=2))
    elif args.command == 'anchor':
        c = AnchorContract(chain=args.chain, private_key=args.key, contract_address=args.contract)
        print(_json.dumps(c.anchor(args.root), indent=2))
    elif args.command == 'query':
        c = AnchorContract(chain=args.chain, contract_address=args.contract)
        print(_json.dumps(c.get_anchor(args.root), indent=2))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
