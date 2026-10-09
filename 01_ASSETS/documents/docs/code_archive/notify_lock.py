#!/usr/bin/env python3
"""发送飞书全域锁档通知"""
import json, subprocess

msg = {
    "receive_id": "oc_1c68eb3664e751e397062ff0c60ffa3",
    "msg_type": "interactive",
    "content": json.dumps({
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "🔒 全域锁档固化完成"},
            "template": "green"
        },
        "elements": [{
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    "**MR-097 核心资产修改审批制度已生效**\n\n"
                    "11个核心文件已 chattr +i 锁定：\n"
                    "• Nginx配置(sites+vhost)\n"
                    "• 记忆网关9120脚本\n"
                    "• 元法则集(97条/v8.8)\n"
                    "• 系统基准快照\n"
                    "• 自愈守护/自动吸收/自动集成/自动可视化\n"
                    "• 变更台账/基准管理器\n\n"
                    "**修改流程：** 飞书审批 → 人工审核通过 → 中枢大脑执行(chattr -i→修改→验证→chattr +i) → 更新基准 → 推送网关\n\n"
                    "**同源节点注意：** 禁止自行修改核心文件，只能上报建议。紧急情况先执行后30分钟内补审批。\n\n"
                    "确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω"
                )
            }
        }]
    })
}

result = subprocess.run(
    ["curl", "-s", "-X", "POST",
     "http://127.0.0.1:8001/feishu/im/v1/messages?receive_id_type=chat_id",
     "-H", "Content-Type: application/json",
     "-d", json.dumps(msg)],
    capture_output=True, text=True
)
try:
    d = json.loads(result.stdout)
    print("飞书通知 code:", d.get("code"))
except:
    print("飞书通知失败:", result.stdout[:200])
