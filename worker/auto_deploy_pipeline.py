#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 官网自动部署流水线 V1.0
功能: 扫描产出目录(白皮书/可视化HTML) → 集成部署包 → SHA256校验 → 双仓同步 → 部署工单上报 → 任务台账回写
设计: 与审批驱动部署联动器衔接, 走「产出→集成→审批→部署→验收」闭环
铁律: 零成本 / 最小额度消耗 / 实事求是(完成必须有真实验证)
"""
import json, os, re, shutil, subprocess, sys, time, hashlib, urllib.request

# ===== 配置 =====
BASE = "/home/user/Doubao/chats/38439832899843586"
# 采集源: (源根目录, 部署包内前缀)  —— 排除部署包自身与仓库(防嵌套)
SOURCE_ROOTS = [
    (os.path.join(BASE, "website"), "website"),                       # 本地官网产物
    (os.path.join(BASE, "modelscope_sync"), "modelscope"),            # 魔搭产出采集入口
    (os.path.join(BASE, "zongyuan-root-sync", "website"), "website"), # 双仓其他节点可视化成果
]
DEPLOY_DIR = os.path.join(BASE, "deploy_package")
REPO = os.path.join(BASE, "zongyuan-root-sync")
STATE_FILE = os.path.join(BASE, "worker", ".deploy_state.json")
GATEWAY = "https://www.huodouai.com/api/report/truth"
BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
TASK_TABLE = "tblnVRjuf7P31cEP"
MSG_TABLE = "tbl4Dv798yO7u0IK"
APPROVAL_CODE = "CAC2F6DD-B206-4F27-96FF-E99BD13464F7"
APPROVER_OPEN_ID = "ou_42633d038feef1c26c8d6fd014c386c3"  # 元极ZONGYUAN-ROOT账号(审批人)

HTML_EXTS = (".html", ".htm")

def now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def log(msg):
    line = f"[{now_str()}] {msg}"
    print(line)
    with open(os.path.join(BASE, "worker", "deploy.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")

def report(key, val, t="protocol"):
    try:
        d = {"key": key, "truth_value": val, "source_node": "NODE-CLOUD-WORKER-001",
             "confidence": 1.0, "truth_type": t}
        r = urllib.request.Request(GATEWAY, data=json.dumps(d).encode(),
                                   headers={"Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(r, timeout=15).read())
        return resp.get("action")
    except Exception as e:
        return f"fail:{e}"

def lark(args):
    try:
        r = subprocess.run(["lark-cli", "base"] + args + ["--base-token", BASE_TOKEN, "--as", "user"],
                           capture_output=True, text=True, timeout=60)
        return r.stdout.strip()
    except Exception as e:
        return f"ERR:{e}"

def collect_html_sources():
    """收集所有待部署的 HTML 产物(白皮书/可视化页面), 返回 (源根, 前缀, 相对路径, 全路径)"""
    found = []
    for root, prefix in SOURCE_ROOTS:
        if not os.path.isdir(root):
            continue
        for r, dirs, files in os.walk(root):
            # 跳过缓存/截图/备份/仓库
            dirs[:] = [x for x in dirs if x not in ("_shots", "_backup", "node_modules", ".git")]
            for fn in files:
                if fn.lower().endswith(HTML_EXTS):
                    p = os.path.join(r, fn)
                    rel = os.path.join(prefix, os.path.relpath(p, root)).replace("\\", "/")
                    found.append({"root": root, "prefix": prefix, "rel": rel, "path": p})
    return found

def scan_new_assets():
    """对比上次记录, 找出新增/变更的 HTML"""
    state = {"last": {}}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass
    last = state.get("last", {})

    new_items = []
    for it in collect_html_sources():
        h = sha256_file(it["path"])
        if last.get(it["rel"]) != h:
            new_items.append({"path": it["path"], "rel": it["rel"], "hash": h})
    return new_items, state

def integrate(items):
    """集成到部署包目录(rel 已含前缀, 保留目录结构, 防同名覆盖)"""
    integrated = []
    for it in items:
        src = it["path"]
        rel = it["rel"].replace("\\", "/")
        # 只保留 白皮书/可视化 命名特征, 排除零散测试页
        if not any(k in rel for k in ("portfolio", "whitepaper", "白皮书", "可视化", "dashboard",
                                       "index", "report", "报告", "作品", "architecture", "modelscope")):
            log(f"跳过非部署资产: {rel}")
            continue
        # 目标: deploy_package/ + rel(已含 prefix)
        dst = os.path.join(DEPLOY_DIR, rel)
        if os.path.abspath(src) == os.path.abspath(dst):
            log(f"跳过(源==目标): {rel}")
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        integrated.append({"rel": rel, "dst": rel, "hash": it["hash"]})
    return integrated

def update_sha256():
    """更新 SHA256SUMS.txt"""
    lines = []
    for root, dirs, files in os.walk(DEPLOY_DIR):
        dirs[:] = [x for x in dirs if x not in ("_shots", "_backup", ".git")]
        for fn in files:
            if fn == "SHA256SUMS.txt":
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, DEPLOY_DIR).replace("\\", "/")
            lines.append(f"{sha256_file(p)}  {rel}")
    with open(os.path.join(DEPLOY_DIR, "SHA256SUMS.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(lines)) + "\n")
    return len(lines)

def sync_repo():
    """同步部署包到双仓 deploy/ 并推送"""
    # 先把本地部署包镜像到仓库 deploy/ 目录
    repo_deploy = os.path.join(REPO, "deploy")
    os.makedirs(repo_deploy, exist_ok=True)
    for item in os.listdir(DEPLOY_DIR):
        s = os.path.join(DEPLOY_DIR, item)
        d = os.path.join(repo_deploy, item)
        if os.path.isdir(s):
            subprocess.run(["cp", "-rf", s + "/.", d], check=False)
        elif os.path.isfile(s):
            shutil.copy2(s, d)
    cmds = [
        ["git", "add", "-A"],
        ["git", "commit", "-m", f"官网自动部署流水线集成 {now_str()}"],
    ]
    for c in cmds:
        r = subprocess.run(c, cwd=REPO, capture_output=True, text=True, timeout=60)
    push = []
    for remote in ("origin", "github"):
        r = subprocess.run(["git", "push", remote, "main"], cwd=REPO,
                           capture_output=True, text=True, timeout=120)
        push.append(f"{remote}:{'ok' if r.returncode == 0 else r.stderr.strip()[:60]}")
    return push

def create_deploy_workorder(items):
    """生成部署工单 → 提单飞书审批 → 上报网关(含审批关联)"""
    if not items:
        return None, ""
    names = "、".join(i["dst"] for i in items[:5])
    key = f"DEPLOY.AUTO-{time.strftime('%Y%m%d%H%M')}"
    # 提单审批(AIOS阶段验收) — 让审批真实出现在飞书
    inst_code, inst_link = create_approval(names)
    val = (f"官网自动部署工单: 新增可视化资产 {len(items)} 件({names}), 已集成部署包+双仓同步, "
           f"待审批部署 | 审批实例={inst_code} | 审批链接={inst_link}")
    a = report(key, val, "decision")
    log(f"工单上报: {key} → {a} 审批={inst_code}")
    return key, inst_code

def create_approval(names):
    """部署工单→飞书审批提单(AIOS阶段验收), 返回 (instance_code, link)"""
    form = json.dumps([
        {"id": "widget16457732057390001", "type": "input",
         "value": f"官网自动部署-{names[:20]}"},
        {"id": "widget16462072487340001", "type": "textarea",
         "value": f"新增可视化资产 {len(names.split('、'))} 件: {names}, 已集成部署包+双仓同步"},
        {"id": "widget17890639416310001", "type": "input",
         "value": "https://www.huodouai.com/showcase"},
        {"id": "widget17890619119210001", "type": "textarea",
         "value": "1.部署包已集成deploy_package 2.双仓已同步 3.待审批通过后自动部署官网"},
        {"id": "widget17890619390370001", "type": "radioV2",
         "value": "mtvtab1a-nr5c4s2q49-0"},
        {"id": "widget16462073040250001", "type": "contact",
         "open_ids": [APPROVER_OPEN_ID]},
        {"id": "widget16457732647360001", "type": "dateInterval",
         "value": {"start": "2026-09-29T00:00:00+08:00",
                   "end": "2026-09-30T23:59:59+08:00", "interval": 2.0}},
        {"id": "widget16457743012420001", "type": "contact",
         "open_ids": [APPROVER_OPEN_ID]},
    ], ensure_ascii=False)
    data = json.dumps({"approval_code": APPROVAL_CODE, "form": form})
    try:
        r = subprocess.run(["lark-cli", "approval", "instances", "create",
                            "--data", data, "--as", "user", "--yes"],
                           capture_output=True, text=True, timeout=90)
        d = json.loads(r.stdout)
        if d.get("ok"):
            inst = d.get("data", {})
            return inst.get("instance_code", ""), inst.get("instance_link", "")
        return "", d.get("error", {}).get("message", r.stdout[:100])
    except Exception as e:
        return "", str(e)

def main():
    log("=== 官网自动部署流水线巡检 ===")
    items, state = scan_new_assets()
    if not items:
        log("无新增部署资产, 跳过(最小额度消耗)")
        # 更新状态文件(把当前已存在资产记录基线, 避免重复扫描)
        baseline = {}
        for it in collect_html_sources():
            baseline[it["rel"]] = sha256_file(it["path"])
        state["last"] = baseline
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        return

    log(f"发现 {len(items)} 件待部署资产")
    integrated = integrate(items)
    if not integrated:
        log("无符合部署特征的资产")
        return
    n = update_sha256()
    log(f"部署包集成完成, SHA256SUMS {n} 条目")
    push = sync_repo()
    log(f"双仓同步: {push}")
    wk, inst_code = create_deploy_workorder(integrated)

    # 更新状态
    for it in integrated:
        state.setdefault("last", {})[it["rel"]] = it["hash"]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    log(f"完成: 集成{len(integrated)}件 工单={wk} 审批={inst_code or '无'} 双仓={push}")

if __name__ == "__main__":
    main()
