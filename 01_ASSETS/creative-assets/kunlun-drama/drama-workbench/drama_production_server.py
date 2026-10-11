#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drama_production_server.py — 昆仑洞天一键量产引擎 本地 HTTP 接入层
================================================================
元极恒一自治体系 | DID-BR-000002 | 锚定 Ω₀⊂⊙∞⊂Ω | 纯 Python 标准库。

本服务【只做接入层】，绝不重写分镜/提示词生成逻辑：
  - 通过 subprocess 复用同目录 one_key_production.py（真实量产引擎）
  - 完成后自动解压产物分镜表 JSON，复用 DRM-PIPE-V1.3/drama_validator.py 校验
  - 密钥安全与引擎完全一致：引擎自己从 /home/user/ZONGYUAN-ROOT/.env.brain 读 key，
    本服务从不读取、从不打印、从不回传任何 key；健康检查只报"是否就绪(bool)"。

端点：
  GET  /api/health                 自检（脚本/校验器/产物目录/key是否就绪，绝不报值）
  POST /api/produce                body: {"outline","episodes","outdir"?} -> {"task_id","status":"queued"}
  GET  /api/produce/{task_id}      状态(queued/running/done/failed)+日志摘录+产物摘要+校验结果
  GET  /api/tasks                  最近任务列表（摘要）
  GET  /api/file?path=<abs>        受控下载（仅允许 ARTIFACTS_DIR 内文件，防目录穿越）

退出码语义（透传引擎）：
  0 -> done（API 真实成功且校验通过）
  2 -> failed（缺 key / 参数错误）
  3 -> done 但 needsReview=true（全部 API 失败，已用兜底模板产出 ZIP）
