#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zr_node_git.py · 实例联通更优稳态 Worker V1.1 (mode=git-command + cloud-result)
============================================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0
职责: 魔搭实例(永久CPU) 作 ZONGYUAN-ROOT 计算节点，最优稳态闭环:
      命令下发走 git (主控push → 实例匿名pull, 无需凭证)
      结果/心跳走云端 (实例POST节点token → 主控GET读回, 写读均200已验证)
      实例【不需要】git push 凭证 —— 绕开所有凭证/单点死结
流程(每30s):
  1. git pull 魔搭 control/ (匿名读, fetch+checkout --force 抗冲突)
  2. 扫描 CMD-<id>.json (未处理) → 执行 → POST 云端 RESULT.<id>
     (本地 done 去重, CMD不删远端, 靠done幂等, 无需push)
  3. POST 云端 HEARTBEAT
幂等: task_id done记录(本地持久)防重启重放; 结果云端带task_id
退避: 网络/git错误 5→60s 封顶, 成功重置 (META-STEADY-001-C)
部署: /mnt/workspace/zr_node_git.py (无需git凭证)
用法: nohup python3 /mnt/workspace/zr_node_git.py >> /mnt/workspace/git_worker.log 2>&1 &
"""
import json, os, subprocess, time, urllib.request, urllib.error

NODE = os.environ.get("ZR_NODE", "ZR-NODE-MODEL-dsw-223619")
DID = "DID-BR-000002"
REPO_DIR = "/mnt/workspace/zr_ctrl"           # 命令槽工作区(稀疏clone control/, 匿名)
CTRL_REL = "control"
REPO_URL = "https://modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git"  # 匿名读
TOKEN_FILE = "/mnt/workspace/.zr/node_token.env"
REPORT_URL = "https://www.huodouai.com/api/report/truth"
DONE_FILE = "/mnt/workspace/.zr/git_worker_done.json"

def sh(cmd, timeout=90):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or ""), (r.stderr or "")
    except Exception as e:
        return -1, "", str(e)

def load_token():
    try:
        for line in open(TOKEN_FILE):
            if line.strip().startswith("ZR_NODE_TOKEN="):
                return line.strip().split("=", 1)[1].strip()
    except Exception:
        pass
    return os.environ.get("ZR_NODE_TOKEN", "")

def post_cloud(key, value):
    """结果/心跳上报云端 (节点token, 200已验证)"""
    token = load_token()
    if not token:
        return {"ok": False, "error": "no-token"}
    body = json.dumps({"truth_key": key, "truth_value": value,
                       "source_node": NODE, "truth_type": "rule", "confidence": 0.95},
                      ensure_ascii=False).encode()
    req = urllib.request.Request(REPORT_URL, data=body, headers={
        "X-Capture-Token": token, "X-DID": DID, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}

def load_done():
    try:
        return set(json.load(open(DONE_FILE)))
    except Exception:
        return set()

def save_done(d):
    try:
        json.dump(sorted(d), open(DONE_FILE, "w"))
    except Exception:
        pass

def ensure_repo():
    """初始化命令槽稀疏clone(匿名)"""
    if os.path.isdir(os.path.join(REPO_DIR, ".git")):
        return True
    sh(f"rm -rf {REPO_DIR}")
    rc, _, _ = sh(f"git clone --depth 1 --filter=blob:none --sparse {REPO_URL} {REPO_DIR}", 120)
    if rc != 0:
        return False
    sh(f"cd {REPO_DIR} && git sparse-checkout set {CTRL_REL}", 60)
    return True

def git_pull():
    """匿名pull命令槽 (fetch+checkout --force 抗冲突, 只恢复control目录)"""
    rc, _, _ = sh(f"cd {REPO_DIR} && git remote set-url origin {REPO_URL} && git fetch origin master 2>&1 && git checkout --force FETCH_HEAD -- {CTRL_REL}", 90)
    return rc == 0

def run_cmd(cmd, timeout=300):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "")[:1500]
        if r.stderr:
            out += f"\n[stderr] {r.stderr[:200]}"
        return r.returncode, out
    except subprocess.TimeoutExpired:
        return -2, "[TIMEOUT]"
    except Exception as e:
        return -1, f"[ERR] {e}"

done = load_done()
backoff = 5
print(f"[git] 启动 | node={NODE} | 命令槽 {REPO_DIR} (匿名, 无需git凭证)", flush=True)
if not ensure_repo():
    print("[git] 命令槽初始化失败(网络?), 退避重试", flush=True)

while True:
    try:
        if not git_pull():
            raise RuntimeError("git pull 失败(匿名读)")
        backoff = 5
        ctrl = os.path.join(REPO_DIR, CTRL_REL)
        if not os.path.isdir(ctrl):
            os.makedirs(ctrl, exist_ok=True)
        cmd_files = [f for f in os.listdir(ctrl) if f.startswith("CMD-") and f.endswith(".json")]
        for fn in sorted(cmd_files):
            task_id = fn[len("CMD-"):-len(".json")]
            if task_id in done:
                continue
            try:
                spec = json.load(open(os.path.join(ctrl, fn)))
            except Exception:
                continue
            cmd = spec.get("cmd")
            if not cmd:
                continue
            print(f"[git] 执行 {task_id}: {str(cmd)[:50]}", flush=True)
            code, out = run_cmd(cmd)
            # 结果走云端(无需git push)
            res = {"task_id": task_id, "node": NODE, "code": code, "out": out, "ts": int(time.time())}
            rr = post_cloud(f"RESULT.{task_id}", json.dumps(res, ensure_ascii=False))
            done.add(task_id); save_done(done)
            print(f"[git] 结果 {task_id} code={code} 云端={'OK' if rr.get('ok') else rr.get('error','?')}", flush=True)
        # 心跳走云端
        post_cloud("HEARTBEAT", json.dumps({"node": NODE, "event": "heartbeat", "ts": int(time.time())}, ensure_ascii=False))
    except RuntimeError as e:
        print(f"[git] {e} | 退避{backoff}s", flush=True)
        time.sleep(backoff); backoff = min(backoff * 2, 60)
    except urllib.error.HTTPError as e:
        print(f"[git] HTTP {e.code} | 退避{backoff}s", flush=True)
        time.sleep(backoff); backoff = min(backoff * 2, 60)
    except Exception as e:
        print(f"[git] {str(e)[:60]} | 退避{backoff}s", flush=True)
        time.sleep(backoff); backoff = min(backoff * 2, 60)
    time.sleep(30)
