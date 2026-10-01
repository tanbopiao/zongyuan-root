#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT → 魔搭 媒体资产限流感知分批上传器 v1.0
确权 DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

解决魔搭 /files/upload 限流（实测：5s 间隔第 3 次触发 429）：
- 单次间隔 10s（安全窗口）
- 每 8 次长冷却 60s（窗口重置）
- 每轮上限 MAX_PER_ROUND=25 次（风控保护，余量留到下一轮）
- 断点续传：按 sha256 记录已上传 file_id，失败/未传完的下轮继续
- 幂等：已上传文件自动跳过
"""
import os, sys, json, time, hashlib, urllib.request, urllib.error
from pathlib import Path

KROOT = Path("/home/user/Doubao/chats/38439570362876674/ZONGYUAN-ROOT")
TOKEN_FILE = KROOT / "config" / "modelscope_token"
STATE_FILE = KROOT / "config" / "ms_upload_state.json"
UPLOAD_URL = "https://modelscope.cn/openapi/v1/files/upload"

INTERVAL = 10          # 单次间隔（秒）
COOLDOWN_EVERY = 8     # 每 N 次长冷却
COOLDOWN = 60          # 长冷却秒数
MAX_PER_ROUND = 25     # 每轮上限

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
    return {"uploaded": {}, "round": 0}

def save_state(st):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=2))

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def upload_one(path, remote_path, token):
    """multipart 上传，返回 (ok, file_id)"""
    import subprocess
    r = subprocess.run(
        ["curl", "-s", "--max-time", "30", "-X", "POST",
         "-H", f"Authorization: Bearer {token}",
         "-F", f"file=@{path}", "-F", f"filename={remote_path}",
         UPLOAD_URL],
        capture_output=True, text=True, timeout=60)
    try:
        d = json.loads(r.stdout)
        if d.get("success") and d.get("data", {}).get("id"):
            return True, d["data"]["id"]
        msg = d.get("message", r.stdout[:100])
        if "Too Many" in msg or d.get("code") == 429:
            return "rate", msg
        return False, msg
    except Exception:
        return False, r.stdout[:100]

def collect_images():
    """收集待上传图片：(path, remote_path)"""
    base = KROOT / "media-library" / "images"
    items = []
    for f in sorted(base.rglob("*.png")):
        rel = f.relative_to(base).as_posix()
        remote = f"media/{rel}"
        items.append((f, remote))
    return items

def main():
    token = get_token()
    st = load_state()
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    items = collect_images()
    todo = []
    for path, remote in items:
        h = sha256_of(path)
        if h in st["uploaded"]:
            continue  # 已上传，跳过
        todo.append((path, remote, h))
    log(f"=== 限流感知分批上传 {mode} ===")
    log(f"图片总数: {len(items)} | 已上传: {len(st['uploaded'])} | 待传: {len(todo)} | 本轮上限: {MAX_PER_ROUND}")
    if mode == "dry-run":
        log(f"[dry-run] 本轮将处理 {min(len(todo), MAX_PER_ROUND)} 个文件")
        return
    done, rate_hits, fail = 0, 0, []
    for idx, (path, remote, h) in enumerate(todo[:MAX_PER_ROUND], 1):
        ok, fid = upload_one(path, remote, token)
        if ok is True:
            st["uploaded"][h] = {"file_id": fid, "remote": remote, "ts": time.time()}
            done += 1
            log(f"  ✅ [{idx}/{MAX_PER_ROUND}] {remote} → {fid[:8]}…")
        elif ok == "rate":
            rate_hits += 1
            log(f"  ⏸ [{idx}] 限流触发，本轮暂停（{remote}）")
            break
        else:
            fail.append(remote)
            log(f"  ❌ [{idx}] {remote}: {str(fid)[:60]}")
        # 节奏控制
        if idx < MAX_PER_ROUND and idx % COOLDOWN_EVERY == 0:
            log(f"  ⏳ 长冷却 {COOLDOWN}s（窗口重置）")
            time.sleep(COOLDOWN)
        else:
            time.sleep(INTERVAL)
    save_state(st)
    log(f"=== 本轮完成: 成功 {done} | 限流中止 {rate_hits} | 失败 {len(fail)} | 累计已传 {len(st['uploaded'])} ===")

if __name__ == "__main__":
    main()
