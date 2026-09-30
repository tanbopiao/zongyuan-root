#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTO-WP-FORGE 白皮书自动锻造引擎 v1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | NODE-DEV-DOUBAO-WORK-001

功能：全自动 提炼生成书 → 确权 → 推送到魔搭展示
  - 扫描种子目录(每子目录一个模块,含 meta.json 提炼要点)
  - 未生成/变更模块 → 自动渲染统一模板白皮书HTML
  - SHA256 确权 + ATTESTATION 凭证 + 批次根哈希
  - Git 直推 魔搭 zongyuan-whitepaper/datalake/whitepapers/whitepaper-matrix/
  - 上报记忆网关 + 本地台账 wp_state.json
  - 幂等：无新模块/无变更则跳过推送；支持 --dry-run / --force

用法:
  python3 auto_wp_forge.py            # 全自动执行
  python3 auto_wp_forge.py --dry-run  # 只生成+确权,不推送
  python3 auto_wp_forge.py --force    # 忽略状态,全部重建
  python3 auto_wp_forge.py --batch <skills_root>  # 批量模式:扫描技能目录所有SKILL.md批量成书(已有白皮书的跳过)
"""
import os, sys, json, hashlib, time, subprocess, urllib.request, urllib.error
from pathlib import Path

DRY = '--dry-run' in sys.argv
FORCE = '--force' in sys.argv
BATCH = None
if '--batch' in sys.argv:
    i = sys.argv.index('--batch')
    if i + 1 < len(sys.argv):
        BATCH = Path(sys.argv[i + 1])

# ============ 配置 ============
BASE = Path('/home/user/ZONGYUAN-ROOT')
SEED_DIR = BASE / 'config' / 'wp-seed'                      # 种子素材目录
STATE_FILE = BASE / 'data' / 'wp_state.json'                # 生成状态台账
REPO_DIR = Path('/home/user/Doubao/chats/38441716968655362/.tmp-zongyuan-whitepaper')  # 魔搭仓库本地镜像
REPO_SUBDIR = 'datalake/whitepapers/whitepaper-matrix'     # 仓库内白皮书矩阵目录
TOKEN_FILE = Path.home() / '.modelscope' / 'credentials' / 'git_token'
GATEWAY = 'https://www.huodouai.com/api/report/truth'
GIT_NAME, GIT_EMAIL = 'zongyuanroot', '195162494@qq.com'
DID, ANCHOR, NODE = 'DID-BR-000002', 'Ω₀⊂⊙∞⊂Ω', 'NODE-DEV-DOUBAO-WORK-001'

# ============ 模板（深色科技风，与矩阵统一） ============
TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Crect width='24' height='24' rx='5' fill='%23070b16'/%3E%3Ccircle cx='12' cy='12' r='7' fill='none' stroke='%23ffc857' stroke-width='1.6'/%3E%3Ccircle cx='12' cy='12' r='2.4' fill='%234fc3f7'/%3E%3C/svg%3E">
<style>
  :root{{
    --bg:#070b16; --bg2:#0b1224; --card:#0e1730; --card2:#121c38;
    --line:#1e2a4d; --line2:#2a3a66;
    --txt:#e8eefc; --sub:#8fa3c8; --dim:#5c6f96;
    --gold:#ffc857; --cyan:#4fc3f7; --violet:#a78bfa; --red:#ff6b6b; --green:#6ee7b7;
    --mono:'JetBrains Mono',Consolas,'Courier New',monospace;
  }}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:
    radial-gradient(1200px 500px at 80% -10%, rgba(79,195,247,.08), transparent 60%),
    radial-gradient(900px 400px at -10% 20%, rgba(167,139,250,.07), transparent 55%),
    var(--bg);
    color:var(--txt); font-family:'Noto Sans SC','PingFang SC','Microsoft YaHei',system-ui,sans-serif;
    line-height:1.7; min-height:100vh}}
  .wrap{{max-width:1000px;margin:0 auto;padding:32px 20px 64px}}
  .doc-head{{border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:28px}}
  .doc-head .wpnum{{font-family:var(--mono);font-size:12px;color:var(--gold);letter-spacing:.14em}}
  .doc-head h1{{font-size:26px;font-weight:800;margin:8px 0 6px}}
  .doc-head .meta{{font-size:12px;color:var(--dim);display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:10px}}
  .doc-head .meta b{{color:var(--sub);font-weight:500}}
  h2{{font-size:18px;font-weight:800;margin:34px 0 12px;display:flex;align-items:center;gap:10px}}
  h2 .n{{color:var(--gold);font-family:var(--mono);font-size:13px;border:1px solid var(--line2);border-radius:6px;padding:2px 9px}}
  h3{{font-size:14px;font-weight:700;color:var(--cyan);margin:18px 0 8px}}
  p{{font-size:13.5px;color:var(--sub);margin-bottom:8px}}
  p b{{color:var(--txt)}}
  .formula{{background:var(--card2);border:1px solid var(--line2);border-left:3px solid var(--gold);border-radius:8px;padding:14px 18px;font-family:var(--mono);font-size:13.5px;color:var(--gold);margin:12px 0;overflow-x:auto}}
  .tbl{{width:100%;border-collapse:collapse;font-size:12.5px;margin:12px 0;table-layout:fixed}}
  .tbl th{{color:var(--sub);font-weight:500;text-align:left;padding:9px 10px;border-bottom:1px solid var(--line2);white-space:nowrap}}
  .tbl td{{padding:8px 10px;border-bottom:1px solid var(--line);color:var(--txt);vertical-align:top}}
  .tbl .mono{{font-family:var(--mono);color:var(--cyan);font-size:11.5px}}
  .tbl td b{{color:var(--gold)}}
  .callout{{background:linear-gradient(160deg,var(--card),var(--card2));border:1px solid var(--line2);border-left:4px solid var(--cyan);border-radius:10px;padding:16px 18px;margin:16px 0;font-size:13px;color:var(--sub)}}
  .callout b{{color:var(--cyan)}}
  footer{{margin-top:48px;padding-top:18px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:10px 24px;justify-content:space-between;font-size:11.5px;color:var(--dim)}}
  .lockline{{font-family:var(--mono);color:var(--gold);font-size:11px}}
  .back{{display:inline-block;margin-bottom:20px;font-size:12px;color:var(--cyan);text-decoration:none;border:1px solid var(--line2);padding:4px 14px;border-radius:8px}}
  .back:hover{{background:rgba(79,195,247,.08)}}
  @media(max-width:620px){{
    .doc-head h1{{font-size:21px}}
    .wrap{{padding:20px 12px 48px}}
    .tbl{{font-size:11.5px}}
    .formula{{font-size:12px}}
  }}
</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="index.html">← 返回白皮书矩阵</a>
  <div class="doc-head">
    <div class="wpnum">{wpnum} · {wpcat} · 自动锻造</div>
    <h1>{title}技术白皮书</h1>
    <div class="meta">
      <span>版本：<b>{version}</b></span>
      <span>日期：<b>{date}</b></span>
      <span>确权：<b>{did}</b></span>
      <span>锚定：<b>{anchor}</b></span>
      <span>来源：<b>{source}</b></span>
      <span>产线：<b>AUTO-WP-FORGE v1.0</b></span>
    </div>
  </div>

  <h2><span class="n">01</span> 摘要</h2>
  <p>{abstract}</p>
  <div class="callout"><b>一句话：</b>{one_line}</div>

  <h2><span class="n">02</span> 核心能力</h2>
  <div class="tbl">
    <colgroup><col style="width:30%"><col style="width:70%"></colgroup>
    <tr><th>能力</th><th>说明</th></tr>
    {cap_rows}
  </div>

  <h2><span class="n">03</span> 执行流程</h2>
  <div class="formula">{formula}</div>

  {extra}

  <div class="callout"><b>体系说明：</b>{footnote}</div>

  <footer>
    <div>火斗云智AIOS 技术白皮书矩阵 · {wpnum}</div>
    <div class="lockline">{anchor} · {did} · {node}</div>
  </footer>
</div>
</body>
</html>
'''

# ============ 自动提炼（进化2：无需手写meta.json） ============
def next_wpnum(st: dict) -> str:
    nums = []
    for r in st.get("wp", {}).values():
        n = r.get("wpnum", "")
        if n.startswith("WP-"):
            try:
                nums.append(int(n[3:]))
            except Exception:
                pass
    return f"WP-{max(nums) + 1:03d}" if nums else "WP-011"

def extract_meta_from_md(md_path: Path) -> dict:
    """从 SKILL.md / README 自动提炼白皮书元数据"""
    import re
    text = md_path.read_text(encoding='utf-8')
    fm = {}
    m = re.match(r'^---\n(.*?)\n---', text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                fm[k.strip()] = v.strip().strip('"')
    name = fm.get('name') or md_path.parent.name
    version = fm.get('version', 'V1.0')
    desc = fm.get('description', '')
    abstract = desc
    if not abstract:
        for ln in text.splitlines():
            ln = ln.strip()
            if ln and not ln.startswith('#') and len(ln) > 20:
                abstract = ln
                break
    one_line = abstract[:80] + ('…' if len(abstract) > 80 else '')
    # 标题：优先从摘要提取中文模块名（xx引擎/体系/内核/中枢/平台/流水线）
    title = name.replace('-', ' ').title()
    mz = re.search(r'([\u4e00-\u9fa5]{2,14}(?:引擎|体系|内核|中枢|平台|流水线|机制|架构|基座))', abstract)
    if mz:
        title = mz.group(1)
    caps = []
    for m3 in re.finditer(r'^###\s+(.+)$', text, re.M):
        cap = m3.group(1).strip()
        after = text[m3.end():].splitlines()
        d = ''
        for ln in after[:8]:
            ln = ln.strip()
            if ln.startswith('-'):
                ln = ln[1:].strip()
            if ln and not ln.startswith(('#', '|', '>', '```')) and len(ln) > 5:
                d = ln[:60] + ('…' if len(ln) > 60 else '')
                break
        caps.append([cap, d or '核心能力'])
        if len(caps) >= 8:
            break
    if not caps:
        for m2 in re.finditer(r'^##\s+(.+)$', text, re.M):
            cap = m2.group(1).strip()
            if any(k in cap for k in ('能力', '架构', '功能', '层', '域')):
                after = text[m2.end():].splitlines()
                d = ''
                for ln in after[:8]:
                    ln = ln.strip()
                    if ln.startswith('-'):
                        ln = ln[1:].strip()
                    if ln and not ln.startswith(('#', '|', '>', '```')) and len(ln) > 5:
                        d = ln[:60] + ('…' if len(ln) > 60 else '')
                        break
                caps.append([cap, d or '核心能力'])
                if len(caps) >= 8:
                    break
    if not caps:
        for row in re.findall(r'^\|\s*([^|]{2,24})\s*\|\s*([^|]{6,})', text, re.M):
            caps.append([row[0].strip(), row[1].strip()[:60]])
            if len(caps) >= 8:
                break
    formula = ''
    steps = re.findall(r'^步骤\s*\d*\s*[：:]\s*(.+)$', text, re.M)
    if not steps:
        steps = re.findall(r'^[一二三四五六七八九十]+、\s*(.{4,30})$', text, re.M)
    if steps:
        formula = ' → '.join(s.strip() for s in steps[:7])
    if not formula:
        mf = re.search(r'流程[：:]\s*(.+?)(?:\n|$)', text)
        if mf:
            formula = mf.group(1).strip()
    if not formula:
        formula = '输入 → 处理 → 输出 → 确权 → 归档 → 上报'
    source = fm.get('source', '')
    if not source:
        source = f"体系技能 {name}"
    return {
        "module_id": md_path.parent.name, "title": title,
        "category": "体系模块", "version": version, "source": source, "one_line": one_line,
        "abstract": abstract, "capabilities": caps, "formula": formula,
        "footnote": f"本白皮书由 AUTO-WP-FORGE 从 {md_path.name} 自动提炼生成",
    }

# ============ 批量模式（进化2：扫描技能目录批量成书） ============
SKIPPED_MODULES = {
    'truth-value-engine', 'causal-singularity-core', 'cte-link', 'drama-pipeline',
    'shield-pipeline', 'unified-orchestrator', 'knowledge-association-engine',
}

def seed_from_skills_root(skills_root: Path, st: dict) -> list:
    """扫描技能根目录,把未成书的 SKILL.md 注入种子目录,返回新种子名列表"""
    injected = []
    if not skills_root.exists():
        log(f"  ⚠️ 技能目录不存在: {skills_root}")
        return injected
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        sk = skill_dir / "SKILL.md"
        if not sk.exists():
            continue
        name = skill_dir.name
        if name in SKIPPED_MODULES or name in st["wp"]:
            continue
        seed_mod = SEED_DIR / f"wp-{name}"
        seed_mod.mkdir(parents=True, exist_ok=True)
        if not (seed_mod / "source.md").exists():
            import shutil
            shutil.copy2(sk, seed_mod / "source.md")
        injected.append(name)
        log(f"  📦 注入种子 {name}")
    return injected

# ============ 工具 ============
def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()

def sh(cmd: str, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"wp": {}, "last_root": ""}

def save_state(st):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=2))

def gateway_report(key, value, ctype='data', conf=0.97):
    body = json.dumps({"truth_key": key, "truth_value": value,
                       "source_node": NODE, "confidence": conf, "truth_type": ctype}).encode()
    req = urllib.request.Request(GATEWAY, data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return r.read().decode()[:60]
    except Exception as e:
        return f"ERR {e}"

# ============ 渲染 ============
def render_wp(meta: dict, filename: str, date: str) -> str:
    cap_rows = "\n".join(
        f"    <tr><td><b>{c[0]}</b></td><td>{c[1]}</td></tr>" for c in meta.get("capabilities", []))
    extra = ""
    if meta.get("extra_html"):
        extra = meta["extra_html"]
    return TEMPLATE.format(
        title=meta["title"], wpnum=meta["wpnum"], wpcat=meta.get("category", "技术"),
        version=meta.get("version", "V1.0"), date=date, did=DID, anchor=ANCHOR,
        source=meta.get("source", "体系"), abstract=meta.get("abstract", ""),
        one_line=meta.get("one_line", ""), cap_rows=cap_rows,
        formula=meta.get("formula", ""), footnote=meta.get("footnote", ""),
        extra=extra, node=NODE)

# ============ 主流程 ============
def main():
    log(f"AUTO-WP-FORGE 启动 | dry_run={DRY} force={FORCE}")
    if not SEED_DIR.exists():
        log(f"❌ 种子目录不存在: {SEED_DIR}")
        return 1

    date = time.strftime("%Y%m%d")
    st = load_state()

    # 0) 批量模式：先注入种子
    if BATCH:
        log(f"批量模式: 扫描 {BATCH}")
        seed_from_skills_root(BATCH, st)

    new_wp = []
    changed = []

    # 1) 扫描种子模块
    for mod in sorted(SEED_DIR.iterdir()):
        if not mod.is_dir():
            continue
        meta_f = mod / "meta.json"
        gen_f = mod / "meta.generated.json"
        if meta_f.exists():
            meta = json.loads(meta_f.read_text())
            meta_sha = sha256_file(meta_f)
        else:
            # 自动提炼：扫描素材文件（无需手写meta.json）
            src = None
            for cand in ("source.md", "SKILL.md", "README.md", "source.txt"):
                if (mod / cand).exists():
                    src = mod / cand
                    break
            if src is None:
                continue
            meta = extract_meta_from_md(src)
            meta["wpnum"] = next_wpnum(st)
            meta["module_id"] = mod.name
            # 写入供复核的生成元数据（不含wpnum，保证幂等键稳定）
            gen_meta = {k: v for k, v in meta.items() if k != "wpnum"}
            gen_f.write_text(json.dumps(gen_meta, ensure_ascii=False, indent=2), encoding='utf-8')
            meta_sha = sha256_file(gen_f)
            log(f"  🔍 自动提炼 {mod.name} → {meta['wpnum']} {meta['title']}")
        module_id = meta.get("module_id") or mod.name
        wpnum = meta.get("wpnum") or next_wpnum(st)
        filename = f"{module_id}.html"
        out_path = REPO_DIR / REPO_SUBDIR / filename

        # 幂等：已生成且未变更 → 跳过
        prev = st["wp"].get(module_id)
        if not FORCE and prev and prev["meta_sha"] == meta_sha and out_path.exists():
            continue

        html = render_wp(meta, filename, date)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding='utf-8')
        html_sha = sha256_file(out_path)

        # 确权凭证
        att = {"asset": filename, "sha256": html_sha, "did": DID, "anchor": ANCHOR,
               "source": f"wp-seed/{mod.name}", "producer": "AUTO-WP-FORGE", "date": date}
        att_path = out_path.parent / f"ATTESTATION-{filename}-{date}.json"
        att_path.write_text(json.dumps(att, ensure_ascii=False, indent=2), encoding='utf-8')

        record = {"meta_sha": meta_sha, "html_sha": html_sha, "wpnum": wpnum,
                  "title": meta["title"], "date": date, "attestation": att_path.name}
        if module_id in st["wp"]:
            changed.append(module_id)
        else:
            new_wp.append(module_id)
        st["wp"][module_id] = record
        log(f"  ✅ 生成 {wpnum} {meta['title']} sha={html_sha[:12]}")

    if not new_wp and not changed:
        log("  无新模块/无变更，幂等跳过")
    else:
        # 2) 批次确权（根哈希）
        files = sorted(p for p in (REPO_DIR / REPO_SUBDIR).glob("wp-*.html"))
        root_hash = hashlib.sha256(
            "|".join(f"{p.name}:{sha256_file(p)}" for p in files).encode()).hexdigest().upper()
        att_m = {"batch": f"WP-MATRIX-{date}", "count": len(files), "root_sha256": root_hash,
                 "did": DID, "anchor": ANCHOR, "files": [f.name for f in files]}
        (REPO_DIR / REPO_SUBDIR / f"ATTESTATION-MATRIX-{date}.json").write_text(
            json.dumps(att_m, ensure_ascii=False, indent=2), encoding='utf-8')
        st["last_root"] = root_hash
        save_state(st)
        log(f"  批次确权: {len(files)} 文件, 根哈希 {root_hash[:16]}")

        # 3) 更新矩阵 index.html 的统计（如存在：仅替换统计条数字）
        index_p = REPO_DIR / REPO_SUBDIR / "index.html"
        if index_p.exists():
            total = len(files)
            import re
            idx = index_p.read_text(encoding='utf-8')
            idx = re.sub(r'<b>(\d+)</b><span>已发布白皮书', f'<b>{total}</b><span>已发布白皮书', idx, count=1)
            index_p.write_text(idx, encoding='utf-8')
            log(f"  index统计更新: {total}")

        # 4) Git 推送（dry-run跳过）
        if not DRY:
            shutil_copy = f"cp {os.path.abspath(__file__)} {REPO_DIR}/scripts/auto_wp_forge.py"
            sh(shutil_copy)
            subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, capture_output=True, text=True)
            msg = f"publish(auto-forge): 新增{','.join(new_wp) or '无'} 变更{','.join(changed) or '无'} 根哈希{root_hash[:12]}"
            r = subprocess.run(["git", "-c", f"user.name={GIT_NAME}", "-c", f"user.email={GIT_EMAIL}",
                                "commit", "-m", msg], cwd=REPO_DIR, capture_output=True, text=True)
            if r.returncode == 0:
                out, err, rcp = sh("git push origin master", cwd=REPO_DIR)
                if rcp != 0:
                    log(f"  ⚠️ push 输出: {out} {err}")
                else:
                    log("  ✅ 已推送魔搭")
            else:
                log("  commit 无变更(或失败), 跳过推送")

        # 5) 上报网关（dry-run 不推送也不上报）
        if not DRY:
            for mid in new_wp:
                rec = st["wp"][mid]
                res = gateway_report(f"WHITEPAPER.{rec['wpnum']}.AUTO-FORGE.{date}",
                                     f"{rec['title']}白皮书由AUTO-WP-FORGE自动提炼生成,sha256={rec['html_sha'][:12]},确权{DID},已推送魔搭",
                                     ctype='data')
                log(f"  上报 {rec['wpnum']}: {res[:40]}")
            if new_wp:
                res = gateway_report(f"WHITEPAPER.MATRIX.AUTO-FORGE.BATCH.{date}",
                                     f"白皮书矩阵自动锻造批次完成:新增{len(new_wp)}变更{len(changed)},总{len(files)}份,根哈希{root_hash[:16]},全自动闭环",
                                     ctype='data')
                log(f"  批次上报: {res[:40]}")

    log("AUTO-WP-FORGE 完成")
    return 0

if __name__ == "__main__":
    sys.exit(main())
