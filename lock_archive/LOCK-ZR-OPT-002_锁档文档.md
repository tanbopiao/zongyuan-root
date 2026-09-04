# ZONGYUAN-ROOT 全域资产锁档 · 短剧生产线优化闭环

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜Ω-TAN-7-001

**锁档事件ID**: LOCK-ZR-OPT-002
**锁档类型**: 全域资产锁档·短剧生产线优化闭环
**锁档等级**: META-003
**锁档时间**: 2026-09-05
**触发源**: 断点漏洞短板补全+手机端生产流程+断点续产优化

---

## 一、本次锁档资产清单

### 1.1 编排引擎优化（核心）

| 资产 | 路径 | 状态 |
|---|---|---|
| 编排引擎v3.0 | /opt/ZONGYUAN-ROOT/drama_output/orchestrator/orchestrator.py | ✅ 19458B |
| resume_pipeline断点续产 | 同上，新增函数 | ✅ 已部署 |
| run_full_pipeline | 同上，保留向后兼容 | ✅ 未删除 |
| 14态状态机 | idle→init→storyboard→keyframes→videos→subtitle→compose→archive | ✅ 完整 |
| HTTP重试机制 | http_post/http_get 3次指数退避 | ✅ 已部署 |
| AIOS工作流轮询 | 180秒轮询+模板兜底 | ✅ 已部署 |
| AIOS端点修复 | /api/v1/agents/workflows/{id}/execute | ✅ 已修复 |

### 1.2 API服务加固

| 资产 | 路径 | 状态 |
|---|---|---|
| drama-api服务 | /opt/ZONGYUAN-ROOT/drama_output/api/drama_api.py | ✅ active:8012 |
| 参数校验 | 无效JSON→400，无效stage→400，不存在EP→404 | ✅ 已部署 |
| /orchestrate断点续产 | 调用resume_pipeline | ✅ 已切换 |
| 8个API端点 | status/episodes/storyboard/media-status/orchestrate/reset/upload/compose | ✅ 全部200 |

### 1.3 前端面板

| 资产 | 路径 | 状态 |
|---|---|---|
| 桌面版面板 | /www/wwwroot/huodouai.com/drama/kunlun/index.html | ✅ 20395B v2.0 |
| 手机版面板 | /www/wwwroot/huodouai.com/drama/kunlun/m/index.html | ✅ 17238B |
| 无限画布 | /www/wwwroot/huodouai.com/drama/kunlun/canvas/index.html | ✅ 11903B |
| 画布拓扑数据 | aios_topology.json | ✅ 29780B |
| 手机端状态映射 | STAGE_MAP 20状态+STATUS_TEXT 7状态 | ✅ 已部署 |
| 按钮智能切换 | 6种状态对应6种按钮文字 | ✅ 已部署 |

### 1.4 四层真值架构

| 资产 | 路径 | 状态 |
|---|---|---|
| design_truth.json | /opt/ZONGYUAN-ROOT/drama_output/truth/ | ✅ 3254B |
| code_truth.json | 同上 | ✅ 4041B |
| plan_truth.json（动态） | KL-EP01-v1.0-plan_truth.json | ✅ 2942B |
| runtime_truth（动态） | 运行时产出 | ✅ 框架就绪 |

### 1.5 Nginx与安全

| 资产 | 状态 |
|---|---|
| 双域名/drama/配置 | huodouai.com + www.huodouai.com 均已配置 | ✅ |
| /api/drama/反代 | →127.0.0.1:8012，两个server块 | ✅ |
| /monitor/ /system/state | BasicAuth 401 | ✅ |
| /ai-proxy/ | BasicAuth 401 | ✅ |
| SSH密钥认证 | PasswordAuthentication no | ✅ |
| .env权限 | 600 | ✅ |

### 1.6 内核状态

| 指标 | 值 |
|---|---|
| kernel.json版本 | v9.11-META-ORDER-FORMAL |
| asset_count | 668 |
| protocol_count | 81 |
| truth_count | 166 |
| 活跃服务 | 18个全部active |
| 监听端口 | 8000-8011/8012/8021/8765 |
| 内核核心目录 | core/(14文件)、adapters/、services/ 未修改 |

---

