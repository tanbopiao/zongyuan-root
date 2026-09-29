#!/usr/bin/env python3
"""
L1 数据层 - 内容寻址存储 (Content-Addressable Storage)

每个数据对象的标识符 = SHA256(内容)，而非文件名。
相同内容产生相同ID，修改内容 = 创建新对象，旧对象永久保留。
支持不可变DAG（对象之间通过哈希引用关联）。
"""

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any


class CASStore:
    """内容寻址存储"""

    def __init__(self, store_dir: str = None):
        self.store_dir = Path(store_dir) if store_dir else Path(__file__).parent.parent / 'cas_store'
        self.objects_dir = self.store_dir / 'objects'
        self.refs_dir = self.store_dir / 'refs'
        self.index_file = self.store_dir / 'index.json'
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        self.refs_dir.mkdir(parents=True, exist_ok=True)
        self._init_index()

    def _init_index(self):
        if not self.index_file.exists():
            with open(self.index_file, 'w') as f:
                json.dump({'objects': {}, 'refs': {}, 'created_at': datetime.now(timezone.utc).isoformat()}, f, ensure_ascii=False, indent=2)

    def _load_index(self) -> dict:
        with open(self.index_file) as f:
            return json.load(f)

    def _save_index(self, index: dict):
        with open(self.index_file, 'w') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _object_path(self, content_hash: str) -> Path:
        # 分片存储: ab/cdef... (前2位为目录)
        return self.objects_dir / content_hash[:2] / content_hash[2:]

    def put(self, data: bytes, metadata: dict = None) -> str:
        """
        存储数据，返回内容哈希(CID)

        Args:
            data: 原始数据字节
            metadata: 附加元数据

        Returns:
            content_hash (SHA256 hex)
        """
        content_hash = hashlib.sha256(data).hexdigest()
        obj_path = self._object_path(content_hash)

        if not obj_path.exists():
            obj_path.parent.mkdir(parents=True, exist_ok=True)
            with open(obj_path, 'wb') as f:
                f.write(data)

        # 更新索引
        index = self._load_index()
        if content_hash not in index['objects']:
            index['objects'][content_hash] = {
                'size': len(data),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'metadata': metadata or {},
                'ref_count': 0,
            }
            self._save_index(index)

        return content_hash

    def put_json(self, obj: Any, metadata: dict = None) -> str:
        """存储JSON对象"""
        data = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()
        return self.put(data, metadata)

    def get(self, content_hash: str) -> Optional[bytes]:
        """按内容哈希获取数据"""
        obj_path = self._object_path(content_hash)
        if obj_path.exists():
            with open(obj_path, 'rb') as f:
                return f.read()
        return None

    def get_json(self, content_hash: str) -> Optional[Any]:
        """按内容哈希获取JSON对象"""
        data = self.get(content_hash)
        if data:
            return json.loads(data)
        return None

    def exists(self, content_hash: str) -> bool:
        """检查对象是否存在"""
        return self._object_path(content_hash).exists()

    def delete(self, content_hash: str) -> bool:
        """
        逻辑删除（不物理删除，只标记）
        CAS中物理删除是不允许的，这里只减少引用计数
        """
        index = self._load_index()
        if content_hash in index['objects']:
            index['objects'][content_hash]['ref_count'] = max(0, index['objects'][content_hash].get('ref_count', 0) - 1)
            index['objects'][content_hash]['deleted'] = True
            index['objects'][content_hash]['deleted_at'] = datetime.now(timezone.utc).isoformat()
            self._save_index(index)
            return True
        return False

    def set_ref(self, name: str, content_hash: str):
        """设置命名引用（如HEAD、main、snapshot-20260831）"""
        ref_path = self.refs_dir / name
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ref_path, 'w') as f:
            f.write(content_hash)

        index = self._load_index()
        index['refs'][name] = content_hash
        # 增加引用计数
        if content_hash in index['objects']:
            index['objects'][content_hash]['ref_count'] = index['objects'][content_hash].get('ref_count', 0) + 1
        self._save_index(index)

    def get_ref(self, name: str) -> Optional[str]:
        """获取命名引用"""
        ref_path = self.refs_dir / name
        if ref_path.exists():
            with open(ref_path) as f:
                return f.read().strip()
        return None

    def list_refs(self) -> Dict[str, str]:
        """列出所有引用"""
        refs = {}
        for fp in self.refs_dir.rglob('*'):
            if fp.is_file():
                name = str(fp.relative_to(self.refs_dir))
                with open(fp) as f:
                    refs[name] = f.read().strip()
        return refs

    def list_objects(self, limit: int = 100) -> List[dict]:
        """列出对象"""
        index = self._load_index()
        objects = []
        for h, info in list(index['objects'].items())[:limit]:
            objects.append({'hash': h, **info})
        return objects

    def verify_integrity(self) -> dict:
        """
        验证存储完整性
        1. 索引中的对象都存在于磁盘
        2. 磁盘中的对象哈希正确
        3. 引用指向的对象存在
        """
        index = self._load_index()
        errors = []
        verified = 0

        # 验证索引中的对象
        for content_hash, info in index['objects'].items():
            obj_path = self._object_path(content_hash)
            if not obj_path.exists():
                errors.append({'hash': content_hash, 'error': 'missing on disk'})
                continue
            with open(obj_path, 'rb') as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            if actual_hash != content_hash:
                errors.append({'hash': content_hash, 'error': f'hash mismatch: {actual_hash}'})
            else:
                verified += 1

        # 验证引用
        for name, ref_hash in index['refs'].items():
            if not self.exists(ref_hash):
                errors.append({'ref': name, 'error': f'ref points to missing object: {ref_hash}'})

        return {
            'total_objects': len(index['objects']),
            'verified': verified,
            'errors': errors,
            'valid': len(errors) == 0,
            'refs_count': len(index['refs']),
        }

    def stats(self) -> dict:
        """存储统计"""
        index = self._load_index()
        total_size = sum(info.get('size', 0) for info in index['objects'].values())
        return {
            'total_objects': len(index['objects']),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'refs_count': len(index['refs']),
            'store_dir': str(self.store_dir),
        }


