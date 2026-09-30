#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 全资产自动扩展展示引擎 V2.0（源头自动发现）
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
V2.0 升级: 不再要求人工放入发布目录——自动扫描源头资产目录,
        SHA256对比已发布清单(manifest), 新产生/变更的资产自动发布+展示。
用法: python3 auto_publish_all.py [--dry-run] [--force]
"""
import os, sys, json, hashlib, subprocess, time, glob

DRY = '--dry-run' in sys.argv
FORCE = '--force' in sys.argv
NOW = time.strftime('%Y%m%d-%H%M%S')
BASE = '/home/user/ZONGYUAN-ROOT'
MANIFEST = f'{BASE}/data/publish_manifest.json'
TMP = '/tmp/auto_publish'
GIT_TOKEN = open(os.path.expanduser('~/.modelscope/credentials/git_token')).read().strip()
GIT_NAME, GIT_EMAIL = 'zongyuanroot', '195162494@qq.com'
DID, ANCHOR = 'DID-BR-000002', 'Ω₀⊂⊙∞⊂Ω'

# 源头资产目录（任何新资产落入以下目录即自动发现，无需人工登记）
SOURCE_DIRS = [
    f'{BASE}/docs',                                  # 白皮书/紫皮书/文档/可视化网页
    os.path.expanduser('~/.zongyuan_root/PERMANENT_BASE/aios_deliverables/docs'),
]
WHITEPAPER_REPO = ('model', 'zongyuanroot/zongyuan-whitepaper', 'datalake/whitepapers')
DATALAKE_REPO = ('dataset', 'zongyuanroot/ZONGYUAN-SHARED-DATALAKE', 'zongyuan-root/web')

def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def sha(f):
    return hashlib.sha256(open(f, 'rb').read()).hexdigest()

def load_manifest():
    if os.path.exists(MANIFEST):
        try: return json.load(open(MANIFEST))
        except Exception: return {}
    return {}

def save_manifest(m):
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    json.dump(m, open(MANIFEST, 'w'), ensure_ascii=False, indent=2)

def discover():
    """扫描源头目录, 返回 {相对标识: (本地路径, sha256, 路由key)}"""
    found = {}
    for sd in SOURCE_DIRS:
        if not os.path.isdir(sd):
            continue
        for f in glob.glob(f'{sd}/**/*.md', recursive=True) + glob.glob(f'{sd}/**/*.html', recursive=True):
            low = f.lower()
            if any(x in f for x in ('/.git/', '/node_modules/', '/archive_', '/_archived', '/backup', '/locks/', '/data/')):
                continue
            # ===== 安全过滤层 V2（防止敏感文件误公开） =====
            up = f.upper()
            secret_hits = ['CREDENTIAL', 'CRED-', 'SECRET', 'PRIVATE', 'PASSWORD', 'SSH-KEY', 'API-TOKEN',
                           '.ENV', 'NODE-IDENTITY-CARD', 'AGENTS.MD', 'APPROVAL-EXEC', 'BOOTSTRAP',
                           'PERMISSION', 'WHITELIST', 'AUTH', 'KEY-STORE', 'VAULT', 'TOKEN-']
            if any(h in up for h in secret_hits):
                print(f'  [安全跳过] {f}')
                continue
            rel = f.replace(sd, '').lstrip('/')
            rkey = 'datalake' if '/showcase/' in f else ('whitepaper' if ('whitepaper' in low or '白皮' in f) else 'datalake')
            found[rel] = (f, sha(f), rkey)
    return found

def clone(kind, repo):
    url = f'https://oauth2:{GIT_TOKEN}@www.modelscope.cn/{kind}s/{repo}.git'
    d = f'{TMP}/{repo.split("/")[1]}'
    for attempt in range(3):
        if os.path.exists(f'{d}/.git'):
            return d
        sh(f'rm -rf {d} && git clone -q {url} {d}')
    raise RuntimeError(f'clone失败(3次): {repo}')

def publish(rel, local, h, rkey):
    kind, repo, sub = WHITEPAPER_REPO if rkey == 'whitepaper' else DATALAKE_REPO
    d = clone(kind, repo)
    dst_dir = f'{d}/{sub}'
    os.makedirs(dst_dir, exist_ok=True)
    dst = f'{dst_dir}/{rel}'
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    content = open(local, 'rb').read()
    if os.path.exists(dst) and open(dst, 'rb').read() == content:
        return None  # 幂等
    open(dst, 'wb').write(content)
    attest = {'type': 'attestation', 'asset': rel, 'date': NOW[:10], 'sha256': h,
              'did': DID, 'anchored': ANCHOR, 'source': 'auto-publish-engine-v2'}
    aname = f'ATTESTATION-{os.path.basename(rel)}-{NOW[:8]}.json'
    open(f'{dst_dir}/{aname}', 'w').write(json.dumps(attest, ensure_ascii=False, indent=2))
    out, err, rc = sh(f'cd {d} && git add -A && git -c user.name="{GIT_NAME}" -c user.email="{GIT_EMAIL}" commit -q -m "publish(auto): {rel}" && git push -q origin master')
    return (rel, repo, rc)

def update_index(entries):
    d = clone(*DATALAKE_REPO[0:2])
    base = f'{d}/{DATALAKE_REPO[2]}'
    html = f'''<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>火斗云智AIOS · 资产展示导航</title>
<style>body{{font-family:system-ui;max-width:960px;margin:40px auto;padding:0 20px;background:#0d0d0f;color:#e8d9a8}}
h1{{border-bottom:2px solid #c9a962;padding-bottom:10px}}a{{color:#c9a962}}table{{width:100%;border-collapse:collapse}}
td,th{{padding:8px;border-bottom:1px solid #333;text-align:left}}</style></head>
<body><h1>火斗云智AIOS · 资产自动展示导航</h1>
<p>自动生成: {NOW} | {DID} | {ANCHOR} | 共 {len(entries)} 项资产（自动发现自动发布）</p>
<table><tr><th>类别</th><th>资产</th><th>链接</th></tr>'''
    for rkey, f in sorted(entries):
        kind, repo, sub = WHITEPAPER_REPO if rkey == 'whitepaper' else DATALAKE_REPO
        url = f'https://www.modelscope.cn/{kind}s/{repo}/resolve/master/{sub}/{f}'
        html += f'<tr><td>{rkey}</td><td>{f}</td><td><a href="{url}">查看</a></td></tr>'
    html += '</table></body></html>'
    os.makedirs(base, exist_ok=True)
    open(f'{base}/INDEX.html', 'w').write(html)
    sh(f'cd {d} && git add -A && git -c user.name="{GIT_NAME}" -c user.email="{GIT_EMAIL}" commit -q -m "index: 导航自动更新({len(entries)}项)" && git push -q origin master')

def main():
    print(f'[引擎V2.0] {NOW} 模式={"DRY-RUN" if DRY else "REAL"}')
    manifest = load_manifest()
    found = discover()
    new = []
    for rel, (local, h, rkey) in found.items():
        if FORCE or manifest.get(rel) != h:
            new.append((rel, local, h, rkey))
    print(f'[发现] 源头资产 {len(found)} 项 | 新/变更 {len(new)} 项 | 已发布 {len(found)-len(new)} 项')
    if DRY:
        for rel, local, h, rkey in new[:20]:
            print(f'  将发布: [{rkey}] {rel}')
        return
    pushed = []
    for rel, local, h, rkey in new:
        r = publish(rel, local, h, rkey)
        if r:
            pushed.append(r)
            manifest[rel] = h
            print(f'[发布] {rel} -> {r[1]} (rc={r[2]})')
        else:
            manifest[rel] = h  # 内容相同也记录
    save_manifest(manifest)
    entries = []
    for rel, (local, h, rkey) in found.items():
        entries.append((rkey, rel))
    update_index(entries)
    print(f'[引擎V2.0] 完成: 新发布 {len(pushed)} 项 | 导航页更新 {len(entries)} 项资产')

if __name__ == '__main__':
    main()
