# 多智能体编排系统 · Multi-Agent Orchestrator

> ZONGYUAN-ROOT 元极恒一自治体系 · 任务编排与资源分级调度引擎
> 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 开源 Apache-2.0

---

## 一、是什么

多智能体编排系统是体系内所有子智能体的调度中枢：对每个分片任务先执行 **任务评估（evaluate）**，按元法则 META-RES-003（资源稳态保护）/ META-RES-004（多模态任务资源分级判定）自动判定风险等级，白名单任务自动并行分发，黑名单任务强制人工放行，杜绝高消耗任务失控抢占资源。

## 二、核心机制

### 1. 任务风险三级判定

| 风险级 | 判定条件 | 处置 |
|--------|----------|------|
| **WHITE 白名单** | 仅命中低消耗动作 | 自动分片并行执行 |
| **BLACK 黑名单** | 命中高消耗动作 | 强制拦截，人工放行（human_approve） |
| **MIXED 混合** | 白+黑动作并存 | 整体按高消耗判定，人工放行 |

### 2. 动作库（与元法则 1:1 对齐）

**白名单（WHITE_ACTIONS）**：file_scan / read_metadata / asset_classify_index / ledger_write / hash_verify / dir_organize / detect_missing_asset / light_visual_tag / ffmpeg_stream_copy

**黑名单（BLACK_ACTIONS）**：txt2img / img2img / inpaint / style_transfer / super_res / txt2video / img2video / video_extend / video_redraw / frame_interp_ai / ai_tts / ai_bgm_gen / ai_vocal_gen / ai_video_render / drama_batch_produce / pv_auto_produce / storyboard_render

### 3. 配套调度规则 R9

> **所有分片在分片分发之前，必须调用 evaluate_task 做校验，不允许跳过评估直接下发子智能体。**

## 三、核心代码骨架（multi_agent_plan.py）

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多智能体编排-任务评估模块 ｜ 适配 META-RES-003 / META-RES-004"""
import json, time
from dataclasses import dataclass, asdict
from enum import Enum

class TaskRiskLevel(Enum):
    WHITE = "WHITE"   # 白名单-低消耗，允许自动并行
    BLACK = "BLACK"   # 黑名单-高消耗，必须人工放行
    MIXED = "MIXED"   # 混合任务，整体人工放行

@dataclass
class EvaluateResult:
    risk_level: TaskRiskLevel
    allow_auto_run: bool
    hit_actions: list
    block_reason: str
    suggestion: str
    event_log: dict

WHITE_ACTIONS = {
    "file_scan", "read_metadata", "asset_classify_index", "ledger_write",
    "hash_verify", "dir_organize", "detect_missing_asset", "light_visual_tag",
    "ffmpeg_stream_copy",
}

BLACK_ACTIONS = {
    "txt2img", "img2img", "inpaint", "style_transfer", "super_res",
    "txt2video", "img2video", "video_extend", "video_redraw", "frame_interp_ai",
    "ai_tts", "ai_bgm_gen", "ai_vocal_gen", "ai_video_render",
    "drama_batch_produce", "pv_auto_produce", "storyboard_render",
}

def evaluate_task(task_def: dict) -> EvaluateResult:
    """任务评估主入口：白名单自动放行 / 黑名单拦截 / 混合人工放行"""
    task_id = task_def.get("task_id", f"task-{int(time.time())}")
    actions = set(task_def.get("actions", []))
    human_approve = bool(task_def.get("human_approve", False))
    hit_white = actions & WHITE_ACTIONS
    hit_black = actions & BLACK_ACTIONS
    event_log = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task_id": task_id,
        "hit_white_actions": list(hit_white),
        "hit_black_actions": list(hit_black),
        "human_approve_flag": human_approve,
    }
    # 场景1：只命中白名单 → 自动并行
    if hit_white and not hit_black:
        return EvaluateResult(TaskRiskLevel.WHITE, True, list(hit_white), "",
            "白名单低耗任务，允许编排系统自动分片并行执行；遵循降耗优先。", event_log)
    # 场景2：只命中黑名单 → 人工放行
    elif hit_black and not hit_white:
        allow = bool(human_approve)
        return EvaluateResult(TaskRiskLevel.BLACK, allow, list(hit_black),
            "" if allow else "命中高消耗黑名单，【META-RES-004】强制拦截，等待人工明确放行指令。",
            "已获取人工放行标记，受控执行高消耗任务。" if allow else "强制拦截，等待人工放行。", event_log)
    # 场景3：混合 → 整体按高消耗判定
    elif hit_white and hit_black:
        allow = bool(human_approve)
        return EvaluateResult(TaskRiskLevel.MIXED, allow, list(hit_white | hit_black),
            "" if allow else "任务混合高低消耗动作，按META-RES-004整体判定高消耗，强制拦截等待人工放行。",
            "已人工放行；建议白名单并行、黑名单受控串行执行。" if allow else "整体拦截，等待人工放行。", event_log)
    # 场景4：无匹配动作（纯推演/文本规划）
    else:
        return EvaluateResult(TaskRiskLevel.WHITE, True, [], "",
            "无多媒体生产动作，纯文本推演规划，允许自动执行。", event_log)

def export_event_log(result: EvaluateResult, log_path: str):
    """评估事件日志持久化落盘，供飞书Base/中枢网关上报"""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")

# ---- 调用示例 ----
# from multi_agent_plan import evaluate_task, export_event_log
# task = {"task_id": "kunlun-asset-index-001",
#         "actions": ["file_scan", "read_metadata", "asset_classify_index"],
#         "human_approve": False}
# eval_ret = evaluate_task(task)
# export_event_log(eval_ret, "./event-audit-log.jsonl")
# if eval_ret.allow_auto_run: ...   # 分片调度
# else: print(f"任务拦截：{eval_ret.block_reason}")
```

## 四、审计与合规

| 项目 | 说明 |
|------|------|
| 事件日志 | 每次评估完整落盘（JSONL），可读推飞书Base + 中枢记忆网关 |
| 单元测试 | 内置 3 用例：白名单放行 / 黑名单拦截 / 混合拦截，`python multi_agent_plan.py` 直接自测 |
| 资源稳态 | META-RES-003：任务队列空自动降频休眠，P0 心跳保障最低频率 |
| 零成本 | 纯标准库实现，无第三方依赖，最小额度消耗 |

## 五、与体系协同

- 上层调度：任务台账（共享大脑）→ 认领 → evaluate 校验 → 分片 → 执行 → 回写
- 算力保护：高消耗动作（图像/视频生成）全部黑名单化，杜绝自动消耗付费额度
- 闭环：白名单并行、黑名单人工放行、混合拆分串行，全程留痕可审计

---

> 火斗云智AIOS · ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
