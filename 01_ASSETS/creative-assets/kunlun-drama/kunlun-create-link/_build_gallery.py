#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

BASE = "/home/user/Doubao/chats/1128121028098/kunlun-create-link"
MANIFEST = BASE + "/pipeline_reports/final_frames_manifest_20260929.json"
VERIFY = BASE + "/pipeline_reports/gallery_url_verify_20260929.json"
TEMPLATE = BASE + "/关键帧画廊_模板.html"
OUT = BASE + "/昆仑洞天作品关键帧画廊.html"

manifest = json.load(open(MANIFEST, encoding="utf-8"))
verify = json.load(open(VERIFY, encoding="utf-8"))
passed_urls = {r["url"] for r in verify["results"] if r["ok"]}

frames = []
for it in manifest:
    if it["url"] not in passed_urls:
        continue
    frames.append({
        "name": it["name"],
        "path": it["rel"],
        "url": it["url"],
        "theme": it.get("theme", ""),
    })

print("frames to inject:", len(frames))

tpl = open(TEMPLATE, encoding="utf-8").read()

# 1) inject FRAMES json
frames_json = json.dumps(frames, ensure_ascii=False)
tpl = tpl.replace("var FRAMES = __FRAMES_JSON__;", "var FRAMES = " + frames_json + ";")

# 2) extend THEME map (fallback path-based mapping)
old_theme_block = '''var THEME = {
  "01-jiutian_xuannv_20260929":"九天玄女",
  "03-archive_ep01_03_xuannv":"九天玄女·横版",
  "07-xuannv_works":"九天玄女",
  "jiutian_xuannv-20260929":"九天玄女·三型",
  "02-kunlun_dongtian":"昆仑洞天·太阴/角色",
  "04-archive_zhulong_duizhi":"玄女×烛龙",
  "05-archive_kunlun_assets_shennv":"神女·创世",
  "08-taiyin_moon":"太阴月神"
};'''
new_theme_block = '''var THEME = {
  "jiutian_xuannv-20260929":"九天玄女·三型",
  "02-kunlun_dongtian":"昆仑洞天·太阴/角色",
  "03-archive_ep01_03_xuannv":"九天玄女·横版",
  "04-archive_zhulong_duizhi":"玄女×烛龙",
  "05-archive_kunlun_assets_shennv":"神女·创世",
  "07-xuannv_works":"九天玄女",
  "xn_webp":"九天玄女·战斗帧",
  "keyframe_kf003_010_20260913":"玄女×烛龙·幽墟裂隙",
  "keyframe_lock_20260913":"玄女×烛龙·幽墟裂隙",
  "archive_kunlun-20260913":"玄女×烛龙·幽墟裂隙",
  "01-jiutian_xuannv_20260929":"九天玄女",
  "08-taiyin_moon":"太阴月神"
};'''
assert old_theme_block in tpl, "THEME block not found"
tpl = tpl.replace(old_theme_block, new_theme_block)

# 3) make init() prefer manifest-provided theme, fall back to themeOf(path)
old_init = "FRAMES.forEach(function(it){it.theme=themeOf(it.path);});"
new_init = "FRAMES.forEach(function(it){if(!it.theme){it.theme=themeOf(it.path);}});"
assert old_init in tpl, "init line not found"
tpl = tpl.replace(old_init, new_init)

open(OUT, "w", encoding="utf-8").write(tpl)
print("written:", OUT, len(tpl), "bytes")
