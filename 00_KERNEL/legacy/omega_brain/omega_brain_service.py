#!/usr/bin/env python3
"""
Ω-Brainμ 自治内核 FastAPI 常驻服务
动作1: 真值基座全量内存加载，API网关，任务调度
启动: uvicorn omega_brain_service:app --host 0.0.0.0 --port 8765 --workers 1
"""
import json
import hashlib
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
app = FastAPI(title="Ω-Brainμ Autonomous Kernel", version="1.1.0")

# ============ 启动时全量加载到内存（零IO查询） ============
MEMORY = {
    "truth_base": {},
    "kernel_protocol": {},
    "templates": {},
    "asset_index": {},
    "config": {},
    "loaded_at": None
}

def load_all_to_memory():
    """启动时全量加载真值基座+协议+模板+配置到内存"""
    # 加载最新真值基座
    truth_dir = ROOT / "truth_base"
    if truth_dir.exists():
        for fp in sorted(truth_dir.glob("*.json")):
            with open(fp) as f:
                MEMORY["truth_base"][fp.name] = json.load(f)
    # 加载最新内核协议
    proto_dir = ROOT / "autonomous_kernel_protocol"
    if proto_dir.exists():
        protos = sorted(proto_dir.glob("*.json"))
        if protos:
            with open(protos[-1]) as f:
                MEMORY["kernel_protocol"] = json.load(f)
    # 加载模板库
    tpl = ROOT / "templates" / "prompt" / "template_library.json"
    if tpl.exists():
        with open(tpl) as f:
            MEMORY["templates"] = json.load(f)
    # 加载配置
    cfg = ROOT / "config" / "omega_brain_config_v1.1.json"
    if cfg.exists():
        with open(cfg) as f:
            MEMORY["config"] = json.load(f)
    # 构建资产索引
    MEMORY["asset_index"] = build_asset_index()
    MEMORY["loaded_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    return len(MEMORY["truth_base"]), len(MEMORY["asset_index"])

def build_asset_index():
    """构建全量资产索引（SHA256+路径+域）"""
    index = {}
    for fp in ROOT.rglob("*"):
        if fp.is_file() and "cache" not in str(fp):
            rel = str(fp.relative_to(ROOT))
            h = hashlib.sha256()
            with open(fp, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            index[rel] = {"sha256": h.hexdigest(), "size": fp.stat().st_size,
                          "domain": rel.split("/")[0]}
    return index

@app.on_event("startup")
async def startup_event():
    n_truth, n_assets = load_all_to_memory()
    print(f"[Ω-Brainμ] 内存加载完成: {n_truth}真值文件, {n_assets}件资产索引")

# ============ API 端点 ============
class TaskRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any]
    priority: Optional[str] = "normal"

@app.get("/")
async def root():
    return {"service": "Ω-Brainμ", "status": "running", "loaded_at": MEMORY["loaded_at"],
            "truth_files": len(MEMORY["truth_base"]), "assets_indexed": len(MEMORY["asset_index"])}

@app.get("/health")
async def health():
    return {"status": "healthy", "kernel": "Ω-Brainμ v1.1", "memory_loaded": bool(MEMORY["loaded_at"])}

@app.get("/truth/base")
async def get_truth_base():
    """获取全量真值基座（内存直接返回，零IO）"""
    return {"truth_base": MEMORY["truth_base"], "source": "memory"}

@app.get("/truth/formulas")
async def get_formulas():
    """获取真值公式列表"""
    formulas = []
    for name, data in MEMORY["truth_base"].items():
        if "formulas" in data:
            formulas.extend(data["formulas"])
        if "truth_formulas" in data:
            formulas.extend(data["truth_formulas"])
    return {"count": len(formulas), "formulas": formulas}

@app.get("/kernel/protocol")
async def get_kernel_protocol():
    return {"protocol": MEMORY["kernel_protocol"]}

@app.get("/templates")
async def get_templates():
    return {"templates": MEMORY["templates"]}

@app.get("/assets")
async def list_assets(domain: Optional[str] = None):
    if domain:
        filtered = {k: v for k, v in MEMORY["asset_index"].items() if v["domain"] == domain}
        return {"count": len(filtered), "assets": filtered}
    return {"count": len(MEMORY["asset_index"]), "assets": MEMORY["asset_index"]}

@app.get("/assets/{asset_path:path}")
async def get_asset(asset_path: str):
    if asset_path in MEMORY["asset_index"]:
        return MEMORY["asset_index"][asset_path]
    raise HTTPException(status_code=404, detail="Asset not found")

@app.post("/task/submit")
async def submit_task(req: TaskRequest):
    """提交任务到调度队列"""
    task_id = hashlib.sha256(f"{req.task_type}{time.time()}".encode()).hexdigest()[:16]
    return {"task_id": task_id, "status": "queued", "type": req.task_type, "priority": req.priority}

@app.get("/config")
async def get_config():
    return {"config": MEMORY["config"]}

@app.post("/reload")
async def reload_memory():
    """热重载内存数据"""
    n_truth, n_assets = load_all_to_memory()
    return {"status": "reloaded", "truth_files": n_truth, "assets": n_assets}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765, workers=1)
