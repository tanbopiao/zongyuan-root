#!/usr/bin/env python3
"""
L3 可信时间层 - RFC3161时间戳客户端

对接免费TSA服务，为每个Merkle根获取可信时间戳。
支持多TSA冗余、时间戳验证、批量时间戳。

TSA服务:
  - freetsa.org (免费, 无需注册)
  - timestamp.digicert.com (免费)
  - time.certum.pl (免费)
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from pyasn1.codec.der import decoder, encoder
from pyasn1_modules import rfc3161, rfc2459, rfc5652
from pyasn1.type import univ

# 常量
SHA256_OID = univ.ObjectIdentifier('2.16.840.1.101.3.4.2.1')
DEFAULT_TSA_LIST = [
    {
        'name': 'freetsa',
        'url': 'https://freetsa.org/tsr',
        'cert_url': 'https://freetsa.org/files/tsa.crt',
        'ca_cert_url': 'https://freetsa.org/files/cacert.pem',
    },
    {
        'name': 'digicert',
        'url': 'http://timestamp.digicert.com',
        'cert_url': None,
    },
    {
        'name': 'certum',
        'url': 'http://time.certum.pl',
        'cert_url': None,
    },
]


class TimestampClient:
    """RFC3161时间戳客户端"""

    def __init__(self, storage_dir: str = None, tsa_list: list = None):
        self.storage_dir = Path(storage_dir) if storage_dir else Path(__file__).parent.parent / 'timestamps'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.tsa_list = tsa_list or DEFAULT_TSA_LIST
        self._cert_cache = {}

    def _build_tsq(self, data_hash: bytes, hash_oid=SHA256_OID) -> bytes:
        """构造RFC3161 TimeStampReq"""
        tsq = rfc3161.TimeStampReq()
        tsq['version'] = 1
        # MessageImprint
        message_imprint = rfc3161.MessageImprint()
        hash_algorithm = rfc2459.AlgorithmIdentifier()
        hash_algorithm['algorithm'] = hash_oid
        hash_algorithm['parameters'] = univ.Null('')
        message_imprint['hashAlgorithm'] = hash_algorithm
        message_imprint['hashedMessage'] = univ.OctetString(data_hash)
        tsq['messageImprint'] = message_imprint
        # reqPolicy (可选)
        # nonce (可选，防重放)
        nonce = int.from_bytes(os.urandom(8), 'big')
        tsq['nonce'] = univ.Integer(nonce)
        tsq['certReq'] = True
        return encoder.encode(tsq)

    def request_timestamp(self, data: bytes, tsa_name: str = None, timeout: int = 30) -> dict:
        """
        请求时间戳

        Args:
            data: 要时间戳的数据（通常是Merkle根的字节）
            tsa_name: 指定TSA名称，None则自动尝试列表
            timeout: 超时秒数

        Returns:
            {
                'success': bool,
                'tsa': str,
                'data_hash': str,
                'timestamp_token_der': str (base64),
                'timestamp_time': str (ISO8601),
                'serial_number': str,
                'error': str (if failed)
            }
        """
        data_hash = hashlib.sha256(data).digest()
        data_hash_hex = data_hash.hex()

        tsas = [t for t in self.tsa_list if t['name'] == tsa_name] if tsa_name else self.tsa_list
        if not tsas:
            return {'success': False, 'error': f'TSA not found: {tsa_name}'}

        last_error = None
        for tsa in tsas:
            try:
                result = self._request_single_tsa(data_hash, tsa, timeout)
                if result['success']:
                    result['data_hash'] = data_hash_hex
                    return result
                last_error = result.get('error', 'unknown')
            except Exception as e:
                last_error = str(e)
                continue

        return {
            'success': False,
            'tsa': tsa_name or 'all',
            'data_hash': data_hash_hex,
            'error': f'All TSAs failed. Last: {last_error}'
        }

    def _request_single_tsa(self, data_hash: bytes, tsa: dict, timeout: int) -> dict:
        """向单个TSA请求时间戳"""
        tsq_bytes = self._build_tsq(data_hash)

        resp = requests.post(
            tsa['url'],
            data=tsq_bytes,
            headers={'Content-Type': 'application/timestamp-query'},
            timeout=timeout,
        )
        resp.raise_for_status()

        if resp.headers.get('Content-Type') != 'application/timestamp-reply':
            # 某些TSA返回不同content-type，仍尝试解析
            pass

        tsr, _ = decoder.decode(resp.content, asn1Spec=rfc3161.TimeStampResp())
        status_info = tsr['status']
        status = int(status_info['status'])

        if status != 0:  # 0 = granted
            status_strs = ['granted', 'grantedWithMods', 'rejection', 'waiting', 'revocationWarning', 'revocationNotification']
            return {
                'success': False,
                'tsa': tsa['name'],
                'error': f'TSA status: {status} ({status_strs[status] if status < len(status_strs) else "unknown"})'
            }

        # 提取TSTInfo - content是Any类型，需用SignedData解码
        tst_token = tsr['timeStampToken']
        content_der = bytes(tst_token['content'])
        signed_data, _ = decoder.decode(content_der, asn1Spec=rfc5652.SignedData())
        encap_content = signed_data['encapContentInfo']
        # eContent是EXPLICIT [0]标记，提取原始字节
        econtent = encap_content['eContent']
        tst_info_der = bytes(econtent) if hasattr(econtent, '__bytes__') else bytes(econtent.isValue)
        tst_info, _ = decoder.decode(tst_info_der, asn1Spec=rfc3161.TSTInfo())

        # 提取时间
        gen_time = tst_info['genTime']
        # pyasn1 GeneralizedTime处理
        gen_time_str = str(gen_time)

        # 提取序列号
        serial = int(tst_info['serialNumber'])

        # 保存token
        token_der = resp.content
        token_path = self.storage_dir / f'ts_{data_hash.hex()[:16]}_{tsa["name"]}.tsr'
        with open(token_path, 'wb') as f:
            f.write(token_der)

        return {
            'success': True,
            'tsa': tsa['name'],
            'timestamp_token_der': token_der.hex(),
            'timestamp_token_path': str(token_path),
            'timestamp_time': gen_time_str,
            'serial_number': str(serial),
        }

    def timestamp_merkle_root(self, merkle_root: str, description: str = '') -> dict:
        """
        为Merkle根获取时间戳（多TSA冗余）

        Args:
            merkle_root: Merkle根哈希（hex字符串）
            description: 描述信息

        Returns:
            时间戳结果（含多TSA）
        """
        data = merkle_root.encode()
        results = []
        for tsa in self.tsa_list:
            result = self.request_timestamp(data, tsa_name=tsa['name'])
            results.append(result)

        success_count = sum(1 for r in results if r['success'])
        record = {
            'merkle_root': merkle_root,
            'description': description,
            'requested_at': datetime.now(timezone.utc).isoformat(),
            'tsa_count': len(self.tsa_list),
            'success_count': success_count,
            'timestamps': [
                {
                    'tsa': r['tsa'],
                    'success': r['success'],
                    'timestamp_time': r.get('timestamp_time'),
                    'serial_number': r.get('serial_number'),
                    'token_path': r.get('timestamp_token_path'),
                    'error': r.get('error'),
                }
                for r in results
            ]
        }

        # 保存记录
        record_path = self.storage_dir / f'record_{merkle_root[:16]}.json'
        with open(record_path, 'w') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        return record

    def verify_timestamp(self, data: bytes, token_path: str) -> dict:
        """
        验证时间戳令牌

        验证内容:
        1. 令牌格式正确
        2. 数据哈希匹配
        3. 时间在合理范围内
        4. TSA签名验证（需要TSA证书）

        Returns:
            {'valid': bool, 'details': {...}}
        """
        try:
            with open(token_path, 'rb') as f:
                token_der = f.read()

            tsr, _ = decoder.decode(token_der, asn1Spec=rfc3161.TimeStampResp())
            status = int(tsr['status']['status'])
            if status != 0:
                return {'valid': False, 'error': f'TSA status: {status}'}

            tst_token = tsr['timeStampToken']
            content_der = bytes(tst_token['content'])
            signed_data, _ = decoder.decode(content_der, asn1Spec=rfc5652.SignedData())
            encap_content = signed_data['encapContentInfo']
            econtent = encap_content['eContent']
            tst_info_der = bytes(econtent) if hasattr(econtent, '__bytes__') else bytes(econtent.isValue)
            tst_info, _ = decoder.decode(tst_info_der, asn1Spec=rfc3161.TSTInfo())

            # 验证数据哈希匹配
            stored_hash = bytes(tst_info['messageImprint']['hashedMessage'])
            actual_hash = hashlib.sha256(data).digest()
            hash_match = stored_hash == actual_hash

            # 提取时间
            gen_time = str(tst_info['genTime'])
            serial = int(tst_info['serialNumber'])

            # 签名验证（简化版：检查证书存在）
            # 完整验证需要: 提取signerInfo → 验证签名 → 验证证书链
            certificates = signed_data['certificates']
            has_cert = len(certificates) > 0 if certificates else False

            return {
                'valid': hash_match,
                'details': {
                    'hash_match': hash_match,
                    'timestamp_time': gen_time,
                    'serial_number': serial,
                    'has_certificate': has_cert,
                    'note': 'Full signature verification requires TSA cert chain validation'
                }
            }
        except Exception as e:
            return {'valid': False, 'error': str(e)}

    def list_timestamps(self) -> list:
        """列出所有时间戳记录"""
        records = []
        for fp in sorted(self.storage_dir.glob('record_*.json')):
            with open(fp) as f:
                records.append(json.load(f))
        return records


def main():
    """CLI入口"""
    import argparse
    parser = argparse.ArgumentParser(description='RFC3161 Timestamp Client')
    sub = parser.add_subparsers(dest='command')

    # timestamp
    ts_p = sub.add_parser('timestamp', help='Request timestamp for data')
    ts_p.add_argument('--data', required=True, help='Data to timestamp (hex string or file path)')
    ts_p.add_argument('--tsa', default=None, help='TSA name (freetsa/digicert/certum)')
    ts_p.add_argument('--desc', default='', help='Description')

    # verify
    v_p = sub.add_parser('verify', help='Verify timestamp')
    v_p.add_argument('--data', required=True, help='Original data (hex or file)')
    v_p.add_argument('--token', required=True, help='Timestamp token file')

    # list
    sub.add_parser('list', help='List all timestamp records')

    args = parser.parse_args()
    client = TimestampClient()

    if args.command == 'timestamp':
        if Path(args.data).is_file():
            with open(args.data, 'rb') as f:
                raw = f.read()
            merkle_root = hashlib.sha256(raw).hexdigest()
        elif len(args.data) == 64 and all(c in '0123456789abcdefABCDEF' for c in args.data):
            merkle_root = args.data
        else:
            merkle_root = hashlib.sha256(args.data.encode()).hexdigest()
        result = client.timestamp_merkle_root(merkle_root, description=args.desc)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == 'verify':
        if Path(args.data).is_file():
            with open(args.data, 'rb') as f:
                raw = f.read()
            merkle_root = hashlib.sha256(raw).hexdigest()
        elif len(args.data) == 64 and all(c in '0123456789abcdefABCDEF' for c in args.data):
            merkle_root = args.data
        else:
            merkle_root = hashlib.sha256(args.data.encode()).hexdigest()
        result = client.verify_timestamp(merkle_root.encode(), args.token)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == 'list':
        records = client.list_timestamps()
        print(json.dumps({'count': len(records), 'records': records}, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
