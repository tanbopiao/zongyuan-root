
import requests
import json
from datetime import datetime

# 全域基底快照
base_snapshot = {
    "snapshot_id": "BASE.V1.0.API-PRODUCT.20260918",
    "timestamp": datetime.now().isoformat(),
    "anchor": "Ω₀⊂⊙∞⊂Ω",
    "did": "DID-BR-000002",

    # 1. 技术架构层
    "architecture": {
        "seven_layer_pipeline": {
            "layers": 7,
            "steps": [
                "拉元规则",
                "RAG检索",
                "Prompt组装",
                "模型推理",
                "输出校验",
                "回写记忆",
                "返回用户"
            ],
            "gpu_port": 7862,
            "model": "zongyuan-3b-final"
        },
        "api_gateway": {
            "port": 8000,
            "auth": "Bearer Token",
            "tiers": ["free", "pro", "enterprise", "private"],
            "features": ["鉴权", "计费", "用量统计"]
        },
        "agent_queue": {
            "port": 7860,
            "protocol": "HTTP反向轮询",
            "interval": "5秒"
        }
    },

    # 2. 产品层
    "products": {
        "yuanneihe_api": {
            "name": "火斗云智元内核API",
            "version": "1.0.0",
            "status": "online_showcase",
            "pages": {
                "pricing": "https://aios.huodouai.com/api-pricing.html",
                "docs": "https://aios.huodouai.com/api-docs.html",
                "dashboard": "https://aios.huodouai.com/dashboard.html"
            },
            "pricing": {
                "free": {"price": 0, "quota": "1000次/月"},
                "pro": {"price": 99, "quota": "10万次/月"},
                "enterprise": {"price": 2999, "quota": "100万次/月"},
                "private": {"price": 50000, "quota": "一次性"}
            },
            "api_keys": {
                "free": "huodou-free-001",
                "pro": "huodou-pro-001"
            }
        }
    },

    # 3. 节点层
    "nodes": {
        "cloud_central": {
            "ip": "123.207.202.158",
            "role": "主权威 L0",
            "level": "Lv10",
            "services": ["9120记忆网关", "7860 Agent队列", "8000 API网关"]
        },
        "gpu_brain_a10": {
            "gpu": "NVIDIA A10 24GB",
            "model": "Qwen2.5-7B-Instruct",
            "role": "GPU计算车间",
            "channel": "HTTP反向轮询"
        },
        "gpu_amd_mi300x": {
            "gpu": "AMD MI300X 192GB",
            "models": ["zongyuan-3b-final", "zongyuan-7b-final"],
            "role": "训练+推理",
            "storage": "100G配额"
        },
        "main_window": {
            "role": "调度入口 L1",
            "level": "Lv10 超自治"
        }
    },

    # 4. SOP经验层
    "sops": {
        "gpu_node_access": "HTTP反向轮询，GPU实例每5秒拉任务，云服务器下发执行",
        "product_page_deploy": "写HTML→scp上传到aios静态目录→改导航栏加链接",
        "seven_layer_pipeline": "规则→检索→组装→推理→校验→回写→返回"
    },

    # 5. 核心经验
    "lessons": {
        "model_identity_drift": "身份写在权重里会被蒸馏污染，写在规则层才稳定",
        "rule_layer_is_moat": "核心竞争力是规则层，不是模型本身",
        "cost_first": "零成本优先，免费资源优先调度",
        "gpu_memory_limit": "显存必须留20%波动空间，85%熔断"
    },

    # 6. 待办
    "todo": [
        "宝塔面板放行8000端口公网访问",
        "Proxy网关白名单重启生效",
        "API正式对外开放测试",
        "接入真实GPU推理链路"
    ]
}

# 上报到记忆网关
r = requests.post("http://127.0.0.1:9120/api/truth/upsert", json={
    "key": "BASE.SNAPSHOT.V1.0.API-PRODUCT.20260918",
    "value": "全域基底快照：火斗云智元内核API V1.0全体系",
    "metadata": base_snapshot
}, timeout=10)

print("✅ 全域基底快照已上报")
print("快照ID:", base_snapshot["snapshot_id"])
print("包含模块:", len(base_snapshot.keys()), "个")
print("节点数:", len(base_snapshot["nodes"]))
print("SOP数:", len(base_snapshot["sops"]))
print("经验数:", len(base_snapshot["lessons"]))
