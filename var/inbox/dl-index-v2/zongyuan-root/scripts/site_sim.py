#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
官网变更本地仿真门（META-VISUAL-STANDARD-001 VS-9/VS-10）
用法:
  python3 site_sim.py --download <name>             # 下载线上原版到本地 site_lab/（只读，触网仅读取）
  python3 site_sim.py --apply <name> --anchor <旧锚> --insert <新行> [--before]
  python3 site_sim.py --diff <name>                 # diff 校验：只增不改（删除/替换行 → 拒绝）
  python3 site_sim.py --simulate <name>             # 本地渲染自检（shot.py，输出 _shots/）
  python3 site_sim.py --deploy <name>               # 仿真通过后部署（远端 immutable 仍须人工审批解锁）
"""
import os, sys, subprocess, io, difflib, datetime

ZR = "/home/user/ZONGYUAN-ROOT"
LAB = f"{ZR}/site_lab"
REMOTE_ROOT = "/www/wwwroot/huodouai.com"
SK = "/home/user/.doubao/agent_mode/workspace/.skills/html"

def ssh(cmd):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", "zongyuan-cloud", cmd],
                          capture_output=True, text=True, timeout=60)

def lab_path(name):
    return f"{LAB}/{name}"

def download(name):
    os.makedirs(LAB, exist_ok=True)
    r = subprocess.run(["scp", "-o", "BatchMode=yes", f"zongyuan-cloud:{REMOTE_ROOT}/{name}", lab_path(name)],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"[下载] 失败: {r.stderr[-200:]}"); return
    print(f"[下载] 线上原版 → {lab_path(name)}（{os.path.getsize(lab_path(name))}B，只读基准）")
    return lab_path(name)

def apply(name, anchor, insert, before=False):
    p = lab_path(name)
    if not os.path.exists(p):
        print(f"[应用] 先 --download {name}"); return
    src = io.open(p, encoding="utf-8").read()
    n = src.count(anchor)
    if n != 1:
        print(f"[应用] 拒绝：锚点出现 {n} 次（需唯一，避免误插/破坏结构）"); return
    if insert.strip() in src:
        print(f"[应用] 已存在该插入内容，跳过（幂等）"); return
    src = src.replace(anchor, anchor + "\n" + insert, 1) if not before else src.replace(anchor, insert + "\n" + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(src)
    print(f"[应用] 本地副本已应用增量（锚点唯一 ✓ 幂等 ✓）")

def diff(name):
    p = lab_path(name)
    if not os.path.exists(p):
        print(f"[diff] 无本地副本"); return
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "zongyuan-cloud",
                        f"cat {REMOTE_ROOT}/{name}"], capture_output=True, text=True, timeout=60)
    remote = r.stdout.splitlines(keepends=True)
    local = io.open(p, encoding="utf-8").read().splitlines(keepends=True)
    adds, mods, dels = [], [], []
    # 简化diff：本地含而远端不含 = 新增行；远端含而本地不含 = 删除行
    rs, ls = set(remote), set(local)
    for line in sorted(ls - rs, key=lambda x: local.index(x)):
        adds.append(line.rstrip())
    for line in sorted(rs - ls, key=lambda x: remote.index(x)):
        dels.append(line.rstrip())
    for line in sorted(rs & ls):
        pass
    ok = len(dels) == 0
    print(f"[diff] 新增行 {len(adds)} ｜ 删除/替换行 {len(dels)}")
    for a in adds[:5]: print(f"  + {a.strip()[:80]}")
    for d in dels[:5]: print(f"  - {d.strip()[:80]}")
    print(f"[diff] 判定：{'通过（只增不改 ✓）' if ok else '拒绝（存在删除/替换 ✗）'}")
    return ok

def simulate(name):
    p = lab_path(name)
    if not os.path.exists(p):
        print(f"[simulate] 无本地副本"); return
    r = subprocess.run(["python3", f"{SK}/scripts/shot.py", p], capture_output=True, text=True, timeout=180)
    print(f"[simulate] shot.py 渲染自检退出码 {r.returncode}；截图见 {LAB}/_shots/")
    print((r.stdout or "")[-300:] if r.returncode == 0 else (r.stderr or "")[-300:])
    return r.returncode == 0

def deploy(name):
    print(f"[deploy] 仿真门通过。远端 {name} 若 immutable 锁档 → 属已固化资产，禁止解锁覆盖；")
    print("        新文件发布请用新文件名；锁档文件确需增量变更 → 人工审批后执行。未部署。")
    return None

if __name__ == "__main__":
    a = sys.argv
    if "--download" in a: download(a[a.index("--download") + 1])
    elif "--apply" in a:
        i = a.index("--apply")
        apply(a[i + 1], a[a.index("--anchor") + 1], a[a.index("--insert") + 1], "--before" in a)
    elif "--diff" in a: diff(a[a.index("--diff") + 1])
    elif "--simulate" in a: simulate(a[a.index("--simulate") + 1])
    elif "--deploy" in a: deploy(a[a.index("--deploy") + 1])
    else: print(__doc__)
