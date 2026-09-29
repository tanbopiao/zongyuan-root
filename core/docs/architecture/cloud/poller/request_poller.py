#!/usr/bin/env python3
"""
云内核中枢请求轮询服务
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω
功能：定时git pull → 读取cloud/requests/ → 执行任务 → 写入响应 → push回远程
"""
import json
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime

# 配置
REPO_DIR = "/data/zongyuan-root"  # 云服务器上的项目路径
POLL_INTERVAL = 60  # 轮询间隔（秒）
REQUESTS_DIR = Path(REPO_DIR) / "cloud" / "requests"
RESPONSES_DIR = Path(REPO_DIR) / "cloud" / "responses"
AUDIT_LOG = Path(REPO_DIR) / "cloud" / "poller_audit.log"

def log(msg):
    ts = datetime.now().isoformat()
    line = f"[{ts}] {msg}"
    print(line)
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_cmd(cmd, cwd=None, timeout=60):
    """执行shell命令"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd or REPO_DIR,
            capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except Exception as e:
        return False, str(e)

def git_pull():
    """拉取最新代码"""
    ok, out = run_cmd("git pull origin main", timeout=30)
    if not ok:
        ok, out = run_cmd("git pull gitee main", timeout=30)
    return ok

def git_push():
    """推送结果回远程"""
    run_cmd("git add -A", timeout=10)
    run_cmd(f"git commit -m 'AUTO: poller response {datetime.now().isoformat()}'", timeout=10)
    run_cmd("git push origin main", timeout=30)
    run_cmd("git push gitee main", timeout=30)

def get_web_root():
    """查找Web根目录"""
    candidates = [
        "/www/wwwroot/www.huodouai.com",
        "/www/wwwroot/huodouai.com",
        "/var/www/html",
        "/usr/share/nginx/html"
    ]
    for path in candidates:
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "index.html")):
            return path
    # 宝塔面板自动查找
    ok, out = run_cmd("find /www/wwwroot -name 'index.html' -maxdepth 2 2>/dev/null | head -1 | xargs dirname")
    if ok and out and "No such" not in out:
        return out
    return None

def execute_request(request_file):
    """执行单个请求"""
    try:
        with open(request_file, "r", encoding="utf-8") as f:
            req = json.load(f)
    except Exception as e:
        log(f"❌ 读取请求失败: {request_file.name} - {e}")
        return None

    req_id = req.get("request_id", "UNKNOWN")
    action = req.get("action", "")
    params = req.get("params", {})

    log(f"📥 收到请求: {req_id} | action={action}")

    result = {
        "request_id": req_id,
        "executed_at": datetime.now().isoformat(),
        "status": "PENDING",
        "output": ""
    }

    # 执行部署任务
    if action in ["DEPLOY_WEB_PAGE", "DEPLOY_STATIC_PAGE"]:
        web_root = get_web_root()
        if not web_root:
            result["status"] = "FAILED"
            result["output"] = "未找到Web根目录"
        else:
            log(f"  Web根目录: {web_root}")

            # 创建目录
            run_cmd(f"mkdir -p {web_root}/static/diff", timeout=10)

            # 复制文件
            src = f"{REPO_DIR}/showcase-page/differential_capabilities.html"
            dst = f"{web_root}/static/diff/index.html"
            ok, out = run_cmd(f"cp {src} {dst}", timeout=10)

            if ok:
                # 设置权限
                run_cmd(f"chmod 644 {dst}", timeout=5)
                # 验证
                ok_verify, out_verify = run_cmd(
                    "curl -s -o /dev/null -w '%{http_code}' http://localhost/static/diff/",
                    timeout=5
                )
                result["status"] = "SUCCESS"
                result["output"] = f"文件已部署到 {dst} | 本地验证HTTP {out_verify}"
                log(f"  ✅ 部署完成: {dst}")
            else:
                result["status"] = "FAILED"
                result["output"] = f"复制文件失败: {out}"
                log(f"  ❌ 复制失败: {out}")

    # 写入响应文件
    response_file = RESPONSES_DIR / f"RES_{req_id}.json"
    with open(response_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log(f"  📤 响应已写入: {response_file.name}")
    return result

def poll_once():
    """执行一次轮询"""
    log("=" * 50)
    log("🔄 开始轮询...")

    # 1. git pull
    ok = git_pull()
    if not ok:
        log("⚠️ git pull 失败，使用本地缓存")

    # 2. 读取请求文件
    if not REQUESTS_DIR.exists():
        log("⚠️ requests目录不存在")
        return

    request_files = sorted(REQUESTS_DIR.glob("REQ_*.json"))
    if not request_files:
        log("📭 无新请求")
        return

    log(f"📋 发现 {len(request_files)} 个请求文件")

    # 3. 逐个执行
    for req_file in request_files:
        # 检查是否已有响应
        req_id = req_file.stem.replace("REQ_", "")
        response_file = RESPONSES_DIR / f"RES_{req_id}.json"
        if response_file.exists():
            log(f"  ⏭️ 已处理: {req_id}")
            continue

        execute_request(req_file)

    # 4. git push 响应
    git_push()
    log("✅ 轮询完成，响应已推送")

def main():
    log("=" * 60)
    log("🚀 云内核中枢请求轮询服务启动")
    log(f"📂 项目路径: {REPO_DIR}")
    log(f"⏱️ 轮询间隔: {POLL_INTERVAL}秒")
    log("=" * 60)

    while True:
        try:
            poll_once()
        except Exception as e:
            log(f"❌ 轮询异常: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
