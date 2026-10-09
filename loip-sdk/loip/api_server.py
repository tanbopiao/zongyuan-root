"""
LOIP REST API 服务 v0.2
将LOIP SDK封装为HTTP服务，任意技术栈可通过REST接口接入。

启动方式：
    pip install fastapi uvicorn
    python -m loip.api_server --host 0.0.0.0 --port 8000 --baseline ./baseline.json

或：
    uvicorn loip.api_server:app --host 0.0.0.0 --port 8000

API文档：http://localhost:8000/docs
"""
import os
import json
import argparse
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException, Body
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    print("[LOIP] 缺少依赖：pip install fastapi uvicorn pydantic")
    raise

from .sdk import LOIP
from . import __version__


# ===== 请求/响应模型 =====

class ProcessRequest(BaseModel):
    user_input: str
    ai_output: str
    context: Optional[str] = None


class RuleRequest(BaseModel):
    key: str
    rule: str
    weight: float = 1.0


class FactRequest(BaseModel):
    key: str
    fact: str
    confidence: float = 1.0


class ConstraintRequest(BaseModel):
    constraint: str
    level: str = "hard"


# ===== 全局LOIP实例 =====

_loip_instance: Optional[LOIP] = None
_config: Dict[str, Any] = {}


def get_loip() -> LOIP:
    if _loip_instance is None:
        raise HTTPException(status_code=500, detail="LOIP内核未初始化")
    return _loip_instance


