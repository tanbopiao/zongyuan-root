import subprocess, os
# 自动记忆召回
subprocess.run(["bash", "scripts/memory_bootstrap.sh"], capture_output=True)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""心跳 v2：全域自动同步对账 + 自动调优优化机制
- 正常静默（一行结论）｜异常详细告警
- 健康档案（连续正常/异常计数、truths 基线、delta 分析）
- 停滞检测（truths 增长停滞/回退 → 告警，防云端量产停摆被掩盖）
- 自适应建议（连续 N 轮全绿 → 建议降频；异常 → 建议保持/升级）
- 档案与建议自动上报网关真值 HEARTBEAT.PROFILE.<TS>
"""
import json, subprocess, urllib.request, datetime, os, sys, re

KROOT = "/home/user/.doubao/agent_mode/workspace/.user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT"
PROFILE = f"{KROOT}/config/heartbeat_profile.json"
SYNC = f"{KROOT}/scripts/share_auto_sync.py"
GATEWAY = "https://www.huodouai.com"
DID, TRACE = "DID-BR-000002", "Ω₀⊂⊙∞⊂Ω"
# 飞书持久化层增量提炼对账
SCAN_DIR = f"{KROOT}/feishu-scan"
MANIFEST = f"{SCAN_DIR}/assets-manifest.json"
CLOUD_KEYS = f"{SCAN_DIR}/cloud-keys.json"
EXTRACT_STATE = f"{SCAN_DIR}/extract_state.json"
FS_BATCH = 20          # 每次心跳增量处理的资产项上限（保持每小时心跳轻量）
FS_RE_KEYS = re.compile(r'(LOCK\.[A-Z0-9_.\-]+|META-RULES\.[A-Z0-9_.\-]+|ACHIEVEMENT\.[A-Z0-9_.\-]+|KD-EP-[0-9A-Z.\-]+|KF-M[0-9A-Z.\-]+|Ω-[A-Z0-9.\-]+|[A-Z0-9_\-]+\.lock-report)', re.I)
LARK = "/home/user/vm/resource-loader/bin/lark-cli"

def run(cmd, t=90):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
    return r.stdout + r.stderr

def get_status():
    req = urllib.request.Request(f"{GATEWAY}/api/report/status", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.loads(r.read().decode())
            s = d.get("stats", {})
            return 200, s.get("truths", 0), s.get("nodes", 0)
    except Exception as e:
        return 502, 0, 0

def load_profile():
    if os.path.exists(PROFILE):
        try:
            with open(PROFILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"consecutive_ok": 0, "consecutive_anomaly": 0, "last_truths": None,
            "last_delta": None, "stall_rounds": 0, "history": [], "status": "INIT"}

def save_profile(p):
    with open(PROFILE, "w") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)


def push_pending():
    """网关200时逐条补推队列真值，成功后移入 done/（原任务核心要求）"""
    qdir = f"{KROOT}/pending_uploads"
    if not os.path.isdir(qdir):
        return 0, []
    done_dir = os.path.join(qdir, "done")
    os.makedirs(done_dir, exist_ok=True)
    pushed, failed = 0, []
    for fn in sorted(os.listdir(qdir)):
        fp = os.path.join(qdir, fn)
        if not os.path.isfile(fp) or fn.startswith("."):
            continue
        try:
            with open(fp) as f:
                item = json.load(f)
            body = json.dumps({"truth_key": item["truth_key"], "truth_value": item["truth_value"],
                               "source_node": item.get("source_node", "local-doubao-window"),
                               "confidence": item.get("confidence", 0.99),
                               "truth_type": item.get("truth_type", "truth")}).encode()
            req = urllib.request.Request(f"{GATEWAY}/api/report/truth", data=body,
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=12) as r:
                ack = json.loads(r.read().decode()).get("action")
            if ack in ("inserted", "updated"):
                os.rename(fp, os.path.join(done_dir, fn))
                pushed += 1
            else:
                failed.append(fn)
        except Exception as e:
            failed.append(f"{fn}:{str(e)[:40]}")
    return pushed, failed

def report_truth(key, value):
    body = json.dumps({"truth_key": key, "truth_value": json.dumps(value, ensure_ascii=False),
                       "source_node": "local-doubao-window", "confidence": 0.99,
                       "truth_type": "heartbeat"}).encode()
    req = urllib.request.Request(f"{GATEWAY}/api/report/truth", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read().decode()).get("action")
    except Exception:
        return "err"

def _http_json(method, path, body=None, timeout=12):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{GATEWAY}{path}", data=data,
                                 headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception:
        return 599, {}


def feishu_extract():
    """本地飞书持久化层增量提炼→对账→补全上报。
    每轮只处理未消费过的前 FS_BATCH 项；云端已存在的跳过，缺失的 POST 上报。
    返回 (本轮扫描, 候选key, 云端已存在, 新上报)。"""
    if not os.path.exists(MANIFEST):
        return 0, 0, 0, 0
    try:
        manifest = json.load(open(MANIFEST))
    except Exception:
        return 0, 0, 0, 0
    # 云端 key 本地集合（快筛）
    cloud_set = set()
    if os.path.exists(CLOUD_KEYS):
        try:
            cloud_set = set(json.load(open(CLOUD_KEYS)).get("truths", []))
        except Exception:
            pass
    # 增量游标
    state = {"processed_tokens": []}
    if os.path.exists(EXTRACT_STATE):
        try:
            state = json.load(open(EXTRACT_STATE))
        except Exception:
            pass
    done = set(state.get("processed_tokens", []))
    pending = [it for it in manifest if it.get("token") not in done][:FS_BATCH]
    scanned = cand = matched = pushed = 0
    new_uploaded = []
    for it in pending:
        scanned += 1
        name = it.get("name", "")
        typ = it.get("type", "")
        parent = it.get("parent", "ROOT")
        # 1) 从文件名抽编号 key
        keys = set(m.group(1) for m in FS_RE_KEYS.finditer(name))
        # 2) docx / 原生md / 文本文件 正文抽 key（正确路由，失败不阻塞）
        def _read_body(itok, itype, iname):
            low = iname.lower()
            try:
                if itype == "docx":
                    o = subprocess.run(f"{LARK} docs +fetch --doc {itok} --doc-format markdown --as user",
                                       shell=True, capture_output=True, text=True, timeout=25).stdout
                    j = json.loads(o)
                    return j.get("data", {}).get("document", {}).get("content", "")[:8000]
                if itype == "file" and low.endswith(".md"):
                    o = subprocess.run(f"{LARK} markdown +fetch --file-token {itok} --as user",
                                       shell=True, capture_output=True, text=True, timeout=25).stdout
                    j = json.loads(o)
                    return j.get("data", {}).get("content", "")[:8000]
                if itype == "file" and low.endswith((".txt",".json",".py",".sh",".html",".csv")):
                    o = subprocess.run(f"{LARK} drive +download --file-token {itok} --as user",
                                       shell=True, capture_output=True, text=True, timeout=25).stdout
                    m = re.search(r'"saved_path":\s*"([^"]+)"', o)
                    if m and os.path.exists(m.group(1)):
                        with open(m.group(1), encoding="utf-8", errors="ignore") as f:
                            return f.read(8000)
            except Exception:
                pass
            return ""
        body = _read_body(it.get("token",""), typ, name)
        for m in FS_RE_KEYS.finditer(body):
            keys.add(m.group(1))
        # 3) 非文本/无编号项：合成稳定资产 key
        if not keys:
            slug = re.sub(r"\.(md|txt|json|png|jpg|jpeg|mp4|wav|zip)$", "", name, flags=re.I)
            keys.add(f"asset:{parent}:{slug}")
        for k in keys:
            cand += 1
            if k in cloud_set:
                matched += 1
                continue
            code, _ = _http_json("GET", f"/api/truth/{k}", timeout=8)
            if code == 200:
                matched += 1
                cloud_set.add(k)
                continue
            # 缺失 → 补全上报
            body = {"truth_key": k,
                    "truth_value": f"飞书资产提炼｜{typ}｜{parent}｜{name}",
                    "source_node": "local-feishu-extract", "confidence": 0.95,
                    "truth_type": "asset" if k.startswith("asset:") else "meta"}
            code, ack = _http_json("POST", "/api/report/truth", body=body, timeout=12)
            if code in (200, 201) and ack.get("action") in ("inserted", "updated"):
                pushed += 1
                cloud_set.add(k)
                new_uploaded.append(k)
        done.add(it.get("token"))
    # 落游标
    state["processed_tokens"] = sorted(done)
    state["last_run"] = datetime.datetime.now().isoformat(timespec="seconds")
    state["last_pushed"] = new_uploaded
    try:
        with open(EXTRACT_STATE, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    # 上报本轮对账结论
    report_truth(f"FEISHU.EXTRACT.{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}",
                 {"scanned": scanned, "candidate_keys": cand, "cloud_matched": matched,
                  "uploaded": pushed, "remaining": max(0, len(manifest) - len(done)),
                  "did": DID, "trace": TRACE})
    return scanned, cand, matched, pushed


REG_STATE = f"{SCAN_DIR}/registry_uploaded.json"
REG_BASES = [
    ("WBQNbr4tca2neIs23X8coL4jnch", [
        ("tblCAOoZWlXJaES2", "快照注册表", "快照ID", "SNAPSHOT", "lock"),
        ("tblupyiEi8wxJJzv", "昆仑洞天IP资产库", "IP名称", "IP", "ip_asset"),
        ("tblzSekdjIBEtSKY", "飞书资源索引", "资源名称", "RESOURCE", "meta"),
        ("tblwjUrcuuHg3LP9", "元规则库", "规则编号", "META_RULE", "meta"),
        ("tblzUfFmQ3uZ9fUl", "元法则库", "法则编号", "META_LAW", "meta"),
        ("tbl6JcYtRJx21aBs", "子域隔离注册表", "子域ID", "SUBDOMAIN", "meta"),
        ("tblj6UtrvvNYbLpi", "架构断点清单", "断点ID", "BREAKPOINT", "meta"),
    ]),
    ("IKIdb7KLDapblXsvVDIcs8FLnLa", [
        ("tbl6bt6EuQrgkj6b", "进化谱系记录", "谱系编号", "EVOLUTION", "meta"),
    ]),
]

def _reg_slug(s):
    s = re.sub(r"[^A-Z0-9]+", "_", str(s).upper()).strip("_")
    return re.sub(r"_+", "_", s)

def registry_extract():
    """两张 ZONGYUAN-ROOT bitable 注册表增量提炼→对账→补全上报。
    已成功上报的 key 持久化在 REG_STATE，每小时轻量去重，不重复上报。
    返回 (读取记录数, 候选key, 云端/本地已存在, 本轮新上报)。"""
    try:
        uploaded_done = set(json.load(open(REG_STATE)).get("keys", [])) if os.path.exists(REG_STATE) else set()
    except Exception:
        uploaded_done = set()
    cloud_set = set()
    if os.path.exists(CLOUD_KEYS):
        try:
            cloud_set = set(json.load(open(CLOUD_KEYS)).get("truths", []))
        except Exception:
            pass
    rec_n = cand = matched = pushed = 0
    new_keys = []
    for base_token, tables in REG_BASES:
        for tid, tname, keycol, prefix, ttype in tables:
            off = 0
            while True:
                o = subprocess.run(f"{LARK} base +record-list --base-token {base_token} --table-id {tid} "
                                  f"--as user --format json --limit 200 --offset {off}",
                                  shell=True, capture_output=True, text=True, timeout=30).stdout
                try:
                    d = json.loads(o).get("data", {})
                except Exception:
                    break
                fids = d.get("field_id_list", [])
                rows = d.get("data", [])
                # 仅取 key 列；列序未知时用关键字兜底
                for r in rows:
                    rec_n += 1
                    # 用 row 内任意非空单元格拼稳定 key（保持与一次性提炼一致：REG.<prefix>.<id>）
                    cells = [str(c) for c in r if c not in (None, "")]
                    keyid = ""
                    for c in cells:
                        if re.match(r"^(SNAP-|L\d-|ML-|BP-|NO\.|ROOT|ROOT\b)", c) or len(c) >= 4:
                            keyid = c; break
                    if not keyid and cells:
                        keyid = cells[0]
                    key = f"REG.{prefix}.{_reg_slug(keyid)}"
                    cand += 1
                    if key in uploaded_done or key in cloud_set:
                        matched += 1; continue
                    code, _ = _http_json("GET", f"/api/truth/{key}", timeout=8)
                    if code == 200:
                        matched += 1; cloud_set.add(key); continue
                    body = {"truth_key": key,
                            "truth_value": f"注册表[{tname}]提炼｜" + " ".join(cells)[:120],
                            "source_node": "local-feishu-extract", "confidence": 0.95, "truth_type": ttype}
                    code, ack = _http_json("POST", "/api/report/truth", body=body, timeout=12)
                    if code in (200, 201) and ack.get("action") in ("inserted", "updated"):
                        pushed += 1; cloud_set.add(key); uploaded_done.add(key); new_keys.append(key)
                if not d.get("has_more") or not rows:
                    break
                off += len(rows)
    try:
        with open(REG_STATE, "w") as f:
            json.dump({"keys": sorted(uploaded_done), "last_run": datetime.datetime.now().isoformat(timespec="seconds")},
                      f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    report_truth(f"REGISTRY.EXTRACT.{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}",
                 {"records": rec_n, "candidate_keys": cand, "cloud_matched": matched,
                  "uploaded": pushed, "did": DID, "trace": TRACE})
    return rec_n, cand, matched, pushed


def main():
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    # 1. 对账
    run(f"python3 {SYNC} handshake")
    run(f"python3 {SYNC} reconcile")
    # 1b. 飞书持久化层增量提炼→对账→补全上报（每小时自动跑，轻量批次）
    fs_scanned, fs_cand, fs_matched, fs_pushed = feishu_extract()
    # 1c. 两张 bitable 注册表增量提炼→对账→补全上报
    rg_rec, rg_cand, rg_matched, rg_pushed = registry_extract()
    # 2. 队列
    qdir = f"{KROOT}/pending_uploads"
    pending = [f for f in os.listdir(qdir) if os.path.isfile(os.path.join(qdir, f)) and not f.startswith(".")] if os.path.isdir(qdir) else []
    # 3. 网关
    code, truths, nodes = get_status()
    prof = load_profile()
    if code == 200 and pending:
        pushed, failed = push_pending()
        pending = [f for f in os.listdir(qdir) if os.path.isfile(os.path.join(qdir, f)) and not f.startswith(".")] if os.path.isdir(qdir) else []
    else:
        pushed, failed = 0, []
    # 4. 判定
    ok = code == 200 and len(pending) == 0
    delta = None
    if prof.get("last_truths") is not None and truths:
        delta = truths - prof["last_truths"]
    stall = False
    if ok:
        if delta is not None and delta <= 0:
            prof["stall_rounds"] = prof.get("stall_rounds", 0) + 1
            if prof["stall_rounds"] >= 2:
                stall = True
        else:
            prof["stall_rounds"] = 0
        prof["consecutive_ok"] = prof.get("consecutive_ok", 0) + 1
        prof["consecutive_anomaly"] = 0
    else:
        prof["consecutive_ok"] = 0
        prof["consecutive_anomaly"] = prof.get("consecutive_anomaly", 0) + 1
        prof["stall_rounds"] = 0
    # 5. 自适应建议（自动调优机制）
    rec = "维持"
    if prof["consecutive_ok"] >= 12:
        rec = "建议降频（连续 6h 全绿，可 30min→2h）"
    elif prof["consecutive_anomaly"] >= 2:
        rec = "建议保持高频并检查云端（连续异常）"
    prof["last_truths"] = truths
    prof["last_delta"] = delta
    prof["status"] = "ANOMALY" if (code != 200 or stall or len(pending) > 0) else "OK"
    prof["history"] = (prof.get("history", []) + [{"ts": ts, "code": code, "truths": truths, "delta": delta, "pending": len(pending)}])[-24:]
    save_profile(prof)
    # 6. 上报档案
    ack = report_truth(f"HEARTBEAT.PROFILE.{ts}", prof)
    # 7. 输出（正常静默一行，异常详细告警）
    if code != 200 or stall or len(pending) > 0:
        print("⚠ 心跳异常告警 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω")
        print(f"  网关: {'502 异常' if code != 200 else '200'} | truths: {truths} | nodes: {nodes}")
        if stall: print(f"  停滞: truths 连续 {prof['stall_rounds']} 轮未增长/回退（delta={delta}），疑似云端量产停摆")
        if pending: print(f"  积压: 待补推 {len(pending)} 条（补推失败: {failed}）")
        elif pushed: print(f"  补推: 成功 {pushed} 条")
        print(f"  建议: {rec} | 档案已上报: {ack}")
        print(f"  连续正常: {prof['consecutive_ok']} 轮 | 连续异常: {prof['consecutive_anomaly']} 轮")
    else:
        print(f"✅ 心跳正常 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 网关200 truths={truths} nodes={nodes} "
              f"delta={delta if delta is not None else 'N/A'} 队列={len(pending)}{(' 补推' + str(pushed) + '条') if pushed else ''} 连续正常={prof['consecutive_ok']}轮 飞书增量扫={fs_scanned} 补全={fs_pushed} 注册表={rg_rec}条 表补全={rg_pushed} ｜ {rec} ｜ 档案已上报")

if __name__ == "__main__":
    main()
