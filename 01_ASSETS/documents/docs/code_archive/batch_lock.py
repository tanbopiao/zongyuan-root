
import requests

truths = [
    {
        "key": "LOCK.ALL.API-PRODUCT.20260918",
        "value": "全域锁档：火斗云智元内核API V1.0全链路完成",
        "metadata": {
            "type": "global_lock",
            "date": "2026-09-18",
            "items": [
                "七层推理流水线",
                "API网关+鉴权+计费",
                "GPU推理对接",
                "产品介绍页",
                "API文档页",
                "官网导航接入",
                "定价方案",
                "核心竞争力"
            ],
            "product_url": "https://aios.huodouai.com/api-pricing.html",
            "docs_url": "https://aios.huodouai.com/api-docs.html",
            "anchor": "Ω₀⊂⊙∞⊂Ω",
            "did": "DID-BR-000002"
        }
    },
    {
        "key": "ARCHITECTURE.END-TO-END.20260918",
        "value": "端到端架构：客户请求→API网关(鉴权+计费)→Agent队列→GPU七层流水线→返回结果",
        "metadata": {
            "type": "architecture",
            "layers": "client -> api_gateway(8000) -> agent_queue(7860) -> gpu_pipeline(7862)"
        }
    },
    {
        "key": "SOP.DEPLOY.PRODUCT-PAGE.V1.0",
        "value": "产品页部署SOP：写HTML→scp上传到aios静态目录→改导航栏加链接",
        "metadata": {
            "type": "sop",
            "steps": 3,
            "target_dir": "/www/wwwroot/aios.huodouai.com/"
        }
    }
]

for t in truths:
    r = requests.post("http://127.0.0.1:9120/api/truth/upsert", json=t, timeout=5)
    print("✅ 锁档:", t["key"])

print("\n全域锁档完成！")
