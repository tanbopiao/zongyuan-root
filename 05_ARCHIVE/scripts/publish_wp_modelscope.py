#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 白皮书 → 魔搭仓库发布器
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

沿用仓库既有发布约定（见 scripts/auto_publish_all.py）：
  白皮书类资产 → 模型仓 zongyuanroot/zongyuan-whitepaper → datalake/whitepapers/ → 分支 master

凭据：运行时从环境变量 MODELSCOPE_TOKEN 注入；不接受命令行传参（避免进入进程列表），
     不写入仓库、不写入 .git/config、不打印明文。

安全/幂等：
  - 目标文件内容与本地 sha256 相同（远端回读一致）→ skipped，不提交
  - --dry-run：不克隆、不修改，仅探测远端现状并打印计划
  - 推送后按 resolve URL 回读，比对 sha256，不一致即非零退出

用法：
  MODELSCOPE_TOKEN=ms-*** python3 publish_wp_modelscope.py \
      --src reports/xxx.html --slug my-whitepaper [--dest-subdir datalake/whitepapers] [--dry-run]
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone

REPO = 'zongyuanroot/zongyuan-whitepaper'
REPO_KIND = 'models'
DEST_SUBDIR = 'datalake/whitepapers'
BRANCH = 'master'
GIT_NAME, GIT_EMAIL = 'zongyuanroot', '195162494@qq.com'
DID, ANCHOR = 'DID-BR-000002', 'Ω₀⊂⊙∞⊂Ω'


def sha256_file(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def resolve_url(repo, subdir, slug):
    return f'https://www.modelscope.cn/{REPO_KIND}/{repo}/resolve/{BRANCH}/{subdir}/{slug}'


def api_list_dir(repo, subdir):
    """只读列目录（不需 token），返回 {Name: Sha256}"""
    url = (f'https://www.modelscope.cn/api/v1/{REPO_KIND}/{repo}/repo/files'
           f'?Revision={BRANCH}&Root={subdir}')
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            d = json.loads(r.read().decode('utf-8'))
        files = (d.get('Data') or {}).get('Files') or []
        return {f['Name']: f.get('Sha256', '') for f in files}
    except Exception as e:
        return {'__error__': str(e)}


def git(args, cwd, token):
    helper = "!f(){ echo username=oauth2; echo password=${MODELSCOPE_TOKEN}; };f"
    env = dict(os.environ, MODELSCOPE_TOKEN=token, GIT_TERMINAL_PROMPT='0')
    cmd = ['git', '-c', f'credential.helper={helper}', '-c', 'credential.interactive=false'] + args
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--slug', required=True, help='目标文件名（含 .html）')
    ap.add_argument('--dest-subdir', default=DEST_SUBDIR)
    ap.add_argument('--repo', default=REPO)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--receipt-dir', default='reports')
    a = ap.parse_args()

    if not os.path.isfile(a.src):
        print(f'源文件不存在: {a.src}', file=sys.stderr)
        return 2
    if '/' in a.slug or '..' in a.slug:
        print('--slug 非法', file=sys.stderr)
        return 2
    local_sha = sha256_file(a.src)
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    rurl = resolve_url(a.repo, a.dest_subdir, a.slug)

    print(f'仓库   : {REPO_KIND}/{a.repo}@{BRANCH}')
    print(f'目标   : {a.dest_subdir}/{a.slug}')
    print(f'本地   : {a.src}  sha256={local_sha[:16]}…')
    print(f'回读URL: {rurl}')

    listing = api_list_dir(a.repo, a.dest_subdir)
    if '__error__' in listing:
        print(f'远端目录探测失败: {listing["__error__"]}（继续，不影响推送）')
        remote_has = None
    else:
        remote_has = a.slug in listing
        print(f'远端已有同名文件: {remote_has}  目录条目数={len(listing)}')

    if a.dry_run:
        print('--- [dry-run] 计划 ---')
        print(f'  1. git clone --depth 1 {REPO_KIND}/{REPO}')
        print(f'  2. 写入 {DEST_SUBDIR}/{a.slug} + ATTESTATION')
        print(f'  3. commit + push origin {BRANCH}')
        print(f'  4. 回读 {rurl} 校验 sha256')
        print('--- dry-run 结束：未做任何修改 ---')
        return 0

    token = os.environ.get('MODELSCOPE_TOKEN', '').strip()
    if not token:
        print('缺少环境变量 MODELSCOPE_TOKEN（运行时注入，勿写入文件）', file=sys.stderr)
        return 2

    work = tempfile.mkdtemp(prefix='wp-ms-pub-')
    repo_dir = os.path.join(work, 'repo')
    try:
        rc, out, err = git(['clone', '--depth', '1', '--branch', BRANCH,
                            f'https://www.modelscope.cn/{REPO_KIND}/{REPO}.git', repo_dir], work, token)
        if rc != 0:
            print(f'clone 失败: {err}', file=sys.stderr)
            return 4

        dst_dir = os.path.join(repo_dir, DEST_SUBDIR)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, a.slug)

        if os.path.exists(dst) and sha256_file(dst) == local_sha:
            print('远端内容与本地一致，幂等跳过')
            return 0

        shutil.copy2(a.src, dst)

        attest = {'type': 'attestation', 'asset': a.slug, 'sha256': local_sha,
                  'did': DID, 'anchored': ANCHOR, 'date': ts[:10],
                  'source': 'publish_wp_modelscope.py'}
        att_path = os.path.join(dst_dir, f'ATTESTATION-{a.slug}-{ts[:8]}.json')
        open(att_path, 'w', encoding='utf-8').write(
            json.dumps(attest, ensure_ascii=False, indent=2))

        rc, out, err = git(['add', '-A'], repo_dir, token)
        rc, out, err = git(['-c', f'user.name={GIT_NAME}', '-c', f'user.email={GIT_EMAIL}',
                            'commit', '-q', '-m', f'publish: {a.slug} | {ANCHOR} | sha256:{local_sha[:16]}'],
                           repo_dir, token)
        if rc != 0 and 'nothing to commit' not in (out + err):
            print(f'commit 失败: {err}', file=sys.stderr)
            return 4

        rc, out, err = git(['push', 'origin', BRANCH], repo_dir, token)
        if rc != 0:
            print(f'push 失败: {err}', file=sys.stderr)
            return 4
        print('已推送 origin', BRANCH)

        # 落盘实测：回读比对 sha256
        try:
            with urllib.request.urlopen(rurl, timeout=30) as r:
                code, body = r.status, r.read()
        except Exception as e:
            print(f'回读失败: {e}', file=sys.stderr)
            return 5
        got = sha256_bytes(body)
        match = (got == local_sha)
        print(f'回读 HTTP {code} | 期望sha256={local_sha[:16]}… 实得={got[:16]}… match={match}')
        if code != 200 or not match:
            print('回读校验未通过', file=sys.stderr)
            return 5

        os.makedirs(a.receipt_dir, exist_ok=True)
        receipt = os.path.join(a.receipt_dir, f'WP-PUBLISH-MODELSCOPE-{ts}.json')
        json.dump({
            'receipt': 'WP-PUBLISH-MODELSCOPE', 'ts_utc': ts, 'repo': f'{REPO_KIND}/{REPO}',
            'branch': BRANCH, 'path': f'{DEST_SUBDIR}/{a.slug}', 'local_src': a.src,
            'local_sha256': local_sha, 'remote_sha256': got, 'resolve_url': rurl,
            'readback_http': code, 'match': match, 'attestation': os.path.basename(att_path),
            'status': 'published', 'provenance': 'measured',
        }, open(receipt, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('回执:', receipt)
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
