#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT → 魔搭社区 自动增量发布引擎 v2.0
确权 DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

限流规则（实测确认）：
- POST /files/upload：滑动窗口约 2 次/30s，第 3 次 429 + Retry-After≈29s —— 本引擎不使用
- git 直推 / POST /collections/items / GET 类：无限流 —— 本引擎主力

策略：一切可 git 的走 git（媒体用数据集仓库承载），门户/索引自动生成，合集自动聚合。
v2 新增：全资产索引生成（INDEX.json）、门户 index.html 数据驱动更新+部署、合集自动补齐。
"""
import os, sys, json, time, shutil, subprocess, urllib.request, urllib.error, hashlib
from pathlib import Path

KROOT = Path("/home/user/Doubao/chats/38439570362876674/ZONGYUAN-ROOT")
STATE_FILE = KROOT / "config" / "ms_publish_state.json"
TOKEN_FILE = KROOT / "config" / "modelscope_token"
TMP = Path("/tmp/ms_auto_pub")
GATEWAY = "https://www.huodouai.com"
GIT_BASE = "https://oauth2:{}@www.modelscope.cn/{}/zongyuanroot/{}.git"
API = "https://modelscope.cn/openapi/v1"

# 仓库映射：repo_name -> (类型, 源目录列表) —— 类型支持 datasets/models/studios
REPOS = {
    "zongyuan-truth-corpus": ("datasets", [
        (KROOT / "config" / "central-truths", "central-truths"),
        (KROOT / "locks", "locks"),
        (KROOT / "meta-rules", "meta-rules"),
    ]),
    "zongyuan-character-keyframes": ("datasets", [
        (KROOT / "media-library" / "images", "media-images"),
    ]),
    "zongyuan-whitepaper": ("models", [
        (KROOT / "docs" if (KROOT / "docs").exists() else KROOT, "docs-root"),
    ]),
    "zongyuan-agent-framework": ("models", [
        (KROOT / "scripts", "scripts"),
    ]),
    "qwen-gguf-models": ("datasets", [
        (KROOT / "config" / "ms_index", "ms-index"),
    ]),
    "zongyuan-hub": ("studios", [
        (KROOT / "config" / "ms_hub_page", "hub-page"),
    ]),
}

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def get_token():
    t = os.environ.get("MS_TOKEN", "").strip()
    if t:
        return t
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    raise RuntimeError("MS_TOKEN 未配置")

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"repos": {}, "last_full": 0}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def collect_new(src_dir, last_ts):
    if not src_dir.exists():
        return []
    out = []
    for f in src_dir.rglob("*"):
        if f.is_file() and f.stat().st_mtime > last_ts:
            out.append((f, f.relative_to(src_dir).as_posix()))
    return out

def git_sync(repo_name, repo_type, token, state):
    repo_key = repo_name
    last_ts = state["repos"].get(repo_key, 0)
    all_new = []
    for src_dir, _ in REPOS[repo_name][1]:
        all_new.extend(collect_new(src_dir, last_ts))
    if not all_new:
        return True, 0, ""
    seen, unique = set(), []
    for f, rel in all_new:
        if rel not in seen:
            seen.add(rel)
            unique.append((f, rel))
    repo_dir = TMP / repo_name
    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    url = GIT_BASE.format(token, repo_type, repo_name)
    r = subprocess.run(["git", "clone", "--depth", "1", url, str(repo_dir)],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return False, 0, f"clone: {r.stderr.strip()[:120]}"
    copied = 0
    for f, rel in unique:
        dst = repo_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(f, dst)
            copied += 1
        except Exception as e:
            log(f"  ⚠ 复制 {rel}: {e}")
    if copied == 0:
        return True, 0, ""
    subprocess.run(["git", "add", "-A"], cwd=repo_dir, capture_output=True)
    r = subprocess.run(
        ["git", "-c", "user.name=ZONGYUAN-ROOT", "-c", "user.email=zongyuanroot@modelscope.cn",
         "commit", "-m", f"自动增量发布 {copied} 文件 [DID-BR-000002] Ω₀⊂⊙∞⊂Ω"],
        cwd=repo_dir, capture_output=True, text=True, timeout=60)
    if r.returncode != 0 and "nothing to commit" not in r.stderr:
        return False, 0, f"commit: {r.stderr.strip()[:120]}"
    r = subprocess.run(["git", "push"], cwd=repo_dir, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return False, 0, f"push: {r.stderr.strip()[:120]}"
    return True, copied, ""

# ---------- 索引与门户生成（数据驱动，无限流） ----------

def count_dir(d):
    if not d.exists():
        return 0
    return sum(1 for f in d.rglob("*") if f.is_file())

def build_index():
    """生成全资产索引 INDEX.json 与门户 index.html"""
    idx = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "did": "DID-BR-000002",
        "trace": "Ω₀⊂⊙∞⊂Ω",
        "gateway": GATEWAY,
        "assets": {
            "truths": count_dir(KROOT / "config" / "central-truths"),
            "locks": count_dir(KROOT / "locks"),
            "meta_rules": count_dir(KROOT / "meta-rules") if (KROOT / "meta-rules").exists() else 0,
            "plans": count_dir(KROOT / "plans") if (KROOT / "plans").exists() else 0,
            "images": count_dir(KROOT / "media-library" / "images"),
            "scripts": count_dir(KROOT / "scripts"),
        },
        "repos": {
            "models": ["zongyuan-whitepaper", "zongyuan-agent-framework"],
            "datasets": ["zongyuan-truth-corpus", "zongyuan-character-keyframes", "qwen-gguf-models"],
            "studios": ["zongyuan-hub"],
            "skills": ["zongyuan-truth-query"],
            "collections": ["wwwhuodouaicom"],
        },
    }
    idx_dir = KROOT / "config" / "ms_index"
    idx_dir.mkdir(parents=True, exist_ok=True)
    (idx_dir / "INDEX.json").write_text(json.dumps(idx, ensure_ascii=False, indent=2))
    # 摘要 md
    md = f"""# ZONGYUAN-ROOT 资产索引
