#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提交前密钥扫描器 secret_scan.py

用途: pre-commit 钩子。扫描本次 staged 的文件内容, 拦截明文凭据入库。
凭据来源: 仓库外 600 权限凭据件 /root/.zr-credentials/*.env (键=值), 值不落库。
规则: 1) 已知凭据值精确匹配; 2) 高置信前缀/形态正则(github_pat_/ms-/ghp_/AKIA 等)。

用法:
  python3 scripts/secret_scan.py            # 扫描 staged 内容(pre-commit 默认)
  python3 scripts/secret_scan.py --all      # 扫描工作区所有 git 跟踪文件
  python3 scripts/secret_scan.py --path F   # 扫描指定文件
退出码: 0=通过, 1=发现疑似明文凭据(阻断提交)。
"""
import os, re, subprocess, sys, argparse

CRED_DIR = "/root/.zr-credentials"

# 高置信度密钥形态(不依赖已知值, 用于发现新泄露)
PATTERNS = [
    ("github_pat", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("gh_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("modelscope", re.compile(r"ms-[0-9a-f]{32}")),
    ("aws_key", re.compile(r"(AKIA|ASIA)[A-Z0-9]{16}")),
    ("private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("slack", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("openai", re.compile(r"sk-[A-Za-z0-9]{20,}")),
]

def load_known():
    """从仓库外凭据件加载已知密钥值(仅取 键名以 TOKEN/PAT/KEY/SECRET/PASSWORD 结尾 且 值长度>=16 的项;
    仓库名/用户名/HEAD 等非密钥字段不计入, 避免假阳性)。"""
    secret_key = re.compile(r"(TOKEN|PAT|_KEY|KEY|SECRET|PASSWORD|PASSWD)$", re.I)
    known = {}
    if not os.path.isdir(CRED_DIR):
        return known
    for fn in sorted(os.listdir(CRED_DIR)):
        if not fn.endswith(".env"):
            continue
        p = os.path.join(CRED_DIR, fn)
        for line in open(p, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if len(v) >= 16 and secret_key.search(k.strip()):
                known[v] = f"{fn}:{k}"
    return known

def mask(s):
    return s[:4] + "***" + s[-3:] if len(s) > 10 else "***"

def staged_files():
    r = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                       capture_output=True, text=True)
    return [f for f in r.stdout.splitlines() if f.strip()]

def tracked_files():
    r = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    return [f for f in r.stdout.splitlines() if f.strip()]

def read_text(path):
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        if b"\x00" in raw[:8192]:      # 二进制, 跳过(DB 已由 .gitignore 兜底)
            return None
        return raw.decode("utf-8", errors="ignore")
    except OSError:
        return None

def scan(paths, known):
    hits = []
    for p in paths:
        txt = read_text(p)
        if txt is None:
            continue
        for val, src in known.items():
            if val in txt:
                hits.append((p, f"已知凭据({src}) -> {mask(val)}"))
        for name, rx in PATTERNS:
            m = rx.search(txt)
            if m:
                hits.append((p, f"形态匹配[{name}] -> {mask(m.group(0))}"))
    return hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="扫描全部 git 跟踪文件")
    ap.add_argument("--path", action="append", default=[], help="扫描指定文件")
    a = ap.parse_args()
    known = load_known()
    if a.path:
        files = a.path
    elif a.all:
        files = tracked_files()
    else:
        files = staged_files()
    hits = scan(files, known)
    if not hits:
        print(f"[secret-scan] PASS  已扫描 {len(files)} 文件 / 已知凭据 {len(known)} 条")
        return 0
    print(f"[secret-scan] BLOCK  发现 {len(hits)} 处疑似明文凭据:")
    for p, d in hits:
        print(f"   ! {p}  {d}")
    print("   处置: 改为读取环境变量/凭据件引用, 勿提交明文。")
    return 1

if __name__ == "__main__":
    sys.exit(main())
