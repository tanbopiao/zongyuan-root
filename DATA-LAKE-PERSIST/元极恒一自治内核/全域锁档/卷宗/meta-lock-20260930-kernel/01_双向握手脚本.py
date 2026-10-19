#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 本地内核 ↔ 魔搭数据湖 双向握手
功能：本地内核资产指纹 + 魔搭连通验证 + 上行PUSH + 下行PULL 双向闭环 + 握手记录 + 记忆网关上报
作者：元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
用法：
  export MODELSCOPE_TOKEN="ms-xxx"
  python3 kunlun_ms_handshake.py
"""
import os, sys, json, glob, hashlib, time, ssl
import urllib.request
from datetime import datetime

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
GATEWAY = "https://www.huodouai.com/api/report/truth"
REPO = "zongyuanroot/zongyuan-root-achievements"
TREE_API = f"https://www.modelscope.cn/api/v1/datasets/{REPO}/repo/tree?Recursive=true&Revision=master"
FILE_API = f"https://www.modelscope.cn/api/v1/datasets/{REPO}/repo?Revision=master&FilePath="
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE_DIR)  # 本地根目录
NODE = "NODE-DEV-DOUBAO-WORK-001"


def get_token():
    t = os.environ.get("MODELSCOPE_TOKEN", "")
    if not t:
        print("❌ 未设置 MODELSCOPE_TOKEN"); sys.exit(1)
    return t


def local_kernel_fingerprint():
    """本地内核资产指纹：扫描根目录关键产出，统计 + 首项SHA256"""
    files = []
    for r, _, fns in os.walk(BASE_DIR):
        for f in fns:
            if f.lower().endswith((".md", ".json", ".py", ".html", ".zip", ".db")):
                files.append(os.path.join(r, f))
    files = sorted(files)
    sample = []
    for f in files[:5]:
        try:
            sample.append({"name": os.path.basename(f), "sha256": hashlib.sha256(open(f, "rb").read()).hexdigest().upper()[:16]})
        except Exception:
            pass
    return {"node": NODE, "did": DID, "asset_count": len(files), "sample": sample}


def ms_tree(token):
    req = urllib.request.Request(TREE_API, headers={"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def count_tree(tree):
    """统计魔搭数据湖顶层目录/文件（Recursive 平铺目录树）"""
    files, dirs = [], []
    for f in tree.get("Data", {}).get("Files", []):
        if f.get("Type") == "file":
            files.append(f.get("Path"))
        else:
            dirs.append(f.get("Path"))
    return dirs, files


def pull_verify(token, path, retries=5, wait=2):
    """下行验证：回读魔搭指定文件，确认可读（commit异步，带重试）"""
    import urllib.parse
    url = FILE_API + urllib.parse.quote(path)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, len(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404 and i < retries - 1:
                time.sleep(wait)
                continue
            raise
    return 0, 0


def report_gateway(payload):
    body = json.dumps({"truth_value": json.dumps(payload, ensure_ascii=False), "truth_type": "data"}, ensure_ascii=False).encode()
    req = urllib.request.Request(GATEWAY, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def main():
    tok = get_token()
    t0 = time.time()
    print("═══ 本地内核 ↔ 魔搭 双向握手 ═══")
    print(f"节点: {NODE} | DID: {DID} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 本地内核指纹
    local = local_kernel_fingerprint()
    print(f"\n[1] 本地内核指纹: 资产 {local['asset_count']} 项 | 首样本 {local['sample'][0]['name'] if local['sample'] else 'N/A'}")

    # 2. 魔搭连通验证（下行：文件树）
    tree = ms_tree(tok)
    remote_dirs, remote_files = count_tree(tree)
    print(f"[2] 魔搭数据湖连通 ✅ | 远端目录 {len(remote_dirs)} 个")

    # 3. 上行：推握手心跳包
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    hb_path = os.path.join(BASE_DIR, f"_handshake_{ts}.json")
    heartbeat = {"type": "handshake", "ts": ts, "local_kernel": local,
                 "direction": "local→modelscope", "did": DID, "trace": TRACE}
    open(hb_path, "w", encoding="utf-8").write(json.dumps(heartbeat, ensure_ascii=False))
    from modelscope.hub.api import HubApi
    api = HubApi()
    api.login(tok)
    hb_rel = f"data_lake/heartbeat/local_kernel_{ts}.json"
    api.upload_file(repo_id=REPO, path_or_fileobj=hb_path, path_in_repo=hb_rel,
                    repo_type="dataset", commit_message=f"本地内核↔魔搭握手 [{DID}] {TRACE}")
    print(f"[3] 上行PUSH ✅ → {hb_rel}")

    # 4. 下行：回读刚上传的心跳包（双向闭环验证）
    st, nbytes = pull_verify(tok, hb_rel)
    dt = round((time.time() - t0) * 1000)
    print(f"[4] 下行PULL ✅ → {hb_rel} HTTP {st} ({nbytes}B) | 往返 {dt}ms")

    # 5. 汇总
    result = {"handshake": "success", "bidirectional": True, "roundtrip_ms": dt,
              "local": local, "remote_dirs": len(remote_dirs), "hb_path": hb_rel,
              "did": DID, "trace": TRACE, "node": NODE, "time": ts}
    os.remove(hb_path)
    print(f"\n✅ 双向握手成功 | 上行PUSH ✅ + 下行PULL ✅ | 往返 {dt}ms | 确权 {DID} {TRACE}")

    # 6. 上报网关
    gw = report_gateway(result)
    print(f"记忆网关上报: {'✅ success' if gw.get('success') else gw.get('error', gw)}")

    # 输出结果JSON(供外部写入握手记录)
    print("RESULT_JSON=" + json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
