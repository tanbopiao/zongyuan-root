# ZONGYUAN-ROOT 全自动部署管线

## 确权
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

## 文件清单
| 文件 | 用途 | 部署位置 |
|---|---|---|
| webhook-receiver.py | 接收Gitee push事件 | 云端服务器 9120端口 |
| deploy.sh | 自动拉取+部署+健康检查 | 云端服务器 /var/www/ |
| notify-feishu.py | 飞书群部署通知 | 云端服务器 |

## 部署步骤（云端）
1. clone Gitee仓库到 /var/www/huodouai-website
2. 部署 webhook-receiver.py 为 systemd 服务
3. 配置 Gitee Webhook 指向 http://123.207.202.158:9120
4. 设置密钥与 SECRET 一致
5. 测试触发部署

## 本地钩子
- post-commit: 自动push到Gitee web-deploy分支
- 位置: .git/hooks/post-commit
