# OP-BATCH-GEN-004｜关键帧批量生成调度算子

> 算子编号：OP-BATCH-GEN-004
> 归属体系：昆仑洞天 IP 量产流水线
> 状态：契约定稿 v1.0

---

## 一、真值契约

### 目标
读取分镜清单（storyboard.json），按顺序批量调用图像生成模型，产出关键帧图片，自动绑定提示词元数据，归档至对应剧集目录。

### 输入
```json
{
  "op_name": "OP-BATCH-GEN-004",
  "storyboard_path": "/storyboard/season1_ep01-09.json",
  "output_dir": "/assets/keyframes/",
  "model": "seedream-5.0-flash",
  "aspect_ratio": "9:16",
  "max_retries": 2,
  "concurrency": 1
}
```

### 分镜清单结构（storyboard.json）
```json
{
  "season": 1,
  "episode_range": "EP01-EP09",
  "frames": [
    {
      "ep": "EP01",
      "shot_id": "KF-EP01-01",
      "prompt": "昆仑洞天初始创世，悬浮神山...",
      "negative_prompt": "西方铠甲,畸形肢体",
      "style_ref": "kunlun-tianyuan-v1"
    }
  ]
}
```

### 执行流程
```
Step1  读取 storyboard.json，校验 JSON 结构完整
Step2  逐帧取出 prompt + negative_prompt
Step3  调用图像生成 API（seedream-5.0-flash）
Step4  生成成功 → 保存到 output_dir/{ep}/{shot_id}.jpg
Step5  同时写入同名 .meta.json（含 prompt、model、时间戳、privacy_level=private）
Step6  生成失败 → 重试 max_retries 次
Step7  仍失败 → 记录 failed_frames，不中断整体批次
Step8  全部完成后，调用 OP-ARCHIVE-001 归档新资产
Step9  输出生成报告 JSON
```

### 禁止项
- ❌ 禁止跳过失败帧继续而不记录
- ❌ 禁止并发超过 concurrency 限制（默认串行，防额度超限）
- ❌ 禁止覆盖已存在的同名关键帧（已归档则跳过）
- ❌ 禁止修改 storyboard.json 原始分镜清单

### 输出报告
```json
{
  "op_name": "OP-BATCH-GEN-004",
  "run_timestamp": "2026-10-10T23:00:00+08:00",
  "summary": {
    "total_frames": 9,
    "success": 9,
    "failed": 0,
    "skipped_existing": 0,
    "retries_used": 0
  },
  "generated_files": [
    "/assets/keyframes/EP01/KF-EP01-01.jpg"
  ],
  "failed_frames": [],
  "archive_triggered": true
}
```

---

## 二、测试用例

| 编号 | 场景 | 预期 |
|---|---|---|
| TC-01 | 正常9帧全部生成 | success=9，文件+meta.json成对存在 |
| TC-02 | 第3帧生成失败 | 重试2次后仍失败，failed记录，其余帧继续 |
| TC-03 | 已有同名关键帧 | skipped_existing，不重复生成 |
| TC-04 | storyboard.json格式错误 | 报错退出，不发起任何生成请求 |
| TC-05 | 全部完成后自动归档 | 触发OP-ARCHIVE-001，新资产进入账本 |
| TC-06 | 额度耗尽 | 记录 rate_limit，停止后续生成，不崩溃 |

---

## 三、技术约束
- 图像生成 API 调用需在工作任务沙箱内（普通对话无此权限）
- 默认 concurrency=1 串行，避免触发额度限流
- 每帧生成后立即落盘，不内存攒批
- privacy_level 默认 private（关键帧不对外，仅画廊筛选后公开）
