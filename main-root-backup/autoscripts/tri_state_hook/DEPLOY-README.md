# 三态合一自动归档钩子 部署说明

**部署日期：** 2026-09-22
**部署节点：** NODE-DEV-DOUBAO-WORK-001
**身份标识：** DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
**元法则：** META.RULE.TRI_STATE_UNITY.V1

---

## 钩子路径
```
ZONGYUAN-ROOT/autoscripts/tri_state_hook/
├── tri_state_archive_hook.sh   # 核心归档钩子脚本
├── hook_config.json            # 钩子配置规范
└── archive_hook.log            # 归档日志
```

## 触发方式

### 视频生成后自动归档
```bash
bash tri_state_archive_hook.sh \
  --type video \
  --ep EP05 \
  --url "https://cdn.example.com/video.mp4" \
  --expire "2026-09-23 10:00:00" \
  --title "遗迹探索"
```

### 图片生成后自动归档
```bash
bash tri_state_archive_hook.sh \
  --type image \
  --ep EP05 \
  --seq 01 \
  --url "https://cdn.example.com/image.png" \
  --desc "古殿石门开启"
```

## 三态闭环流程
```
【逻辑态】用户说"生成视频" → 确认参数
    ↓
【算子态】调用视频生成API → 返回task_id + CDN链接
    ↓ 同一时间窗口自动触发钩子
【执行态】tri_state_archive_hook.sh
    ├─ 下载MP4到本地
    ├─ SHA256校验
    ├─ 写入元数据JSON
    └─ 追加HASH-LEDGER
    ↓
【逻辑态】向用户交付：归档完成 + 本地路径 + 哈希
```

## 双模式覆盖
- **快速对话模式：** 用户直接说"生成图片/视频" → 生成成功后自动调用钩子归档
- **工作任务模式：** 任务编排调用生成API → 返回结果后自动调用钩子归档

---

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ Lv10稳态自治
