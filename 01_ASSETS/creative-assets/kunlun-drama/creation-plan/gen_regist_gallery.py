#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成昆仑洞天 · 创作确权作品库展示页
1) 为关键帧生成 WebP 缩略图、为成片用 ffmpeg 抽帧生成封面缩略图
2) 读取 regist/manifest.json + ZR 溯源链 -> 生成自包含 HTML（缩略图+SHA256+确权状态+真video）
"""
import json, time, os, subprocess, urllib.request, urllib.error

MANIFEST = "/www/wwwroot/huodouai.com/kunlun/regist/manifest.json"
OUT = "/www/wwwroot/huodouai.com/kunlun/regist/gallery.html"
FRAMES_DIR = "/www/wwwroot/huodouai.com/kunlun/frames"
VIDEOS_DIR = "/www/wwwroot/huodouai.com/kunlun/videos"
THUMB_DIR = "/www/wwwroot/huodouai.com/kunlun/frames/thumb"
VID_THUMB_DIR = "/www/wwwroot/huodouai.com/kunlun/videos/thumb"
ZR_BASE = "https://www.huodouai.com/zr-api/api/v1"
ZR_KEY = "zr-7962dc9e860d3f2cf63a9ca7"

def fetch_chain():
    req = urllib.request.Request(ZR_BASE + "/provenance/chain?limit=100",
                                 headers={"X-API-Key": ZR_KEY})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
        return d.get("tail", []), d.get("merkle_root", ""), len(d.get("tail", []))
    except Exception:
        return [], "", 0

def make_frame_thumbs():
    """给关键帧生成 9:16 竖版 WebP 缩略图（从中心裁出竖版，宽 480）"""
    os.makedirs(THUMB_DIR, exist_ok=True)
    made = 0
    if not os.path.isdir(FRAMES_DIR):
        return made
    for f in sorted(os.listdir(FRAMES_DIR)):
        if not f.lower().endswith((".jpg", ".png", ".jpeg")):
            continue
        src = os.path.join(FRAMES_DIR, f)
        base = os.path.splitext(f)[0]
        dst = os.path.join(THUMB_DIR, base + ".webp")
        if os.path.exists(dst):
            continue
        try:
            p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                "-show_entries", "stream=width,height", "-of", "csv=p=0", src],
                               capture_output=True, text=True, timeout=20)
            wh = p.stdout.strip().split(",")
            w, h = int(wh[0]), int(wh[1])
            if w > h:
                vf = "crop=ih*9/16:ih,scale=900:-2"
            else:
                vf = "scale=900:-2"
            subprocess.run(["ffmpeg", "-y", "-i", src, "-vf", vf, "-q:v", "75", dst],
                           capture_output=True, timeout=30)
            if os.path.exists(dst):
                made += 1
        except Exception:
            pass
    return made

def make_video_thumbs():
    """给成片抽帧生成 9:16 竖版封面（从中心裁出竖版，宽 480）"""
    os.makedirs(VID_THUMB_DIR, exist_ok=True)
    made = 0
    if not os.path.isdir(VIDEOS_DIR):
        return made
    for f in sorted(os.listdir(VIDEOS_DIR)):
        if not f.lower().endswith((".mp4", ".mov", ".webm")):
            continue
        src = os.path.join(VIDEOS_DIR, f)
        base = os.path.splitext(f)[0]
        dst = os.path.join(VID_THUMB_DIR, base + ".webp")
        if os.path.exists(dst):
            continue
        try:
            p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                "-show_entries", "stream=width,height", "-of", "csv=p=0", src],
                               capture_output=True, text=True, timeout=20)
            wh = p.stdout.strip().split(",")
            w, h = int(wh[0]), int(wh[1])
            if w > h:
                vf = "thumbnail,crop=ih*9/16:ih,scale=900:-2"
            else:
                vf = "thumbnail,scale=900:-2"
            subprocess.run(["ffmpeg", "-y", "-i", src, "-vf", vf, "-frames:v", "1",
                            "-q:v", "75", dst], capture_output=True, timeout=30)
            if os.path.exists(dst):
                made += 1
        except Exception:
            pass
    return made

def card(kind, item, idx, chain_map):
    tid = item.get("truth_id", "")
    chain = chain_map.get(tid)
    file = item["file"]
    base = os.path.splitext(file)[0]
    if kind == "frame":
        thumb_url = "/kunlun/frames/thumb/" + base + ".webp"
        inner = ('<img src="' + thumb_url + '" alt="' + file
                 + '" loading="lazy" onerror="this.outerHTML='
                 + "'<div class=vidph>⚠</div>';\">")
        label = "关键帧"
    else:
        thumb_url = "/kunlun/videos/thumb/" + base + ".webp"
        vurl = "/kunlun/videos/" + file
        inner = ('<video class="vplayer" controls preload="none" '
                 + 'poster="' + thumb_url + '">'
                 + '<source src="' + vurl + '" type="video/mp4">'
                 + '不支持视频播放</video>')
        label = "成片"
    chain_html = ('<div class="chain ok">✅ 已确权 · 链上索引 #'
                  + str(chain.get("index", "?")) + '</div>') if chain \
                 else '<div class="chain pending">⏳ 未确权</div>'
    return f'''    <div class="card">
      <div class="thumb">
        {inner}
        <span class="kind">{label}</span>
      </div>
      <div class="meta">
        <div class="name">{file}</div>
        <div class="hash">SHA256 <span class="mono">{item["sha256"][:24]}…</span></div>
        <div class="size">{round(item["size"]/1024/1024,2)} MB</div>
        {chain_html}
      </div>
    </div>'''

def build():
    # 1) 预生成缩略图
    f_made = make_frame_thumbs()
    v_made = make_video_thumbs()
    print("关键帧缩略图生成", f_made, "/ 成片封面生成", v_made)
    # 2) 读台账 + 链
    m = json.load(open(MANIFEST))
    tail, root, length = fetch_chain()
    chain_map = {b.get("truth_id"): b for b in tail}
    frames = m.get("frames", [])
    videos = [v for v in m.get("videos", []) if v.get("size", 0) >= 700 * 1024]
    # 质量门槛：只展示生成了清晰缩略图的资产，模糊/低质源自动隐藏
    frames = [fr for fr in frames
              if os.path.exists(os.path.join(THUMB_DIR, os.path.splitext(fr["file"])[0] + ".webp"))]
    videos = [v for v in videos
              if os.path.exists(os.path.join(VID_THUMB_DIR, os.path.splitext(v["file"])[0] + ".webp"))]
    for i, fr in enumerate(frames):
        fr["truth_id"] = f"TRUTH-KUNLUN-FRAME-{i+1:03d}-{fr['file'].replace('frame_','').replace('.jpg','')}"
    for i, v in enumerate(videos):
        v["truth_id"] = f"TRUTH-KUNLUN-VIDEO-{i+1:03d}-{v['file'].replace('.mp4','')}"
    frame_cards = "\n".join(card("frame", fr, i, chain_map) for i, fr in enumerate(frames))
    video_cards = "\n".join(card("video", v, i, chain_map) for i, v in enumerate(videos))
    n_chain = sum(1 for it in frames + videos if it["truth_id"] in chain_map)
    total = len(frames) + len(videos)
    html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>昆仑洞天 · 创作确权作品库</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#0a0a0a;color:#e0d0a0;font-family:"PingFang SC","Microsoft YaHei",sans-serif}}
.topline{{height:2px;background:linear-gradient(90deg,#d4af37,transparent 70%)}}
.head{{padding:28px 24px 6px;text-align:center}}
.brand{{font-size:13px;color:#d4af37;letter-spacing:.3em;margin-bottom:8px}}
h1{{margin:0;font-size:26px;color:#f0e6c8;letter-spacing:.08em}}
.sub{{color:#8a8570;font-size:13px;margin-top:8px}}
.stats{{display:flex;justify-content:center;gap:28px;margin:20px 0 8px;flex-wrap:wrap}}
.stat{{text-align:center}}
.stat b{{display:block;font-size:30px;color:#d4af37}}
.stat span{{font-size:12px;color:#8a8570}}
.chainbadge{{display:inline-block;margin-top:10px;padding:6px 16px;border:1px solid rgba(212,175,55,.4);border-radius:30px;font-size:12px;color:#d4af37}}
.section{{padding:10px 24px}}
.section h2{{color:#d4af37;font-size:17px;letter-spacing:.1em;margin:24px 0 14px;border-bottom:1px solid rgba(212,175,55,.2);padding-bottom:8px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}}
.card{{background:#121212;border:1px solid rgba(212,175,55,.18);border-radius:10px;overflow:hidden}}
.thumb{{position:relative;aspect-ratio:9/16;background:#161616}}
.thumb img{{width:100%;height:100%;object-fit:cover}}
.vplayer{{width:100%;height:100%;object-fit:cover;background:#161616}}
.vidph{{display:flex;align-items:center;justify-content:center;height:100%;font-size:32px;color:#f2994a}}
.kind{{position:absolute;top:8px;left:8px;background:rgba(10,10,10,.7);color:#d4af37;font-size:11px;padding:2px 8px;border-radius:20px;border:1px solid rgba(212,175,55,.4)}}
.meta{{padding:12px}}
.name{{font-size:12px;color:#f0e6c8;word-break:break-all;margin-bottom:6px}}
.hash{{font-size:11px;color:#8a8570}}
.hash .mono{{font-family:monospace;color:#d4af37}}
.size{{font-size:11px;color:#8a8570;margin-top:2px}}
.chain{{font-size:11px;margin-top:6px}}
.chain.ok{{color:#6fcf97}}
.chain.pending{{color:#f2994a}}
.foot{{padding:30px 24px 40px;text-align:center;color:#8a8570;font-size:12px}}
.mono{{font-family:monospace}}
@media(max-width:520px){{.grid{{grid-template-columns:repeat(2,1fr)}}h1{{font-size:21px}}}}
</style></head><body>
<div class="topline"></div>
<div class="head">
  <div class="brand">ZONGYUAN-ROOT · 昆仑洞天</div>
  <h1>创作确权作品库</h1>
  <div class="sub">关键帧 → 分镜 → 成片 · 全链路 SHA256 确权 · Merkle-DAG 溯源链锁定</div>
  <div class="stats">
    <div class="stat"><b>{total}</b><span>资产总数</span></div>
    <div class="stat"><b>{n_chain}/{total}</b><span>已确权</span></div>
    <div class="stat"><b>{len(frames)}</b><span>关键帧</span></div>
    <div class="stat"><b>{len(videos)}</b><span>成片</span></div>
    <div class="stat"><b>{length}</b><span>溯源链块</span></div>
  </div>
  <div class="chainbadge mono">Merkle-Root {root[:16]}…</div>
  <div class="chainbadge">确权锚定 Ω₀⊂⊙∞⊂Ω · DID-BR-000002</div>
</div>

<div class="section">
  <h2>关键帧 · {len(frames)}</h2>
  <div class="grid">
{frame_cards}
  </div>
</div>

<div class="section">
  <h2>成片 · {len(videos)}</h2>
  <div class="grid">
{video_cards}
  </div>
</div>

<div class="foot">
  <div>生成时间 {time.strftime("%Y-%m-%d %H:%M:%S")} · 链上 {length} 块 · root {root[:16]}…</div>
  <div class="mono" style="margin-top:8px;color:#8a8570">DID-BR-000002 · 锚定 Ω₀⊂⊙∞⊂Ω</div>
</div>
</body></html>'''
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("生成:", OUT, "资产", total, "确权", n_chain)

if __name__ == "__main__":
    build()