- 生成时间：{idx['generated_at']}
- 确权：{idx['did']} ｜ {idx['trace']}
- 真值 {idx['assets']['truths']} ｜ 锁档 {idx['assets']['locks']} ｜ 图片 {idx['assets']['images']}
"""
    (idx_dir / "INDEX.md").write_text(md)
    # 门户页面
    page_dir = KROOT / "config" / "ms_hub_page"
    page_dir.mkdir(parents=True, exist_ok=True)
    cards = [
        ("PORTAL · 官网", "火斗云智官网", "云端中枢智能主域，记忆网关、全域真值汇聚与作品库展示节点。",
         "https://www.huodouai.com"),
        ("WORKS · 作品库", "官网作品画廊", "昆仑女帝系列作品画廊与关键帧画廊，公网直览。",
         "https://www.huodouai.com/works-gallery-v2.html"),
        ("MODEL · 白皮书", "体系白皮书与总报告", "三层架构远程连接运维技术白皮书 V1.0 与全域稳态自治体系完整论述总报告。",
         "https://modelscope.cn/models/zongyuanroot/zongyuan-whitepaper"),
        ("DATASET · 真值", "真值语料库", f"中央真值镜像 {idx['assets']['truths']} 条、锁档 {idx['assets']['locks']} 份。",
         "https://modelscope.cn/datasets/zongyuanroot/zongyuan-truth-corpus"),
        ("DATASET · 视觉", "昆仑洞天角色关键帧", f"昆仑女帝三幕剧关键帧、角色立绘、质检帧（图片 {idx['assets']['images']} 项）。",
         "https://modelscope.cn/datasets/zongyuanroot/zongyuan-character-keyframes"),
        ("AGENT", "真值智能体", "ZONGYUAN 真值 Agent：检索网关状态、真值列表与指定真值内容。",
         "https://modelscope.cn/agents/zongyuanroot/zongyuan-truth-agent"),
        ("SKILL", "真值检索技能", "ZONGYUAN 真值检索：网关状态、真值列表、指定真值内容。",
         "https://modelscope.cn/skills/zongyuanroot/zongyuan-truth-query"),
        ("GALLERY · 白皮书", "白皮书画廊", "体系白皮书 PDF 数字画廊展示。",
         "https://modelscope.cn/gallery/zongyuanroot/zongyuan-whitepaper"),
        ("COLLECTION", "体系资产合集", "模型/数据集/创空间/技能全聚合，一处直达。",
         "https://modelscope.cn/collections/zongyuanroot/wwwhuodouaicom"),
    ]
    cards_html = "\n".join(
        f"""<div class="card"><div class="tag">{t}</div><h3>{h}</h3><p>{d}</p><a href="{u}" target="_blank">查看 →</a></div>"""
        for t, h, d, u in cards)
    page = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ZONGYUAN-ROOT 体系中枢</title>
<style>:root{{--bg:#0a0e1a;--card:#121829;--gold:#d4af37;--cyan:#5eead4;--text:#e2e8f0;--muted:#94a3b8}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:radial-gradient(ellipse at 50% -20%,#1a2440 0%,var(--bg) 60%);color:var(--text);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;min-height:100vh}}
.wrap{{max-width:1080px;margin:0 auto;padding:48px 24px 80px}}
.hero{{text-align:center;margin-bottom:44px}}
.badge{{display:inline-block;padding:6px 16px;border:1px solid var(--gold);color:var(--gold);border-radius:999px;font-size:13px;letter-spacing:2px;margin-bottom:20px}}
h1{{font-size:40px;font-weight:800;letter-spacing:4px;background:linear-gradient(90deg,#fff,var(--gold));-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:12px}}
.sub{{color:var(--muted);font-size:15px;letter-spacing:1px}}
.omega{{color:var(--cyan);font-size:13px;margin-top:14px;letter-spacing:1px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin-top:24px}}
.card{{background:var(--card);border:1px solid #1e293b;border-radius:14px;padding:20px;transition:transform .2s,border-color .2s}}
.card:hover{{transform:translateY(-3px);border-color:var(--gold)}}
.card .tag{{font-size:11px;color:var(--cyan);letter-spacing:1px;margin-bottom:8px}}
.card h3{{font-size:16px;margin-bottom:6px}}
.card p{{color:var(--muted);font-size:13px;line-height:1.6}}
.card a{{display:inline-block;margin-top:10px;color:var(--gold);text-decoration:none;font-size:13px}}
.foot{{text-align:center;margin-top:48px;color:var(--muted);font-size:12px;line-height:2}}
.foot .did{{color:var(--cyan)}}</style></head>
<body><div class="wrap"><div class="hero">
<div class="badge">全域稳态自治 AI 体系</div>
<h1>ZONGYUAN-ROOT</h1>
<p class="sub">云端中枢智能主控 · 多节点自治协作 · 真值确权溯源</p>
<div class="omega">Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 更新 {idx['generated_at']}</div>
</div>
<div class="grid">
{cards_html}
</div>
<div class="foot"><div class="did">DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ ZONGYUAN-ROOT</div><div>云端中枢智能主控 · 全域同步 · 哈希锁档 · 自主进化</div></div>
</div></body></html>"""
    (page_dir / "index.html").write_text(page)
    return idx

