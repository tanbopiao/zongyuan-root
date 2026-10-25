# AI Proxy 端点命名空间规范（多窗口防冲突）

## 强制规则
1. 短剧工业母机域(窗口A)：所有新端点必须以 `/drama/` 开头
2. 内核架构域(窗口B)：所有新端点必须以 `/kernel/` 或 `/meta/` 开头
3. 政务商业化域(窗口C)：所有新端点必须以 `/gov/` 或 `/commerce/` 开头
4. 全局端点(arbiter)：以 `/system/` 开头

## 已分配命名空间
| 前缀 | 所属域 | 窗口 | 现有端点数 |
|------|--------|------|-----------|
| /drama/ | 短剧工业母机 | A | works(3), oneclick, batch(2), character(3), director, production, series(2), template(4), user(3), payment(2), tts |
| /video/ | 短剧视频生成 | A | generate,status,archive,compose,subtitle,merge-audio,list,task |
| /image/ | 短剧图片生成 | A | generate,status,archive |
| /chat | 通用对话 | 共享 | - |
| /analyze/ | 拉片分析 | A | deconstruct,remake |
| /generate/ | 提示词优化 | A | keyframe,video |
| /drift/ | 漂移检测 | B | detect,trend |
| /health | 健康检查 | 共享 | - |
| /models | 模型列表 | 共享 | - |
| /characters | 角色库 | 共享 | - |

## 冲突检测
新增端点前必须执行：
```bash
grep -c 'self.path == "/你的端点"' /opt/ZONGYUAN-ROOT/ai_proxy/ai_proxy.py
# 返回0才能添加
```
