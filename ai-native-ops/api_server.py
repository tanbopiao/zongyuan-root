"""
ANCE API Server - AI原生云运维引擎HTTP服务
端口: 8002
"""
import sys, os, json, hashlib, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from core.intent_parser import parse_intent
from core.planner import plan_deployment
from core.verifier import Verifier
from core.healer import Healer
from core.truth_engine import TruthEngine
from generators.iac_generator import IacGenerator

app = FastAPI(title="ANCE AI-Native Cloud Ops Engine", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

truth_engine = TruthEngine(cache_dir=os.path.join(os.path.dirname(__file__), "truth_cache"))
healer = Healer()

class DeployRequest(BaseModel):
    prompt: str
    execute: bool = False
    host: Optional[str] = None
    ssh_key: Optional[str] = None

class VerifyRequest(BaseModel):
    host: str = "127.0.0.1"
    domain: Optional[str] = None
    ports: Optional[list] = None
    ssl: bool = False

class HealRequest(BaseModel):
    error: str
    context: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok", "service": "ance-api", "version": "1.0.0", "timestamp": int(time.time())}

@app.post("/api/v1/deploy")
def deploy(req: DeployRequest):
    """自然语言部署：意图解析→规划→IaC生成"""
    t0 = time.time()
    plan = parse_intent(req.prompt)
    dag = plan_deployment(plan)
    gen = IacGenerator(output_dir="/tmp/ance_output")
    artifacts = gen.generate_all(plan)
    
    result = {
        "intent": plan.to_dict(),
        "dag": {"steps": len(dag.steps), "details": [{"id": s.step_id, "desc": s.description, "deps": s.depends_on} for s in dag.steps]},
        "iac_artifacts": {k: list(v.keys()) for k, v in artifacts.items()},
        "execution": "skipped (execute=false)" if not req.execute else "pending",
        "elapsed_ms": int((time.time() - t0) * 1000)
    }
    return result

@app.post("/api/v1/verify")
def verify(req: VerifyRequest):
    """服务器验证：端口/HTTP/SSL"""
    v = Verifier(host=req.host)
    results = []
    ports = req.ports or [80, 443, 8000, 8001]
    for p in ports:
        r = v.verify_port(p)
        results.append({"port": p, "passed": r.passed, "detail": r.detail})
    if req.domain:
        r = v.verify_http(f"https://{req.domain}")
        results.append({"type": "https", "domain": req.domain, "passed": r.passed, "detail": r.detail})
    return {"host": req.host, "results": results, "all_passed": all(r["passed"] for r in results)}

@app.post("/api/v1/heal")
def heal(req: HealRequest):
    """错误诊断与自动修复建议"""
    results = healer.heal(req.error)
    return {
        "error": req.error,
        "diagnoses": [{"severity": r.severity, "name": r.error_name, "detail": r.detail, "fix_command": r.fix_command} for r in results],
        "count": len(results)
    }

@app.get("/api/v1/truth")
def truth_list():
    """真值查询"""
    return truth_engine.get_stats()

@app.post("/api/v1/truth/recall")
def truth_recall(query: dict):
    """真值召回（基于部署计划模式匹配）"""
    q = query.get("query", "")
    plan = parse_intent(q)
    try:
        results = truth_engine.recall(plan)
        if results:
            return {"query": q, "matched": True, "pattern": results.pattern, "reuse_count": results.reuse_count}
    except Exception as e:
        pass
    return {"query": q, "matched": False, "message": "无匹配真值"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, workers=1)
