#!/usr/bin/env python3
"""
全自动固化算子 auto_persist.py v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
功能: 成果一键全自动固化到本地持久层
流程: 加固只读444 → (可选)账本留痕 → (可选)启动记忆更新 → git提交 → 推Gitee双副本
落地元规则: 全自动固化成果到本地持久层
用法:
  python3 auto_persist.py --files "path1,path2" --ledger "账本描述" [--memory-desc "启动记忆条目"] [--commit-msg "提交信息"] [--no-push]
"""
import os, sys, json, hashlib, time, subprocess, argparse

PRJ = "/home/user/Doubao/chats/38418284746129666"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
VERSION = "AUTO-PERSIST-V1.0"

def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())

def run(cmd, timeout=120):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or r.stderr).strip()

# ---------- 1 加固只读 ----------
def lock(files: list) -> list:
    locked = []
    for f in files:
        if os.path.exists(f):
            try: os.chmod(f, 0o444); locked.append(f)
            except Exception as e: locked.append(f"{f}(权限失败:{e})")
        else:
            locked.append(f"{f}(文件不存在)")
    return locked

# ---------- 2 账本留痕 ----------
def ledger(note: str) -> str:
    if not note: return "跳过"
    p = PRJ + "/HASH-LEDGER.csv"
    try: os.chmod(p, 0o666)
    except Exception: pass
    with open(p, "a") as f:
        f.write(f"{now()},AUTO-PERSIST-{time.strftime('%Y%m%d%H%M')},{note},{DID}\n")
    os.chmod(p, 0o444)
    return "已留痕"

# ---------- 3 启动记忆更新 ----------
def memory(desc: str) -> str:
    if not desc: return "跳过"
    p = PRJ + "/memory_index.json"
    try: os.chmod(p, 0o666)
    except Exception: pass
    d = json.load(open(p))
    d["asset_entries"].append({"id": f"AUTO-PERSIST-{int(time.time())}", "category": "固化成果",
                               "rule": desc, "added": now(), "locked": "RO-444"})
    d["index_meta"]["total_assets"] = len(d["asset_entries"])
    d["index_meta"]["merkle_root"] = hashlib.sha256(json.dumps(d, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16].upper()
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
    os.chmod(p, 0o444)
    return f"已更新(entries={d['index_meta']['total_assets']}, merkle={d['index_meta']['merkle_root']})"

# ---------- 4 git提交+推送 ----------
def git_push(files: list, commit_msg: str, do_push: bool) -> dict:
    os.chdir(PRJ)
    if not commit_msg:
        commit_msg = f"自动固化{now()}: {','.join(os.path.basename(f) for f in files)[:120]}, DID-BR-000002"
    rc, out = run(["git", "add", "-A"])
    rc2, out2 = run(["git", "commit", "-m", commit_msg])
    sha = ""
    if rc2 == 0:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    result = {"commit_msg": commit_msg, "commit_sha": sha}
    if do_push and sha:
        # 统一main与converge到HEAD并推送
        subprocess.run(["git", "update-ref", "refs/heads/converge-20260928", "HEAD"])
        rc3, out3 = run(["git", "push", "gitee", "refs/heads/main:refs/heads/main",
                         "refs/heads/converge-20260928:refs/heads/converge-20260928"], timeout=180)
        result["push"] = "OK" if rc3 == 0 else f"FAIL: {out3}"
    else:
        result["push"] = "跳过" if not do_push else "无提交"
    return result

def main():
    ap = argparse.ArgumentParser(description="全自动固化算子")
    ap.add_argument("--files", required=True, help="成果文件逗号分隔")
    ap.add_argument("--ledger", default="", help="账本描述(追加HASH-LEDGER)")
    ap.add_argument("--memory-desc", default="", help="启动记忆条目描述(可选)")
    ap.add_argument("--commit-msg", default="", help="git提交信息(可选)")
    ap.add_argument("--no-push", action="store_true", help="不推Gitee")
    a = ap.parse_args()
    files = [f.strip() for f in a.files.split(",") if f.strip()]

    locked = lock(files)
    led = ledger(a.ledger)
    mem = memory(a.memory_desc)
    g = git_push(files, a.commit_msg, not a.no_push)

    report = {"operator": VERSION, "did": DID, "time": now(), "locked_files": locked,
              "ledger": led, "memory": mem, "git_push": g}
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