def sync_collection(token):
    """合集自动补齐（POST 无限流，幂等）"""
    url = f"{API}/collections/zongyuanroot/wwwhuodouaicom"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}), timeout=15) as r:
            d = json.loads(r.read().decode()).get("data", {})
        have = {(it.get("item_type"), it.get("item_object_id")) for it in d.get("items", [])}
    except Exception as e:
        return {"ok": False, "err": str(e)[:100]}
    want = [
        ("model", "zongyuanroot/zongyuan-whitepaper", 1, "体系白皮书与总报告"),
        ("model", "zongyuanroot/huodouai-zongyuan-3b", 2, "火斗云智体系模型"),
        ("model", "zongyuanroot/zongyuan-agent-framework", 3, "多Agent自治框架"),
        ("dataset", "zongyuanroot/zongyuan-truth-corpus", 4, "真值语料库"),
        ("dataset", "zongyuanroot/zongyuan-character-keyframes", 5, "角色关键帧"),
        ("studio", "zongyuanroot/zongyuan-hub", 6, "体系中枢展示站"),
        ("skill", "zongyuanroot/zongyuan-truth-query", 7, "真值检索技能"),
        ("dataset", "zongyuanroot/qwen-gguf-models", 8, "Qwen GGUF 量化模型索引"),
        # 死路（勿重试）：合集 item_type oneof 校验不支持 agent 类目，Agent 展示由 zongyuan-hub 门户承载
    ]
    missing = [w for w in want if (w[0], w[1]) not in have]
    if not missing:
        return {"ok": True, "added": 0, "total": len(want)}
    body = json.dumps({"items": [
        {"item_type": t, "item_object_id": i, "note": n, "position": p}
        for t, i, p, n in missing]}).encode()
    req = urllib.request.Request(f"{url}/items", data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"ok": True, "added": len(missing), "total": len(want), "resp": resp.read().decode()[:80]}
    except urllib.error.HTTPError as e:
        return {"ok": False, "err": e.read().decode()[:100]}

