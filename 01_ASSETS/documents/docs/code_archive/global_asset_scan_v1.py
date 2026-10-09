#!/usr/bin/env python3
"""GLOBAL-ASSET-SCAN-V1 全域资产扫描登记（只读）
用途：扫描本地白名单目录，计算文件指纹，与 M9 账本登记比对，
输出 已登记/孤儿候选(分级)/重复副本 三分类清单。
安全：只读；敏感文件(token/key/credential)仅标记存在，不进哈希报告。
"""
import os, json, hashlib, re, sys
from datetime import datetime
from collections import defaultdict

SCAN_DIRS = [
    "/home/user/Doubao/chats/38438306874426882",
    "/home/user/Doubao/chats/1128121028098",
    "/home/user/.zongyuan_root",
    "/home/user/.doubao/agent_mode/workspace",
]
# 排除：缓存/版本控制/临时/内部技能库
EXCLUDE_DIR_PAT = re.compile(r'(\.git|__pycache__|node_modules|\.skills$|/\.skills/|backup_lv8|github_backup|kernel_backup|\.meta_order_backup|\.zongyuan_root_backup|asset_scan$|comm_reports$|certs$|locks$|snapshots$|memory_gateway_store$|ledger_safe_backups$|^archive$)')
EXCLUDE_EXT = {'.pyc', '.log', '.tmp', '.swp', '.bak', '.jsonl'}
SENSITIVE_PAT = re.compile(r'(token|secret|key|password|passwd|credential|nvapi|base-token|\.db$|\.crt$|\.pem$)', re.I)
# 动态文件模式：这些是系统自动生成的状态/日志文件，不需要逐条登记
DYNAMIC_PAT = re.compile(r'(comm_exec_|evolution_log|error_cases|engine_state|kernel_active_pointer|kernel_write_credential|daily_integrity|_report_|session_|\.bak$)', re.I)
SIZE_LIMIT = 20*1024*1024  # 20MB 以上跳过哈希

LEDGER_PATH = "/home/user/.doubao/agent_mode/workspace/.user_skills/meta-order-archive/locked/M9_global_ledger.json"

def sha256_file(p):
    try:
        if os.path.getsize(p) > SIZE_LIMIT: return None
        h=hashlib.sha256()
        with open(p,'rb') as f:
            for c in iter(lambda:f.read(1<<20),b''): h.update(c)
        return h.hexdigest()
    except Exception: return None

def scan():
    files=[]
    for base in SCAN_DIRS:
        if not os.path.isdir(base): continue
        visited=set()
        for root,dirs,names in os.walk(base, followlinks=True):
            rp=os.path.realpath(root)
            if rp in visited: dirs[:]=[]; continue
            visited.add(rp)
            dirs[:]=[d for d in dirs if not EXCLUDE_DIR_PAT.search(d) and os.path.realpath(os.path.join(root,d)) not in visited]
            for n in names:
                p=os.path.join(root,n)
                if os.path.splitext(n)[1].lower() in EXCLUDE_EXT: continue
                try:
                    st=os.stat(p)
                    if not os.path.isfile(p): continue
                    rel=os.path.relpath(p,base)
                    level = 'A' if base in ('/home/user/.zongyuan_root',) else ('B' if 'Doubao/chats' in base else 'C')
                    files.append({'path':p,'base':base,'rel':rel,'size':st.st_size,
                        'mtime':datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M'),
                        'level':level,'sensitive':bool(SENSITIVE_PAT.search(n))})
                except Exception: pass
    return files

def main():
    led=json.load(open(LEDGER_PATH))
    assets=led['assets']
    # 账本登记的已知文件路径集合（content_file/credential_file/asset_name）
    known=set()
    for a in assets:
        for k in ('content_file','credential_file'):
            v=a.get(k) or ''
            if v: known.add(os.path.basename(v))
        known.add(str(a.get('asset_name','')))

    fl=scan()
    # 哈希（敏感文件跳过）
    for f in fl:
        f['sha256']=None if f['sensitive'] else sha256_file(f['path'])

    # 分类
    registered=[]; orphan=[]; dup=[]
    by_hash=defaultdict(list)
    for f in fl:
        b=f['rel'].split('/')[-1]
        if b in known or f['path'].startswith('/home/user/.doubao/agent_mode/workspace/.user_skills/meta-order-archive/locked/'):
            registered.append(f)
        else:
            orphan.append(f)
        if f['sha256']: by_hash[f['sha256']].append(f['rel'])
    for h,paths in by_hash.items():
        if len(paths)>1: dup.append({'sha256':h[:12],'count':len(paths),'paths':paths})

    # 孤儿分级：A体系候选（静态核心文件）/ B会话产物 / C备份缓存+动态文件
    gradeA=[f for f in orphan if f['level']=='A' and not f['sensitive'] and not DYNAMIC_PAT.search(f['path'])]
    gradeB=[f for f in orphan if f['level']=='B' and not f['sensitive']]
    gradeC=[f for f in orphan if f['level']=='C' or DYNAMIC_PAT.search(f['path'])]
    sens=[f for f in orphan if f['sensitive']]

    out={'version':'GLOBAL-ASSET-SCAN-V1','generated_at':datetime.now().strftime('%Y-%m-%d %H:%M'),
        'scanned':len(fl),'registered':len(registered),'orphan':len(orphan),'duplicate_groups':len(dup),
        'grade_a':len(gradeA),'grade_b':len(gradeB),'grade_c':len(gradeC),'sensitive_flagged':len(sens),
        'duplicates':dup[:20],
        'orphan_a':[{'path':f['path'],'size':f['size'],'mtime':f['mtime'],'sha256':(f['sha256'] or '')[:16]} for f in gradeA[:80]],
        'orphan_b':[{'path':f['path'],'size':f['size'],'mtime':f['mtime']} for f in gradeB[:80]],
        'orphan_c_count':len(gradeC),
        'sensitive_files':[f['path'] for f in sens]}
    return out

if __name__=='__main__':
    r=main()
    outpath=f'/home/user/Doubao/chats/38438306874426882/asset_scan/资产扫描报告_每日_{datetime.now().strftime("%Y%m%d")}.json'
    json.dump(r,open(outpath,'w'),ensure_ascii=False,indent=1)
    print('=== 全域资产扫描完成 ===')
    print(f'扫描文件: {r["scanned"]} | 已登记: {r["registered"]} | 孤儿候选: {r["orphan"]} | 重复组: {r["duplicate_groups"]}')
    print(f'孤儿分级: A体系候选 {r["grade_a"]} | B会话产物 {r["grade_b"]} | C备份缓存 {r["grade_c"]} | 敏感标记 {r["sensitive_flagged"]}')
    print('已输出:',outpath)