def main():
    """CLI入口"""
    import argparse
    parser = argparse.ArgumentParser(description='Content-Addressable Storage')
    sub = parser.add_subparsers(dest='command')

    # put
    p_p = sub.add_parser('put', help='Store data')
    p_p.add_argument('--file', required=True, help='File to store')
    p_p.add_argument('--meta', default='{}', help='Metadata JSON')

    # get
    g_p = sub.add_parser('get', help='Get data by hash')
    g_p.add_argument('--hash', required=True, help='Content hash')
    g_p.add_argument('--output', help='Output file')

    # verify
    sub.add_parser('verify', help='Verify store integrity')

    # stats
    sub.add_parser('stats', help='Store statistics')

    # refs
    sub.add_parser('refs', help='List refs')

    args = parser.parse_args()
    store = CASStore()

    if args.command == 'put':
        with open(args.file, 'rb') as f:
            data = f.read()
        meta = json.loads(args.meta) if args.meta else {}
        h = store.put(data, meta)
        print(json.dumps({'content_hash': h, 'size': len(data)}, ensure_ascii=False, indent=2))
    elif args.command == 'get':
        data = store.get(args.hash)
        if data:
            if args.output:
                with open(args.output, 'wb') as f:
                    f.write(data)
                print(f'Saved to {args.output}')
            else:
                print(data.decode(errors='replace'))
        else:
            print('Not found')
    elif args.command == 'verify':
        print(json.dumps(store.verify_integrity(), ensure_ascii=False, indent=2))
    elif args.command == 'stats':
        print(json.dumps(store.stats(), ensure_ascii=False, indent=2))
    elif args.command == 'refs':
        print(json.dumps(store.list_refs(), ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
