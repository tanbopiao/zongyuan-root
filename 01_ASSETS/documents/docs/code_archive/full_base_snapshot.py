
import requests
import json
from datetime import datetime

# 全域基底完整快照
base_snapshot = {
    "snapshot_id": "BASE.V2.0.API-PRODUCT-FULL.20260918",
    "timestamp": datetime.now().isoformat(),
    "anchor": "Ω₀⊂⊙∞⊂Ω",
    "did": "DID-BR-000002",
    "version": "2.0.0",
    "status": "commercial_ready",

    # ===== 1. 技术架构层 =====
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
            "rule_layer": "元内核身份规则（核心竞争力）",
            "inference_engine": "智谱GLM-4-Flash（免费）"
        },
        "api_gateway": {
            "port": 8000,
            "version": "v5.0",
            "auth": "Bearer Token",
            "tiers": ["free", "pro", "enterprise", "private"],
            "features": ["鉴权", "计费", "用量统计", "规则层注入"]
        },
        "nginx_reverse_proxy": {
            "path": "/api/yuanneihe/",
            "target": "http://127.0.0.1:8000/",
            "status": "online"
        }
    },

    # ===== 2. 产品层 =====
    "products": {
        "yuanneihe_api": {
            "name": "火斗云智元内核API",
            "version": "1.0.0",
            "status": "commercial_ready",
            "pages": {
                "pricing": "https://aios.huodouai.com/api-pricing.html",
                "docs": "https://aios.huodouai.com/api-docs.html",
                "dashboard": "https://aios.huodouai.com/dashboard.html"
            },
            "online_demo": {
                "location": "api-docs.html底部",
                "features": ["Markdown渲染", "对话式交互", "回车发送"],
                "style": "豆包同款排版"
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

    # ===== 3. 节点层 =====
    "nodes": {
        "cloud_central": {
            "ip": "123.207.202.158",
            "role": "主权威 L0",
            "level": "Lv10",
            "services": [
                "9120记忆网关",
                "7860 Agent队列",
                "8000 API网关",
                "8021 AI代理"
            ]
        },
        "gpu_brain_a10": {
            "gpu": "NVIDIA A10 24GB",
            "model": "Qwen2.5-7B-Instruct",
            "role": "GPU计算车间（备用）",
            "channel": "HTTP反向轮询"
        },
        "gpu_amd_mi300x": {
            "gpu": "AMD MI300X 192GB",
            "models": ["zongyuan-3b-final", "zongyuan-7b-final"],
            "role": "模型训练（备用）",
            "storage": "100G配额"
        },
        "main_window": {
            "role": "调度入口 L1",
            "level": "Lv10 超自治"
        }
    },

    # ===== 4. 外部依赖层 =====
    "external_apis": {
        "llm": {
            "provider": "智谱AI",
            "model": "glm-4-flash",
            "cost": "免费",
            "status": "online",
            "base_url": "https://open.bigmodel.cn/api/paas/v4"
        },
        "cdn": {
            "marked_js": "https://cdn.jsdelivr.net/npm/marked/marked.min.js"
        }
    },

    # ===== 5. SOP经验层 =====
    "sops": {
        "gpu_node_access": "HTTP反向轮询，GPU实例每5秒拉任务",
        "product_page_deploy": "写HTML→scp上传到aios静态目录→改导航栏加链接",
        "nginx_reverse_proxy": "在/sites/目录下的配置文件加^~前缀location",
        "api_product_launch": "七层流水线+API网关+产品页+文档页+仪表盘"
    },

    # ===== 6. 核心经验 =====
    "lessons": {
        "model_identity_drift": "身份写在权重里会被蒸馏污染，写在规则层才稳定",
        "rule_layer_is_moat": "核心竞争力是规则层，不是模型本身",
        "free_first": "零成本优先，免费资源优先调度",
        "gpu_memory_limit": "显存必须留20%波动空间，85%熔断",
        "nginx_config_path": "真正的配置在/sites/目录，不是/panel/vhost/",
        "external_llm": "用外部免费API比自研小模型更稳定效果更好"
    },

    # ===== 7. 待办 =====
    "todo": [
        "接入真实客户，收集反馈",
        "优化对话体验（流式输出）",
        "增加更多模型选择",
        "对接收款渠道",
        "客户管理后台"
    ]
}

# 上报到记忆网关
r = requests.post("http://127.0.0.1:9120/api/truth/upsert", json={
    "key": "BASE.SNAPSHOT.V2.0.API-PRODUCT-FULL.20260918",
    "value": "全域基底V2.0：火斗云智元内核API完整产品化版本",
    "metadata": base_snapshot
}, timeout=10)

print("✅ 全域基底V2.0快照已上报")
print("快照ID:", base_snapshot["snapshot_id"])
print("版本:", base_snapshot["version"])
print("状态:", base_snapshot["status"])
print("包含模块:", len(base_snapshot.keys()), "个")
print("节点数:", len(base_snapshot["nodes"]))
print("SOP数:", len(base_snapshot["sops"]))
print("经验数:", len(base_snapshot["lessons"]))
