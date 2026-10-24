#!/usr/bin/env python3
"""资产确权存证引擎 v1.0 —— 哈希指纹 + Merkle 根链 + 凭证 + 自校验（纯标准库）"""
import os, sys, json, csv, hashlib, time, argparse
from pathlib import Path
from typing import List, Dict

class AssetNotary:
    def __init__(self, target_dir: str, snap_id: str, did: str,
                 trace_symbol: str = '', exclude_patterns: List[str] = None,
                 parent_chain: List[str] = None):
        self.target_dir = Path(target_dir).resolve()
        self.snap_id = snap_id
        self.did = did
        self.trace_symbol = trace_symbol
        self.exclude_patterns = exclude_patterns or ['__pycache__', '.git', '.DS_Store', 'Thumbs.db']
        self.parent_chain = parent_chain or []
        self.assets: List[Dict] = []

    def _excluded(self, name: str) -> bool:
        return any(p in name for p in self.exclude_patterns)

    def scan(self) -> List[Dict]:
        """逐文件 SHA256 指纹"""
        self.assets = []
        for root, dirs, files in os.walk(self.target_dir):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
            for fname in sorted(files):
                if self._excluded(fname):
                    continue
                fpath = Path(root) / fname
                rel = str(fpath.relative_to(self.target_dir))
                h = hashlib.sha256(fpath.read_bytes()).hexdigest()
                self.assets.append({'file': rel, 'sha256': h, 'size': fpath.stat().st_size})
        self.assets.sort(key=lambda a: a['file'])
        return self.assets

    def merkle_root(self) -> str:
        """按文件名排序拼接全部哈希再取 SHA256 为 Merkle 根"""
        if not self.assets:
            self.scan()
        concat = ''.join(a['sha256'] for a in self.assets)
        return hashlib.sha256(concat.encode()).hexdigest()

    def build_manifest(self, merkle: str) -> Dict:
        return {
            'snap_id': self.snap_id,
            'did': self.did,
            'trace_symbol': self.trace_symbol,
            'parent_chain': self.parent_chain,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'asset_count': len(self.assets),
            'merkle_root': merkle,
            'target_dir': str(self.target_dir),
            'assets': self.assets,
        }

    @staticmethod
    def credential_md(manifest: Dict) -> str:
        ts = time.strftime('%Y-%m-%d %H:%M:%S %Z')
        lines = [f'# 资产确权凭证｜{manifest["snap_id"]}', '',
                 '## 元数据', '', '| 字段 | 值 |', '|------|-----|',
                 f'| 快照ID | {manifest["snap_id"]} |',
                 f'| 确权身份 | {manifest["did"]} |',
                 f'| 锁档时间 | {ts} |',
                 f'| 资产总数 | {manifest["asset_count"]} |',
                 f'| Merkle根 | `{manifest["merkle_root"]}` |', '']
        if manifest.get('parent_chain'):
            lines += [f'| 快照继承链 | {" → ".join(manifest["parent_chain"] + [manifest["snap_id"]])} |', '']
        lines += ['## 逐文件指纹', '', '| 文件 | 大小 | SHA-256 |', '|------|------|---------|']
        for a in manifest['assets']:
            lines.append(f'| {a["file"]} | {a["size"]}B | `{a["sha256"]}` |')
        lines += ['', '## 复算命令', '', '```bash',
                  f'cd {manifest["target_dir"]}',
                  'python3 -c "import hashlib,os;fs=sorted(f for f in os.listdir(\'.\') if os.path.isfile(f));c=\'\'.join(hashlib.sha256(open(f,\'rb\').read()).hexdigest() for f in fs);print(\'Merkle根:\',hashlib.sha256(c.encode()).hexdigest())"',
                  '```', '', '## 声明', '',
                  f'1. 本快照纳入 {manifest["asset_count"]} 个资产，绑定 {manifest["did"]} 确权身份。',
                  '2. Merkle 根由全部 SHA-256 按文件名排序拼接后再取 SHA-256 生成，单文件篡改即失配。',
                  '3. 锁档后禁止就地改写，后续迭代生成全新快照。', '']
        if manifest.get('trace_symbol'):
            lines.append(f'{manifest["trace_symbol"]}｜确权存证完成｜{manifest["did"]}')
        return '\n'.join(lines)

    def execute(self, output_dir: str = '', title: str = '') -> Dict:
        out = Path(output_dir or self.target_dir)
        out.mkdir(parents=True, exist_ok=True)
        self.scan()
        merkle = self.merkle_root()
        manifest = self.build_manifest(merkle)

        mp = out / f'MANIFEST-{self.snap_id}.json'
        mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        cp = out / f'LOCK-CREDENTIAL-{self.snap_id}.md'
        cp.write_text(self.credential_md(manifest), encoding='utf-8')

        # 自校验：重扫重算根比对
        saved = json.loads(mp.read_text(encoding='utf-8'))
        old = self.assets[:]
        self.assets = []
        self.scan()
        new_root = self.merkle_root()
        self.assets = old
        ok = new_root == saved['merkle_root']

        print(f'[Notary] 资产数={len(self.assets)} Merkle根={merkle[:16]}... 自校验={"PASS" if ok else "FAIL"}')
        print(f'[Notary] 凭证: {cp}')
        return {'snap_id': self.snap_id, 'merkle_root': merkle, 'asset_count': len(self.assets),
                'manifest_path': str(mp), 'credential_path': str(cp), 'self_verify': ok}

    def append_ledger(self, ledger_path: str):
        """账本追加（只追加不覆盖）"""
        lp = Path(ledger_path)
        new_rows = []
        for a in self.assets:
            new_rows.append({'file': a['file'], 'sha256': a['sha256'], 'size': a['size'],
                             'snap_id': self.snap_id, 'did': self.did,
                             'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z')})
        existed = lp.exists()
        with open(lp, 'a', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['file', 'sha256', 'size', 'snap_id', 'did', 'timestamp'])
            if not existed:
                w.writeheader()
            w.writerows(new_rows)
        print(f'[Notary] 账本追加 {len(new_rows)} 行: {lp}')

def main():
    ap = argparse.ArgumentParser(description='资产确权存证引擎')
    ap.add_argument('--dir', required=True)
    ap.add_argument('--snap-id', required=True)
    ap.add_argument('--did', required=True, help='确权身份（自有DID）')
    ap.add_argument('--trace', default='')
    ap.add_argument('--output', default='')
    ap.add_argument('--ledger', default='')
    ap.add_argument('--parent-chain', nargs='*', default=[])
    args = ap.parse_args()

    n = AssetNotary(args.dir, args.snap_id, args.did, args.trace, parent_chain=args.parent_chain)
    r = n.execute(output_dir=args.output)
    if args.ledger:
        n.append_ledger(args.ledger)
    sys.exit(0 if r['self_verify'] else 1)

if __name__ == '__main__':
    main()