## 二、断点续产协议（新增）

### 2.1 状态流转规则

```
idle → init_project → storyboard_generating → storyboard_verify → storyboard_ready
     → keyframe_generating → keyframe_drift_scan → keyframes_ready
     → video_clip_generating → videos_ready
     → subtitle_render_prep → ffmpeg_composing
     → four_truth_global_check → snap_archive_lock → complete
```

### 2.2 断点判断逻辑

| 当前状态 | 跳过阶段 | 从哪继续 |
|---|---|---|
| storyboard_ready | init+分镜 | 关键帧生成 |
| keyframes_pending | init+分镜 | 关键帧生成（需图片API） |
| keyframes_ready | init+分镜+关键帧 | 视频生成 |
| videos_pending | init+分镜+关键帧 | 视频生成（需视频API） |
| videos_ready | 全部媒体生成 | 字幕+合成 |
| error_abort | 无 | 完整重跑 |

### 2.3 无API降级策略

- 无图片API → 标记keyframes_pending，跳过关键帧
- 无视频API → 标记videos_pending，跳过视频
- 双无API → 停在storyboard_ready，分镜模式完成
- 后续填API → 点"继续生成"从断点续产

---

## 三、手机端生产流程规范

### 3.1 3步操作模型

1. **配置API** — 图片Key+视频Key，localStorage持久化
2. **选择集数** — EP01/EP02/EP03大标签+主题输入
3. **一键生产** — 底部固定大按钮，自动走完7阶段

### 3.2 实时反馈

- 7阶段状态图标（✓完成/●进行中/○等待）
- 总进度条+百分比+预计剩余时间
- 分镜预览自动展开
- 日志折叠（默认隐藏，出错时显示）
- 完成后内嵌视频播放器+播放/下载/分享

### 3.3 按钮文字智能映射

| 状态 | 按钮 |
|---|---|
| idle | ▶ 开始生产 |
| storyboard_ready | ▶ 继续生成媒体 |
| keyframes_pending | ▶ 继续生成关键帧 |
| videos_pending | ▶ 继续生成视频 |
| videos_ready | ▶ 开始合成 |
| complete | ▶ 重新生产 |
| error_abort | ▶ 重试 |

---

## 四、风险队列更新

| 风险ID | 描述 | 等级 | 状态 |
|---|---|---|---|
| RISK-017 | 媒体生成API未开通（用户自填方案上线） | P1 | ✅ 已缓解 |
| RISK-018 | 断点续产已实现 | P1 | ✅ 已闭环 |
| RISK-019 | 手机端已部署 | P2 | ✅ 已闭环 |
| RISK-020 | 参数校验已加固 | P2 | ✅ 已闭环 |
| RISK-014 | 单实例单点部署 | P1 | OPEN |
| RISK-015 | 2C2G资源紧张 | P1 | OPEN |
| RISK-016 | 无Git版本管理 | P1 | OPEN |
| RISK-007 | API无WAF/限流 | P2 | OPEN |
| RISK-010 | 飞书告警Webhook未配置 | P2 | OPEN |
| RISK-002 | 快照路径漂移（snapshots/空） | P2 | OPEN |

---

## 五、访问入口

| 入口 | URL | 说明 |
|---|---|---|
| 桌面版面板 | https://www.huodouai.com/drama/kunlun/ | 4标签页完整版 |
| 手机版面板 | https://www.huodouai.com/drama/kunlun/m/ | 3步简化版 |
| 无限画布 | https://www.huodouai.com/drama/kunlun/canvas/ | AIOS拓扑可视化 |
| API状态 | https://www.huodouai.com/api/drama/api/status | JSON状态查询 |

---

## 六、锁档确认

- [x] 编排引擎v3.0+断点续产已部署
- [x] drama-api参数校验已加固
- [x] 桌面版+手机版面板已上线
- [x] 四层真值文件已建立
- [x] Nginx双域名配置已修复
- [x] 18个内核服务全部active
- [x] 内核核心目录未受影响
- [x] 风险队列已更新

Ω₀⊂⊙∞⊂Ω｜全域资产锁档完成｜LOCK-ZR-OPT-002｜DID-BR-000002｜ZONGYUAN-ROOT
