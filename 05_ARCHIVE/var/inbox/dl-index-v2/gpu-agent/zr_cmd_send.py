#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zr_cmd_send.py · 主控侧 git 双向控制面工具 V1.0
================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0
配套 zr_node_git.py (实例侧 git-poll worker):
  send  : 写 CMD-<id>.json 到魔搭 control/ + push (主控→实例)
  check : pull control/ 读 RESULT-<id>.json (实例→主控, 闭环确认)

用法:
  python3 zr_cmd_send.py send <task_id> "<shell cmd>"
  python3 zr_cmd_send.py check <task_id> [--wait 60]
"""
import json, os, subprocess, sys, time

DATA = "https://modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git"
CTRL_REL = "control"
TMP = "/tmp/zr_ctrl_main"

def sh(cmd, timeout=90):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or ""), (r.stderr or "")
    except Exception as e:
        return -1, "", str(e)

def remote_url():
    try:
        token = open(os.path.expanduser("~/.modelscope/credentials/git_token")).read().strip()
    except Exception:
        token = ""
    return DATA.replace("https://", f"https://zongyuanroot:{token}@") if token else DATA

def ensure_repo():
    if os.path.isdir(os.path.join(TMP, ".git")):
        return True
    sh(f"rm -rf {TMP}")
    rc, _, _ = sh(f"git clone --depth 1 --filter=blob:none --sparse '{remote_url()}' {TMP}", 120)
    if rc != 0:
        return False
    sh(f"cd {TMP} && git sparse-checkout set {CTRL_REL}", 60)
    return True

def push_cmd(task_id, cmd):
    if not ensure_repo():
        return {"ok": False, "error": "repo-init-fail"}
    sh(f"cd {TMP} && git remote set-url origin '{remote_url()}' && git pull --ff-only origin master", 60)
    ctrl = os.path.join(TMP, CTRL_REL)
    os.makedirs(ctrl, exist_ok=True)
    spec = {"task_id": task_id, "cmd": cmd, "ts": int(time.time())}
    fn = os.path.join(ctrl, f"CMD-{task_id}.json")
    with open(fn, "w") as f:
        json.dump(spec, f, ensure_ascii=False)
    rc, out, err = sh(f"cd {TMP} && git add -A && git -c user.email='zongyuanroot@modelscope.cn' -c user.name='zongyuanroot' commit -m 'CMD {task_id}' 2>&1 && git push origin master", 120)
    return {"ok": rc == 0, "task_id": task_id, "err": (err or out)[:200]}

def check_result(task_id, wait=60):
    """从云端读回结果: GET /api/truth 最新列表, 按 value.task_id 匹配 RESULT
       (结果由实例 POST 云端, key 自动生成, 用 value 标记匹配)"""
    deadline = time.time() + wait
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(urllib.request.Request("https://www.huodouai.com/api/truth"), timeout=15) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
        except Exception:
            time.sleep(4); continue
        if data.get("ok"):
            for rec in data.get("results", []):
                v = rec.get("value")
                if isinstance(v, dict) and v.get("task_id") == task_id and "code" in v:
                    v["_key"] = rec.get("key"); v["_ts"] = rec.get("ts")
                    return v
        time.sleep(4)
    return None

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(0)
    if args[0] == "send" and len(args) >= 3:
        r = push_cmd(args[1], args[2])
        print("下发:", json.dumps(r, ensure_ascii=False))
    elif args[0] == "check" and len(args) >= 2:
        w = 60
        if len(args) > 2 and args[2] == "--wait":
            w = int(args[3])
        r = check_result(args[1], w)
        print("结果:", json.dumps(r, ensure_ascii=False) if r else f"未收到 RESULT-{args[1]} (超时 {w}s)")
    else:
        print(__doc__)