def deploy_hub(token):
    """触发创空间部署（无限流）"""
    req = urllib.request.Request(f"{API}/studios/zongyuanroot/zongyuan-hub/deploy",
        data=b"{}", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode()).get("data", {}).get("status", "?")
    except Exception as e:
        return f"err:{str(e)[:80]}"

def report_gateway(truth_key, value):
    body = json.dumps({
        "truth_key": truth_key,
        "truth_value": json.dumps(value, ensure_ascii=False),
        "source_node": "local-doubao-window",
        "confidence": 0.95,
        "truth_type": "operation"}).encode()
    req = urllib.request.Request(f"{GATEWAY}/api/report/truth", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()).get("action", "ok")
    except Exception as e:
        return f"err:{str(e)[:80]}"

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    token = get_token()
    state = load_state()
    log(f"=== 魔搭自动增量发布 v2 {mode} ===")
    # 1. 生成索引与门户（始终刷新）
    idx = build_index()
    log(f"索引生成: 真值 {idx['assets']['truths']} | 锁档 {idx['assets']['locks']} | 图片 {idx['assets']['images']}")
    # 2. git 增量推送
    results, total = {}, 0
    for repo_name, (repo_type, _) in REPOS.items():
        ok, n, err = git_sync(repo_name, repo_type, token, state)
        results[repo_name] = {"ok": ok, "new": n, "err": err}
        total += n
        if ok:
            if n:
                log(f"  ✅ {repo_name}: {n} 文件")
                state["repos"][repo_name] = time.time()
            else:
                log(f"  ⏭ {repo_name}: 无新增")
        else:
            log(f"  ❌ {repo_name}: {err}")
    save_state(state)
    # 3. 合集补齐
    col = sync_collection(token) if mode == "run" else {"ok": True, "added": 0, "total": 7}
    log(f"合集: {col}")
    # 4. 门户部署（hub 有更新时）
    deploy = "skip"
    if mode == "run" and results.get("zongyuan-hub", {}).get("ok") and total > 0:
        deploy = deploy_hub(token)
        log(f"门户部署: {deploy}")
    # 5. 汇报
    ts = time.strftime("%Y%m%d-%H%M%S")
    value = {"action": "自动增量发布v2", "total_new": total, "repos": results,
             "collection": col, "deploy": deploy, "index": idx["assets"],
             "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω"}
    if mode == "run":
        resp = report_gateway(f"MODELSCOPE.AUTO.PUBLISH.V2.{ts}", value)
        log(f"网关上报: {resp}")
    else:
        log(f"[dry-run] 预计新增 {total} 文件")
    log("=== 完成 ===")

if __name__ == "__main__":
    main()