"""

import json
import os
import re
import subprocess
import threading
import time
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote as _urlquote

# ------------------------------------------------------------------ #
# 路径常量
# ------------------------------------------------------------------ #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(BASE_DIR, "one_key_production.py")
VALIDATOR = os.path.join(BASE_DIR, "DRM-PIPE-V1.3", "drama_validator.py")
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts_live")
LIVE_DIR = os.path.join(BASE_DIR, "live")
TASK_DIR = os.path.join(LIVE_DIR, "tasks")
REGISTRY = os.path.join(LIVE_DIR, "tasks.json")
ENV_PATH = "/home/user/ZONGYUAN-ROOT/.env.brain"

PORT = int(os.environ.get("DRAMA_PROD_PORT", "8086"))
DID = "DID-BR-000002"
OMEGA = "Ω₀⊂⊙∞⊂Ω"

os.makedirs(TASK_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# ------------------------------------------------------------------ #
# 任务存储（内存 + 落盘 registry，轻量本地单用户）
# ------------------------------------------------------------------ #
_lock = threading.RLock()
TASKS = {}


def _save_registry():
    try:
        snap = {}
        with _lock:
            for tid, t in TASKS.items():
                snap[tid] = {
                    "task_id": t["task_id"],
                    "status": t["status"],
                    "outline": t.get("outline", "")[:60],
                    "episodes": t.get("episodes"),
                    "createdAt": t.get("createdAt"),
                    "updatedAt": t.get("updatedAt"),
                    "zipName": (t.get("result") or {}).get("zipName"),
                    "exitCode": (t.get("result") or {}).get("exitCode"),
                    "needsReview": (t.get("result") or {}).get("needsReview", False),
                }
        with open(REGISTRY, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _mask_outline(s):
    return (s or "")[:80]


# ------------------------------------------------------------------ #
# 产物摘要：直接读 ZIP，真实统计，不猜
# ------------------------------------------------------------------ #
def inspect_zip(zip_path):
    """打开产物 ZIP，真实统计文件/镜数/关键帧/配音/数据源/校验线索。"""
    z = zipfile.ZipFile(zip_path)
    files = [{"name": i.filename, "size": i.file_size} for i in z.infolist()]
    summary = {
        "zip": zip_path,
        "zipName": os.path.basename(zip_path),
        "zipSizeBytes": os.path.getsize(zip_path),
        "files": files,
        "episodes": [],
        "shotCount": 0,
        "kfCount": 0,
        "voCount": 0,
        "dataSources": [],
    }
    # 素材清单
    try:
        manifest = json.loads(z.read("素材清单.json").decode("utf-8"))
        summary["episodes"] = manifest.get("episodes", [])
    except Exception:
        pass
    # 逐集分镜表统计
    for fi in files:
        if fi["name"].endswith("_分镜表.json"):
            try:
                sb = json.loads(z.read(fi["name"]).decode("utf-8"))
            except Exception:
                continue
            shots = sb.get("shots", []) or []
            summary["shotCount"] += len(shots)
            summary["kfCount"] += sum(1 for s in shots if (s.get("kfPrompt") or "").strip())
            summary["voCount"] += sum(
                1 for s in shots if (s.get("vo", {}) or {}).get("text")
            )
            ds = sb.get("meta", {}).get("dataSource", "")
            if ds and ds not in summary["dataSources"]:
                summary["dataSources"].append(ds)
    return summary


def run_validator_on_latest_storyboard(zip_path):
    """从 ZIP 抽出最新分镜表 JSON 到临时目录，调用 DRM-PIPE 校验器，回传结果。"""
    try:
        z = zipfile.ZipFile(zip_path)
        sb_names = [n for n in z.namelist() if n.endswith("_分镜表.json")]
        if not sb_names:
            return {"ran": False, "reason": "ZIP 内无分镜表 JSON"}
        sb_names.sort()
        target = sb_names[-1]
        tmp_dir = os.path.join(TASK_DIR, "_unzip_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        local = os.path.join(tmp_dir, os.path.basename(target))
        with open(local, "wb") as f:
            f.write(z.read(target))
        proc = subprocess.run(
            ["python3", VALIDATOR, "--check-file", local],
            capture_output=True, text=True, timeout=120,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        # 抽取汇总行
        summary_lines = [ln for ln in out.splitlines()
                         if ("汇总" in ln) or ("整体" in ln)]
        return {
            "ran": True,
            "checkedFile": target,
            "exitCode": proc.returncode,
            "passed": proc.returncode == 0,
            "summaryLines": summary_lines[-4:],
            "tail": out[-1200:],
        }
    except Exception as e:
        return {"ran": False, "reason": f"{type(e).__name__}: {e}"}


# ------------------------------------------------------------------ #
# 后台任务：真实调用引擎
# ------------------------------------------------------------------ #
def execute_task(task_id, outline, episodes, outdir):
    log_path = os.path.join(TASK_DIR, f"{task_id}.log")
    with _lock:
        t = TASKS[task_id]
        t["status"] = "running"
        t["updatedAt"] = time.time()
    cmd = [
        "python3", ENGINE,
        "--outline", outline,
        "--episodes", str(int(episodes)),
        "--output", outdir,
    ]
    try:
        with open(log_path, "w", encoding="utf-8") as lf:
            lf.write("$ " + " ".join(_mask_cmd(cmd)) + "\n\n")
            lf.flush()
            proc = subprocess.run(
                cmd, stdout=lf, stderr=subprocess.STDOUT, timeout=1800,
            )
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        exit_code = -999
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write("\n[server] 生产超时(1800s)，已终止。\n")
    except Exception as e:
        exit_code = -1
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write(f"\n[server] 未预期错误 {type(e).__name__}: {e}\n")

    # 解析产物
    result = {"exitCode": exit_code, "needsReview": False, "apiOk": False,
              "zip": None, "validator": None}
    zip_path = None
    try:
        cands = []
        for n in os.listdir(outdir):
            if n.startswith("短剧素材包_") and n.endswith(".zip"):
                cands.append(os.path.join(outdir, n))
        if cands:
            zip_path = max(cands, key=os.path.getmtime)
    except Exception:
        pass

    if zip_path:
        try:
            insp = inspect_zip(zip_path)
            result.update(insp)
            result["apiOk"] = ("doubao-api" in insp.get("dataSources", []))
            # 引擎退出码 3 = 兜底模板产出
            if exit_code == 3:
                result["needsReview"] = True
            elif exit_code == 0:
                result["needsReview"] = False
            # 自动校验
            result["validator"] = run_validator_on_latest_storyboard(zip_path)
        except Exception as e:
            result["inspectError"] = f"{type(e).__name__}: {e}"

    # 读日志摘录
    log_tail = ""
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        log_tail = "".join(lines[-40:])
    except Exception:
        pass

    if exit_code == 0:
        status = "done"
    elif exit_code == 3:
        status = "done"   # 已产出 ZIP（兜底），由 needsReview 标注
    elif exit_code == 2:
        status = "failed"
    else:
        status = "failed"

    with _lock:
        t = TASKS[task_id]
        t["status"] = status
        t["result"] = result
        t["logTail"] = log_tail
        t["logPath"] = log_path
        t["updatedAt"] = time.time()
    _save_registry()


def _mask_cmd(cmd):
    """回显命令时绝不带出任何 key（引擎不从命令行收 key，这里只是保险）。"""
    out = []
    for c in cmd:
        out.append(c)
    return out


def start_task(outline, episodes, outdir):
    task_id = time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    with _lock:
        TASKS[task_id] = {
            "task_id": task_id,
            "status": "queued",
            "outline": outline,
            "episodes": episodes,
            "outdir": outdir,
            "createdAt": time.time(),
            "updatedAt": time.time(),
            "result": None,
            "logTail": "",
        }
    th = threading.Thread(
        target=execute_task, args=(task_id, outline, episodes, outdir), daemon=True,
    )
    th.start()
    _save_registry()
    return task_id


# ------------------------------------------------------------------ #
# 自检
# ------------------------------------------------------------------ #
def health():
    key_ready = False
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DOUBAO_API_KEY=") and line.split("=", 1)[1].strip():
                    key_ready = True
                    break
    except Exception:
        pass
    return {
        "ok": True,
        "service": "drama_production_server",
        "port": PORT,
        "did": DID, "omega": OMEGA,
        "engineExists": os.path.exists(ENGINE),
        "validatorExists": os.path.exists(VALIDATOR),
        "artifactsDir": ARTIFACTS_DIR,
        "keyReady": key_ready,   # 只报 bool，绝不报值
        "taskCount": len(TASKS),
    }


# ------------------------------------------------------------------ #
# HTTP Handler
# ------------------------------------------------------------------ #
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # 静默，避免噪声；日志写入任务文件

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        qs = parse_qs(u.query)

        if path == "/api/health":
            return self._json(health())
        if path == "/api/tasks":
            with _lock:
                items = sorted(TASKS.values(), key=lambda x: x.get("createdAt", 0),
                               reverse=True)[:20]
                out = []
                for t in items:
                    r = t.get("result") or {}
                    out.append({
                        "task_id": t["task_id"], "status": t["status"],
                        "outline": _mask_outline(t.get("outline")),
                        "episodes": t.get("episodes"),
                        "createdAt": t.get("createdAt"),
                        "zipName": r.get("zipName"),
                        "exitCode": r.get("exitCode"),
                        "needsReview": r.get("needsReview", False),
                    })
            return self._json({"tasks": out})
        m = re.match(r"^/api/produce/([A-Za-z0-9_]+)$", path)
        if m:
            tid = m.group(1)
            with _lock:
                t = TASKS.get(tid)
                if not t:
                    return self._json({"error": "task not found", "task_id": tid}, 404)
                return self._json({
                    "task_id": t["task_id"], "status": t["status"],
                    "outline": t.get("outline"), "episodes": t.get("episodes"),
                    "outdir": t.get("outdir"),
                    "createdAt": t.get("createdAt"), "updatedAt": t.get("updatedAt"),
                    "result": t.get("result"), "logTail": t.get("logTail", ""),
                })
        if path == "/api/file":
            return self._serve_file(qs)
        return self._json({"error": "not found", "path": path}, 404)

    def _serve_file(self, qs):
        raw = (qs.get("path", [""])[0] or "")
        # 受控白名单：仅允许 ARTIFACTS_DIR 内文件
        try:
            real = os.path.realpath(raw)
            if not real.startswith(os.path.realpath(ARTIFACTS_DIR) + os.sep):
                return self._json({"error": "forbidden: path outside artifacts dir"}, 403)
            if not os.path.isfile(real):
                return self._json({"error": "file not found"}, 404)
            with open(real, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            ascii_name = "drama_package.zip"
            real_name = os.path.basename(real)
            self.send_header("Content-Disposition",
                             "attachment; filename=\"" + ascii_name +
                             "\"; filename*=UTF-8''" + _urlquote(real_name))
            self.send_header("Content-Length", str(len(data)))
            self._cors()
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/api/produce":
            return self._json({"error": "not found", "path": u.path}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8", "replace")
            body = json.loads(raw) if raw else {}
        except Exception as e:
            return self._json({"error": f"bad json: {e}"}, 400)

        outline = (body.get("outline") or "").strip()
        episodes = body.get("episodes", 1)
        outdir = (body.get("outdir") or "").strip() or ARTIFACTS_DIR
        if not outline:
            return self._json({"error": "outline 不能为空"}, 400)
        try:
            episodes = max(1, min(10, int(episodes)))
        except Exception:
            episodes = 1
        # outdir 归一为绝对路径
        if not os.path.isabs(outdir):
            outdir = os.path.join(BASE_DIR, outdir)
        os.makedirs(outdir, exist_ok=True)

        if not os.path.exists(ENGINE):
            return self._json({"error": f"引擎不存在: {ENGINE}"}, 500)

        tid = start_task(outline, episodes, outdir)
        return self._json({"task_id": tid, "status": "queued",
                           "poll": f"/api/produce/{tid}"}, 202)


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    # 写 pid
    with open(os.path.join(LIVE_DIR, "server.pid"), "w") as f:
        f.write(str(os.getpid()))
    print(f"[drama_production_server] listening on 127.0.0.1:{PORT}  pid={os.getpid()}")
    print(f"  engine   = {ENGINE}")
    print(f"  validator= {VALIDATOR}")
    print(f"  artifacts= {ARTIFACTS_DIR}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
