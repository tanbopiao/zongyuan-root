#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 全资产自动扩展展示引擎 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
功能: 扫描待发布目录 -> 分类路由 -> SHA256确权 -> Git直推魔搭多仓库 -> 更新展示导航页 -> 上报
用法: python3 auto_publish_all.py [--dry-run]
"""
import os, sys, json, hashlib, subprocess, time, glob

DRY = '--dry-run' in sys.argv
NOW = time.strftime('%Y%m%d-%H%M%S')
BASE = '/home/user/ZONGYUAN-ROOT'
PUBLISH_DIR = f'{BASE}/docs/publish'          # 待发布资产目录(放新md/html即自动发布)
TMP = '/tmp/auto_publish'
GIT_TOKEN = open(os.path.expanduser('~/.modelscope/credentials/git_token')).read().strip()
GIT_NAME, GIT_EMAIL = 'zongyuanroot', '195162494@qq.com'
DID, ANCHOR = 'DID-BR-000002', 'Ω₀⊂⊙∞⊂Ω'

REPOS = {
    'whitepaper': ('models', 'zongyuanroot/zongyuan-whitepaper', 'datalake/whitepapers'),
    'datalake':   ('datasets', 'zongyuanroot/ZONGYUAN-SHARED-DATALAKE', 'zongyuan-root/web'),
}
TYPE_HINT = {'白皮': 'whitepaper', '紫皮': 'articles', '可视化': 'datalake', 'index': 'datalake'}

def sh(cmd, **kw):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def sha(f):
    return hashlib.sha256(open(f, 'rb').read()).hexdigest()

def clone(repo_type, repo):
    url = f'https://oauth2:{GIT_TOKEN}@www.modelscope.cn/{repo_type}s/{repo}.git'
    out, err, rc = sh(f'git clone -q {url} {TMP}/{repo.split("/")[1]}')
    return rc == 0 or 'already exists' in err

def publish_files(files):
    """files: [(本地路径, 魔搭仓库key, 仓库内目标目录)]"""
    pushed = []
    for local, rkey, subdir in files:
        repo_type, repo, _ = REPOS[rkey]
        d = f'{TMP}/{repo.split("/")[1]}'
        if not os.path.exists(d):
            clone(repo_type, repo)
        dst_dir = f'{d}/{subdir}'
        os.makedirs(dst_dir, exist_ok=True)
        name = os.path.basename(local)
        dst = f'{dst_dir}/{name}'
        content = open(local, 'rb').read()
        if os.path.exists(dst) and open(dst, 'rb').read() == content:
            continue  # 幂等: 无变更跳过
        open(dst, 'wb').write(content)
        # 确权声明
        attest = {
            'type': 'attestation', 'asset': name, 'date': NOW[:10],
            'sha256': sha(local), 'did': DID, 'anchored': ANCHOR,
            'source': 'auto-publish-engine'
        }
        open(f'{dst_dir}/ATTESTATION-{name}-{NOW[:8]}.json', 'w').write(json.dumps(attest, ensure_ascii=False, indent=2))
        out, err, rc = sh(f'cd {d} && git add -A && git -c user.name="{GIT_NAME}" -c user.email="{GIT_EMAIL}" commit -q -m "publish: {name}" && git push -q origin master')
        pushed.append((name, repo, out or err or 'ok'))
    return pushed

def update_index():
    """更新展示导航页 INDEX.html 到数据湖 web/ 目录"""
    entries = []
    for rkey, (rtype, repo, sub) in REPOS.items():
        d = f'{TMP}/{repo.split("/")[1]}'
        if not os.path.exists(d):
            clone(rtype, repo)
        base = f'{d}/{sub}'
        if os.path.isdir(base):
            for f in sorted(os.listdir(base)):
                if f.endswith(('.md', '.html')) and not f.startswith('ATTESTATION'):
                    url = f'https://www.modelscope.cn/{rtype}s/{repo}/resolve/master/{sub}/{f}'
                    entries.append((rkey, f, url))
    html = f'''<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>火斗云智AIOS · 资产展示导航</title>
<style>body{{font-family:system-ui;max-width:960px;margin:40px auto;padding:0 20px;background:#0d0d0f;color:#e8d9a8}}
h1{{border-bottom:2px solid #c9a962;padding-bottom:10px}}a{{color:#c9a962;text-decoration:none}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:8px;border-bottom:1px solid #333;text-align:left}}</style></head>
<body><h1>火斗云智AIOS · 资产自动展示导航</h1>
<p>自动生成: {NOW} | {DID} | {ANCHOR} | 共 {len(entries)} 项资产</p>
<table><tr><th>类别</th><th>资产</th><th>链接</th></tr>'''
    for rkey, f, url in entries:
        html += f'<tr><td>{rkey}</td><td>{f}</td><td><a href="{url}">查看</a></td></tr>'
    html += '</table></body></html>'
    d = f'{TMP}/ZONGYUAN-SHARED-DATALAKE'
    os.makedirs(f'{d}/zongyuan-root/web', exist_ok=True)
    open(f'{d}/zongyuan-root/web/INDEX.html', 'w').write(html)
    out, err, rc = sh(f'cd {d} && git add -A && git -c user.name="{GIT_NAME}" -c user.email="{GIT_EMAIL}" commit -q -m "index: 展示导航页自动更新" && git push -q origin master')
    return rc

def main():
    print(f'[引擎] {NOW} 模式={"DRY-RUN" if DRY else "REAL"}')
    files = glob.glob(f'{PUBLISH_DIR}/*.md') + glob.glob(f'{PUBLISH_DIR}/*.html')
    if not files:
        print('[引擎] 待发布目录为空(放新文件到 docs/publish/ 即自动发布)')
        return
    jobs = []
    for f in files:
        low = os.path.basename(f).lower()
        rkey = 'whitepaper' if any(k in low for k in ('白皮', 'whitepaper')) else 'datalake'
        jobs.append((f, rkey, REPOS[rkey][2]))
    for j in jobs:
        if not DRY:
            publish_files([j])
        print(f'[引擎] 发布: {os.path.basename(j[0])} -> {j[1]}')
    if not DRY:
        update_index()
    print(f'[引擎] 完成. 待发布: {len(files)} 项 | 展示导航已更新' if not DRY else f'[引擎] DRY-RUN: 待发布 {len(files)} 项')

if __name__ == '__main__':
    main()
