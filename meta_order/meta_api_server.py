"""元秩序统一API - /api/v1/meta/health 等端点"""
import json, sys, os
sys.path.insert(0, '/opt/ZONGYUAN-ROOT/meta_order')
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from health_aggregator import aggregate
from stability_scorer import compute_stability
from meta_constitution_validator import check_constitution_integrity
from quad_anchor_engine import audit_anchor_chain

app = FastAPI(title="ZONGYUAN-ROOT Meta Order API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])



@app.get("/health")
async def health():
    return {"status": "healthy", "service": "meta", "version": "v1.0"}

@app.get("/status")
async def status():
    return {"service": "meta", "version": "v1.0", "status": "running"}
@app.get("/api/v1/meta/health")
def meta_health():
    health = aggregate()
    stability = compute_stability()
    constitution = check_constitution_integrity()
    anchor = audit_anchor_chain()
    return {
        "timestamp": health["timestamp"],
        "overall": health["overall"],
        "stability": stability,
        "meta_constitution": constitution,
        "anchor_chain": {"complete": anchor["anchor_chain_complete"], "violations": anchor["violation_count"]},
        "services": health["services"],
        "resources": health["resources"],
        "truth": health["truth"],
        "kernel": health["kernel"]
    }

@app.get("/api/v1/meta/stability")
def meta_stability():
    return compute_stability()

@app.get("/api/v1/meta/constitution")
def meta_constitution():
    return check_constitution_integrity()

@app.get("/api/v1/meta/anchor")
def meta_anchor():
    return audit_anchor_chain()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
