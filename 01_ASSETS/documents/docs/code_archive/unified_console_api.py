#!/usr/bin/env python3
"""
统一控制台API聚合服务 V1.0
将所有引擎的状态和功能统一暴露，供前端可视化面板调用
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import json, os, subprocess, requests, psutil
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="ZONGYUAN-ROOT Unified Console API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TRUTH_BASE = "http://127.0.0.1:9120"
VECTOR_BASE = "http://127.0.0.1:8014"
KG_BASE = "http://127.0.0.1:8070/api/v1"
LLM_BASE = "http://127.0.0.1:8081/v1"
POWER_BASE = "http://127.0.0.1:9164"

ENGINES = {
    "rag_private_knowledge": {
        "name": "RAG私有知识库问答",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/rag_private_knowledge.py",
        "description": "串联向量库+知识图谱+本地小模型+9120真值库的私有知识库问答",
        "category": "认知能力"
    },
    "external_api_power_source": {
        "name": "外部API动力源V2.0",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/external_api_power_source.py",
        "description": "智谱GLM-4-Flash+魔塔+本地1.5B分层调度",
        "category": "动力源"
    },
    "auto_scaling": {
        "name": "服务自动扩缩容",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/auto_scaling.py",
        "description": "内存>70%自动暂停非核心服务，<50%自动恢复",
        "category": "资源管理"
    },
    "approval_deployment_pipeline": {
        "name": "飞书审批→自动部署闭环",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/approval_deployment_pipeline.py",
        "description": "审批通过后自动执行部署脚本",
        "category": "自动化"
    },
    "multi_agent_debate": {
        "name": "多智能体辩论决策",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/multi_agent_debate.py",
        "description": "5角色辩论(乐观/保守/技术/安全/哲学)+三维稳态加权仲裁",
        "category": "决策"
    },
    "unified_monitor": {
        "name": "统一监控面板",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/unified_monitor.py",
        "description": "81个服务实时健康状态+系统指标+端口状态+真值库状态",
        "category": "监控"
    },
    "deployment_verification": {
        "name": "部署验证闭环",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/deployment_verification_engine.py",
        "description": "5维度自动验证(HTTP/端口/文件/进程/内容)+飞书通知",
        "category": "质量保障"
    },
    "zongyuan_model_adapter": {
        "name": "元极恒一专属小模型适配层",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/zongyuan_model_adapter.py",
        "description": "推理时知识注入+RAG增强+体系前置约束，效果优于静态微调",
        "category": "模型专属化"
    },
    "operator_scheduler": {
        "name": "27算子调度唤醒中枢",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/operator_scheduler.py",
        "description": "十层拓扑27算子事件驱动唤醒+状态持久化+链式触发",
        "category": "算子体系"
    },
    "code_generation_self_check": {
        "name": "代码生成前自检引擎",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/code_generation_self_check.py",
        "description": "禁止模式自动检测，避免重复犯同样的错误",
        "category": "质量保障"
    },
    "three_state_monitor": {
        "name": "三态完备度量化监控",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/three_state_monitor.py",
        "description": "逻辑态/信息态/能量态三态评分+总体评估",
        "category": "理论监控"
    },
    "universal_learning_absorption": {
        "name": "全域学习吸收闭环引擎",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/universal_learning_absorption_engine.py",
        "description": "四层吸收成熟度评分+缺口识别+量化监控",
        "category": "学习进化"
    },
    "auto_solidification": {
        "name": "高价值成果自动固化引擎",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/auto_solidification_engine.py",
        "description": "五维价值评估+三级阈值+自动固化五步",
        "category": "自动化"
    },
    "self_evolution": {
        "name": "自我进化五维能力体系",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/self_evolution_engine.py",
        "description": "融合/整合/净化/修复/递归五维能力",
        "category": "自我进化"
    },
    "domain_twin_scanner": {
        "name": "主域数字孪生扫描器",
        "path": "/opt/ZONGYUAN-ROOT/ai-native-ops/domain_twin_scanner.py",
        "description": "9大维度全量采集，每小时更新DOMAIN_TWIN.CURRENT",
        "category": "数字孪生"
    }
}


@app.get("/api/console/status")
async def get_console_status():
    """获取控制台总览状态"""
    # 系统状态
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    
    # 真值库状态
    truth_count = 0
    try:
        r = requests.get(TRUTH_BASE + "/api/status", timeout=5)
        truth_count = r.json().get("stats", {}).get("truths", 0)
    except:
        pass
    
    # 知识图谱状态
    kg_nodes = 0
    kg_edges = 0
    try:
        r = requests.get(KG_BASE + "/kg/stat", timeout=5)
        kg_data = r.json()
        kg_nodes = kg_data.get("nodes", 0)
        kg_edges = kg_data.get("edges", 0)
    except:
        pass
    
    # 引擎状态
    engines_status = []
    for engine_id, engine_info in ENGINES.items():
        exists = os.path.exists(engine_info["path"])
        is_locked = False
        if exists:
            try:
                result = subprocess.run(["lsattr", engine_info["path"]], capture_output=True, text=True)
                is_locked = "i" in result.stdout.split()[0] if result.stdout else False
            except:
                pass
        engines_status.append({
            "id": engine_id,
            "name": engine_info["name"],
            "category": engine_info["category"],
            "description": engine_info["description"],
            "exists": exists,
            "locked": is_locked,
            "status": "active" if exists else "missing"
        })
    
    return {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu_percent": cpu_percent,
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_percent": disk.percent
        },
        "knowledge_base": {
            "truth_count": truth_count,
            "kg_nodes": kg_nodes,
            "kg_edges": kg_edges
        },
        "engines": {
            "total": len(ENGINES),
            "active": sum(1 for e in engines_status if e["exists"]),
            "locked": sum(1 for e in engines_status if e["locked"]),
            "list": engines_status
        },
        "baseline": {
            "version": "BASELINE-FOUNDATION-V2",
            "status": "locked",
            "no_rollback": True
        }
    }


@app.get("/api/console/engines")
async def list_engines():
    """列出所有引擎"""
    return {"engines": ENGINES}


@app.get("/api/console/engine/{engine_id}")
async def get_engine_detail(engine_id: str):
    """获取单个引擎详情"""
    if engine_id not in ENGINES:
        return {"error": "Engine not found"}
    engine = ENGINES[engine_id]
    exists = os.path.exists(engine["path"])
    file_size = os.path.getsize(engine["path"]) if exists else 0
    return {
        "id": engine_id,
        **engine,
        "exists": exists,
        "file_size_bytes": file_size,
        "file_size_kb": round(file_size / 1024, 2)
    }


@app.get("/api/console/truth/stats")
async def get_truth_stats():
    """获取真值库统计"""
    try:
        r = requests.get(TRUTH_BASE + "/api/status", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/console/kg/stats")
async def get_kg_stats():
    """获取知识图谱统计"""
    try:
        r = requests.get(KG_BASE + "/kg/stat", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/console/model/chat")
async def model_chat(message: dict):
    """调用专属模型适配层对话"""
    try:
        result = subprocess.run(
            ["python3", "/opt/ZONGYUAN-ROOT/ai-native-ops/zongyuan_model_adapter.py", message.get("message", "")],
            capture_output=True, text=True, timeout=60
        )
        return {"output": result.stdout, "error": result.stderr}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/console/deployment/log")
async def get_deployment_log():
    """获取部署验证日志"""
    log_file = "/opt/ZONGYUAN-ROOT/data/deployment_verification_log.json"
    if os.path.exists(log_file):
        with open(log_file) as f:
            return json.load(f)
    return {"deployments": [], "stats": {"total": 0, "success": 0, "failed": 0}}


@app.get("/api/console/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9170)
