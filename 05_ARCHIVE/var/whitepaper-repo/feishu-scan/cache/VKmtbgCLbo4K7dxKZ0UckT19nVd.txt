# 快速对话视频下载归档 SOP V1.0｜QUICKCHAT-VIDEO-ARCHIVE
归档节点：ZONGYUAN-ROOT｜DID-BR-000002｜Ω₀⊂⊙∞⊂Ω
版本：V1.0-LOCK｜2026-09-13｜适用：豆包快速对话生成的视频资产迁移至云端归档
核心原则：以实测为准，回执不作真值，每步独立核验

## 一、适用场景
豆包「快速对话」模式生成的视频（未进入工作任务资产库），需要下载并归档到云端服务器 / 记忆网关。

## 二、全流程（9步）

### 第1步｜获取分享链接
用户从快速对话视频卡片复制分享链接：
`https://www.doubao.com/video-sharing?source_type=mobile&share_id=...&video_id=...`

### 第2步｜解析真实视频直链
分享页为 SPA，HTML 无直链；API 需登录态（401）。用 Playwright 渲染页面并提取 `<video>` 元素 src：
```python
# playwright async: goto 分享URL -> wait 6s -> 点击播放 -> evaluate
# document.querySelector('video').currentSrc
# 得到形如 https://v26-videoweb.doubao.com/.../video/tos/.../xxx.mp4?...&download=true
```

### 第3步｜下载
Python urllib 下载，需带 UA + Referer `https://www.doubao.com/`：
```bash
curl -A "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0...)" -e "https://www.doubao.com/" -o 输出.mp4 "直链"
```

### 第4步｜本地验证（缺一不可）
- `file -b 文件.mp4` → ISO Media, MP4 Base Media
- `ffprobe` → duration≈10s、720x1280、HEVC+AAC
- `sha256sum` → 记录哈希

### 第5步｜云端 videos 桶归档
```bash
curl -s -H "X-Capture-Token: ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d" \
  -F 'file=@文件.mp4' -F 'bucket=videos' -F 'subdir=YYYY-MM-DD' \
  https://drama.huodouai.com/api/upload
# 成功回执含 path /opt/storage/videos/... 与 ep_id
```

### 第6步｜飞书云盘归档
```bash
lark-cli drive +upload --folder-token CbUqfLX4QlpezudczTpcHLqGnd9 --file ./文件.mp4
```

### 第7步｜资产清单更新
manifest JSON 追加条目：asset_id / 时长 / 分辨率 / 本地路径 / SHA256 / 云端 ep_id / 状态=archived

### 第8步｜上报中枢
report 上报：truth_type=achievement，含资产名、SHA256、云端 ep、DID-BR-000002 + Ω₀⊂⊙∞⊂Ω

### 第9步｜回执核验
清单公网链接 + 云端路径 + ep_id + 哈希四核对一致，才标记闭环完成。

## 三、实测记录（2026-09-13）
- V4：huli-V4-20260913.mp4｜10.08s 720x1280 HEVC｜3.77MB
- SHA256 955d7e3b…｜云端 ep cap0913141｜飞书 EnSxbk1K…｜上报 total 3613 ✅

## 四、关键参数
- 上传接口：`https://drama.huodouai.com/api/upload`
- 鉴权：`X-Capture-Token: ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d`
- 桶：videos（作品视频）｜飞书归档文件夹：CbUqfLX4QlpezudczTpcHLqGnd9

## 五、错误处理
- 分享 API 401 → API 需登录态，改走浏览器渲染提取 video src
- 直链带签名参数（l=时间戳等）→ 链接有时效，获取后立即下载
- URL 含 `lr=video_gen_watermark_dyn` → 生成视频带动态水印，属正常
- 下载失败 → 换 UA/Referer 重试一次，仍失败重新解析直链

---
Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜QUICKCHAT-VIDEO-ARCHIVE SOP V1.0｜LOCKED