def create_app(baseline_path: str = "./loip_baseline.json",
               audit_dir: str = "./loip_audit",
               backend: str = "auto") -> FastAPI:
    """创建FastAPI应用实例"""
    global _loip_instance, _config

    _loip_instance = LOIP(
        baseline_path=baseline_path,
        audit_dir=audit_dir,
        backend=backend
    )
    _config = {
        "baseline_path": baseline_path,
        "audit_dir": audit_dir,
        "backend": backend,
        "started_at": datetime.now().isoformat()
    }

    app = FastAPI(
        title="LOIP 逻辑本体智能协议 API",
        description="大模型稳态治理REST接口 · 漂移检测 · 幻觉抑制 · 双闭环审计",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # CORS支持
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ===== 核心治理接口 =====

    @app.post("/api/v1/process", summary="核心治理：漂移检测+幻觉抑制+自动修正")
    async def process_output(req: ProcessRequest):
        """对AI输出执行完整治理流水线"""
        loip = get_loip()
        result = loip.process(req.user_input, req.ai_output, req.context)
        return {
            "ok": True,
            "processing_id": result["processing_id"],
            "needs_correction": result["needs_correction"],
            "original_output": result["original_output"],
            "corrected_output": result["corrected_output"],
            "drift_detection": {
                "detected": result["drift_detection"]["drift_detected"],
                "conflict_count": result["drift_detection"]["conflict_count"],
                "drift_level": result["drift_detection"]["drift_level"],
                "severity": result["drift_detection"]["severity"],
                "conflicts": result["drift_detection"]["conflicts"]
            },
            "hallucination_guard": {
                "risk_level": result["hallucination_guard"]["hallucination_risk"],
                "issue_count": result["hallucination_guard"]["issue_count"],
                "issues": result["hallucination_guard"]["issues"],
                "suggestions": result["hallucination_guard"]["suggestions"]
            },
            "overall_risk": result["overall_risk"],
            "overall_score": result["overall_score"],
            "corrections_applied": result["corrections_applied"]
        }

    @app.post("/api/v1/drift/check", summary="仅执行漂移检测")
    async def check_drift(req: ProcessRequest):
        loip = get_loip()
        result = loip.drift_detector.check(req.user_input, req.ai_output)
        return {"ok": True, **result}

    @app.post("/api/v1/hallucination/check", summary="仅执行幻觉检测")
    async def check_hallucination(req: ProcessRequest):
        loip = get_loip()
        result = loip.hallucination_guard.check(req.ai_output, req.context)
        return {"ok": True, **result}

    # ===== 基线管理接口 =====

    @app.get("/api/v1/baseline", summary="获取本体基线摘要")
    async def get_baseline():
        loip = get_loip()
        return {"ok": True, "baseline": loip.baseline.get_summary()}

    @app.get("/api/v1/baseline/rules", summary="获取全部规则")
    async def get_rules():
        loip = get_loip()
        return {"ok": True, "rules": loip.baseline.get_all_rules()}

    @app.post("/api/v1/baseline/rule", summary="设置核心规则")
    async def set_rule(req: RuleRequest):
        loip = get_loip()
        result = loip.set_rule(req.key, req.rule, req.weight)
        return {"ok": result["status"] == "success", **result}

    @app.get("/api/v1/baseline/facts", summary="获取全部事实标准")
    async def get_facts():
        loip = get_loip()
        return {"ok": True, "facts": loip.baseline.data.get("facts", {})}

    @app.post("/api/v1/baseline/fact", summary="设置事实标准")
    async def set_fact(req: FactRequest):
        loip = get_loip()
        result = loip.set_fact(req.key, req.fact, req.confidence)
        return {"ok": True, **result}

    @app.get("/api/v1/baseline/constraints", summary="获取全部约束")
    async def get_constraints():
        loip = get_loip()
        return {"ok": True, "constraints": loip.baseline.get_constraints()}

    @app.post("/api/v1/baseline/constraint", summary="添加逻辑约束")
    async def add_constraint(req: ConstraintRequest):
        loip = get_loip()
        result = loip.add_constraint(req.constraint, req.level)
        return {"ok": True, **result}

    @app.post("/api/v1/baseline/lock", summary="执行eFuse锁档")
    async def lock_baseline():
        loip = get_loip()
        result = loip.lock()
        return {"ok": True, **result}

    @app.get("/api/v1/baseline/export", summary="导出基线为系统提示词")
    async def export_baseline():
        loip = get_loip()
        prompt = loip.export_baseline_prompt()
        return {"ok": True, "prompt": prompt}

    @app.get("/api/v1/baseline/history", summary="获取基线版本历史")
    async def baseline_history(limit: int = 20):
        loip = get_loip()
        return {"ok": True, "history": loip.baseline.get_version_history(limit)}

    # ===== 审计接口 =====

    @app.get("/api/v1/audit/summary", summary="获取审计摘要")
    async def audit_summary():
        loip = get_loip()
        return {"ok": True, "summary": loip.audit.get_summary()}

    @app.get("/api/v1/audit/report", summary="生成并导出审计报告")
    async def audit_report():
        loip = get_loip()
        report = loip.audit.generate_report()
        return {"ok": True, "report": report}

    @app.get("/api/v1/audit/behavior", summary="获取行为审计日志")
    async def behavior_logs(limit: int = 50):
        loip = get_loip()
        return {"ok": True, "logs": loip.audit.behavior_log[-limit:]}

    @app.get("/api/v1/audit/cognitive", summary="获取认知审计日志")
    async def cognitive_logs(limit: int = 50):
        loip = get_loip()
        return {"ok": True, "logs": loip.audit.cognitive_log[-limit:]}

    # ===== 监控接口 =====

    @app.get("/console", summary="LOIP Console 管理后台")
    async def console():
        """LOIP Console 可视化管理后台"""
        console_path = os.path.join(os.path.dirname(__file__), "console.html")
        if os.path.exists(console_path):
            from fastapi.responses import HTMLResponse
            with open(console_path, 'r', encoding='utf-8') as f:
                return HTMLResponse(content=f.read())
        raise HTTPException(status_code=404, detail="Console页面未找到")

    @app.get("/health", summary="健康检查")
    async def health():
        loip = get_loip()
        integrity = loip.verify_integrity()
        return {
            "status": "healthy",
            "version": __version__,
            "backend": _config.get("backend"),
            "baseline_locked": loip.baseline.is_locked(),
            "processing_count": loip.processing_count,
            "baseline_integrity": integrity["baseline_integrity"]["integrity"],
            "audit_chain_valid": all(v["valid"] for v in integrity["audit_hash_chain"].values()),
            "uptime": _config.get("started_at")
        }

    @app.get("/api/v1/status", summary="获取完整运行状态")
    async def status():
        loip = get_loip()
        return {"ok": True, "status": loip.get_status()}

    @app.get("/api/v1/stats", summary="获取治理统计数据")
    async def stats():
        loip = get_loip()
        return {
            "ok": True,
            "drift_stats": loip.drift_detector.get_drift_stats(),
            "hallucination_stats": loip.hallucination_guard.get_stats(),
            "audit_summary": loip.audit.get_summary(),
            "processing_count": loip.processing_count
        }

    return app


# 默认应用实例（用于uvicorn直接启动）
app = create_app()


def main():
    """命令行启动入口"""
    parser = argparse.ArgumentParser(description="LOIP REST API 服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--baseline", default="./loip_baseline.json", help="基线文件路径")
    parser.add_argument("--audit-dir", default="./loip_audit", help="审计日志目录")
    parser.add_argument("--backend", default="auto", choices=["auto", "keyword", "semantic"],
                        help="检测后端")
    args = parser.parse_args()

    global app, _loip_instance
    app = create_app(args.baseline, args.audit_dir, args.backend)

    import uvicorn
    print(f"[LOIP] API服务启动: http://{args.host}:{args.port}")
    print(f"[LOIP] API文档: http://{args.host}:{args.port}/docs")
    print(f"[LOIP] 基线文件: {args.baseline}")
    print(f"[LOIP] 检测后端: {args.backend}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
