"""
内核状态锚定服务
端口: 8006
功能：任务开始前锚定内核状态，防止重复劳动和任务冲突
"""
import os, json, time, hashlib, subprocess
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="内核状态锚定服务", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# V7.0: 内核自治调度器（内置cron，不依赖外部crontab）
try:
    import sys
    sys.path.insert(0, "/opt/ZONGYUAN-ROOT")
    from autonomous_scheduler import scheduler as auto_scheduler
    auto_scheduler.start()
    SCHEDULER_ENABLED = True
except Exception as e:
    SCHEDULER_ENABLED = False
    print(f"[WARN] 自治调度器启动失败: {e}")

STATE_FILE = "/opt/ZONGYUAN-ROOT/kernel_state.json"
REGISTRY_FILE = "/opt/ZONGYUAN-ROOT/task_registry.json"
INSTALL_DIR = "/opt/ZONGYUAN-ROOT"
ROOT = Path(INSTALL_DIR)

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

class TaskCheckRequest(BaseModel):
    task_name: str
    task_description: Optional[str] = ""
    target_port: Optional[int] = None
    target_route: Optional[str] = ""

class TaskRegisterRequest(BaseModel):
    task_name: str
    description: str
    protocol_version: str
    artifacts: List[str] = []
    hash: str = ""

@app.get("/health")
def health():
    return {"status": "ok", "service": "kernel-anchor", "version": "1.0.0", "scheduler": "running" if SCHEDULER_ENABLED else "disabled"}

@app.get("/api/v1/dashboard")
def dashboard():
    """云内核可视化控制台聚合数据"""
    import os, json, hashlib, time
    from pathlib import Path
    ROOT = Path("/opt/ZONGYUAN-ROOT")
    
    # 1. 服务状态
    services = {}
    for svc in ["omega-brain", "loip", "ance", "vector", "monitor", "gov-ai", "anchor"]:
        try:
            r = os.popen("systemctl is-active zongyuan-%s" % svc).read().strip()
            services[svc] = r
        except:
            services[svc] = "unknown"
    
    # 2. 协议统计
    proto_dir = ROOT / "autonomous_kernel_protocol"
    protos = sorted(proto_dir.glob("*.json")) if proto_dir.exists() else []
    latest_proto = protos[-1].stem.replace("AUTOKERN-PROTO-", "") if protos else "none"
    
    # 3. 真值统计
    truth_dir = ROOT / "truth_architecture"
    truths = list(truth_dir.glob("*.json")) if truth_dir.exists() else []
    omega_idx = ROOT / "Ω-Brainμ" / "truth_index.json"
    omega_count = 0
    if omega_idx.exists():
        try:
            omega_count = json.loads(omega_idx.read_text()).get("truth_count", 0)
            omega_version = json.loads(omega_idx.read_text()).get("version", "unknown")
        except: pass
    
    # 4. 系统资源
    mem = os.popen("free -m | grep Mem").read().split()
    disk = os.popen("df -h / | tail -1").read().split()
    load = os.popen("cat /proc/loadavg").read().split()[0]
    
    # 5. LLM路由
    env_file = ROOT / ".env"
    llm_router = {}
    if env_file.exists():
        env_text = env_file.read_text()
        llm_router["doubao"] = "active" if "DOUBAO_API_KEY" in env_text else "not_configured"
        llm_router["zhipu"] = "configured" if "ZHIPU" in env_text or "GLM" in env_text else "not_configured"
        llm_router["hunyuan"] = "configured" if "HUNYUAN_API_KEY" in env_text else "not_configured"
        llm_router["nvidia_nim"] = "configured" if "NVIDIA_API_KEY" in env_text else "not_configured"
    
    # 6. 锁档状态
    lock_manifests = list(ROOT.glob("GLOBAL-LOCK-MANIFEST-*.json"))
    latest_lock = None
    if lock_manifests:
        try:
            latest_lock = json.loads(sorted(lock_manifests)[-1].read_text())
        except: pass
    
    # 7. META-CORE状态
    meta_core = ROOT / "truth_architecture" / "META-CORE-TRUTH-V1.0.json"
    meta_status = "active" if meta_core.exists() else "not_found"
    
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "kernel_id": "ZONGYUAN-ROOT-AUTONOMOUS-KERNEL",
        "did": "DID-BR-000002",
        "sovereign_root": "Ω-TAN-7-001",
        "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
        "services": services,
        "services_active": sum(1 for v in services.values() if v == "active"),
        "services_total": len(services),
        "protocols": {
            "total": len(protos),
            "latest": latest_proto
        },
        "truths": {
            "files": len(truths),
            "omega_brain_count": omega_count,
            "meta_core": meta_status
        },
        "system": {
            "cpu_load": float(load),
            "memory_used_mb": int(mem[2]) if len(mem) > 2 else 0,
            "memory_total_mb": int(mem[1]) if len(mem) > 1 else 0,
            "memory_percent": round(int(mem[2])/int(mem[1])*100, 1) if len(mem) > 2 else 0,
            "disk_used": disk[2] if len(disk) > 2 else "?",
            "disk_total": disk[1] if len(disk) > 1 else "?",
            "disk_percent": disk[4] if len(disk) > 4 else "?"
        },
        "llm_router": llm_router,
        "lock": {
            "manifests": len(lock_manifests),
            "latest": latest_lock.get("lock_id") if latest_lock else None,
            "merkle_root": latest_lock.get("merkle_root") if latest_lock else None,
            "total_assets": latest_lock.get("total_assets") if latest_lock else 0
        },
        "semantic_recall": {
            "endpoint": "/api/v1/omega/recall",
            "engine": "local_tfidf_five_dim_router_v2",
            "status": "active"
        }
    }


@app.get("/api/v1/scheduler/status")
def scheduler_status():
    """V7.0: 自治调度器状态查询"""
    if not SCHEDULER_ENABLED:
        return {"scheduler": "disabled", "reason": "启动失败或未安装"}
    try:
        return auto_scheduler.get_status()
    except Exception as e:
        return {"scheduler": "error", "detail": str(e)}

@app.get("/api/v1/anchor/state")
def get_state():
    """获取内核当前完整状态快照"""
    state = load_json(STATE_FILE)
    if not state:
        return {"error": "内核状态文件不存在", "state": {}}
    return {
        "kernel_id": state.get("kernel_id"),
        "did": state.get("did"),
        "last_updated": state.get("last_updated"),
        "server": state.get("server"),
        "services_running": len([s for s in state.get("services", []) if s.get("status") == "running"]),
        "services_total": len(state.get("services", [])),
        "services": state.get("services"),
        "api_endpoints": state.get("api_endpoints"),
        "nginx_routes": state.get("nginx_routes"),
        "assets": state.get("assets"),
        "security": state.get("security"),
        "known_issues": state.get("known_issues"),
        "todo_backlog": state.get("todo_backlog"),
        "latest_protocol": state.get("latest_protocol"),
        "registry_version": state.get("registry_version")
    }

@app.get("/api/v1/anchor/tasks")
def get_tasks(limit: int = 20):
    """获取任务谱系"""
    reg = load_json(REGISTRY_FILE)
    tasks = reg.get("tasks", [])
    return {
        "total": reg.get("total_tasks", len(tasks)),
        "recent_tasks": tasks[-limit:],
        "port_allocation": reg.get("port_allocation"),
        "conflict_rules": reg.get("conflict_rules")
    }

@app.post("/api/v1/anchor/check")
def check_task(req: TaskCheckRequest):
    """
    任务开始前冲突检测：
    1. 检测是否与已有任务重复
    2. 检测端口冲突
    3. 检测路由冲突
    4. 返回建议（增量执行 or 新建）
    """
    state = load_json(STATE_FILE)
    reg = load_json(REGISTRY_FILE)
    tasks = reg.get("tasks", [])
    
    issues = []
    suggestions = []
    
    # 1. 重复任务检测（关键词匹配）
    keywords = set(req.task_name.lower().split())
    duplicate_tasks = []
    for t in tasks:
        if t.get("status") == "completed":
            task_words = set(t.get("name", "").lower().split())
            overlap = keywords & task_words
            if len(overlap) >= 2:
                duplicate_tasks.append({"task_id": t["task_id"], "name": t["name"], "overlap": list(overlap)})
    
    if duplicate_tasks:
        issues.append({
            "level": "P1",
            "type": "potential_duplicate",
            "message": f"检测到{len(duplicate_tasks)}个可能重复的已完成任务",
            "details": duplicate_tasks,
            "suggestion": "建议先读取已有任务产物，采用增量优化而非从零构建"
        })
    
    # 2. 端口冲突检测
    if req.target_port:
        used_ports = [s["port"] for s in state.get("services", []) if s.get("status") == "running"]
        if req.target_port in used_ports:
            svc = next((s for s in state["services"] if s["port"] == req.target_port), {})
            issues.append({
                "level": "P0",
                "type": "port_conflict",
                "message": f"端口{req.target_port}已被占用: {svc.get('name', '未知')}",
                "suggestion": f"使用可用端口: {reg.get('port_allocation', {}).get('next_available', [])}"
            })
    
    # 3. 路由冲突检测
    if req.target_route:
        routes = state.get("nginx_routes", {})
        for existing_route in routes:
            if req.target_route.startswith(existing_route) or existing_route.startswith(req.target_route):
                issues.append({
                    "level": "P0",
                    "type": "route_conflict",
                    "message": f"路由{req.target_route}与已有路由{existing_route}冲突",
                    "suggestion": "使用不同的路由前缀"
                })
    
    # 4. 已知问题提醒
    pending_issues = [i for i in state.get("known_issues", []) if i.get("status") == "pending"]
    if pending_issues:
        suggestions.append({
            "type": "pending_issues",
            "message": f"当前有{len(pending_issues)}个待解决问题",
            "details": pending_issues
        })
    
    # 5. 待办提醒
    backlog = state.get("todo_backlog", [])
    if backlog:
        suggestions.append({
            "type": "backlog",
            "message": "当前待办列表",
            "details": backlog
        })
    
    can_proceed = not any(i["level"] == "P0" for i in issues)
    
    return {
        "task_name": req.task_name,
        "can_proceed": can_proceed,
        "issues": issues,
        "suggestions": suggestions,
        "current_state_summary": {
            "services_running": len([s for s in state.get("services", []) if s.get("status") == "running"]),
            "latest_protocol": state.get("latest_protocol"),
            "vector_docs": state.get("assets", {}).get("vector_docs", 0),
            "known_issues": len(pending_issues)
        },
        "anchor_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.post("/api/v1/anchor/register")
def register_task(req: TaskRegisterRequest):
    """任务完成后注册到任务谱系"""
    reg = load_json(REGISTRY_FILE)
    tasks = reg.get("tasks", [])
    
    new_id = f"TASK-{len(tasks)+1:03d}"
    task_hash = req.hash or hashlib.sha256(f"{req.task_name}{time.time()}".encode()).hexdigest()[:16]
    
    new_task = {
        "task_id": new_id,
        "name": req.task_name,
        "date": time.strftime("%Y-%m-%d"),
        "status": "completed",
        "protocol": req.protocol_version,
        "artifacts": req.artifacts,
        "hash": task_hash,
        "description": req.description
    }
    tasks.append(new_task)
    reg["tasks"] = tasks
    reg["total_tasks"] = len(tasks)
    save_json(REGISTRY_FILE, reg)
    
    return {"status": "registered", "task_id": new_id, "hash": task_hash, "total_tasks": len(tasks)}

@app.post("/api/v1/anchor/update-state")
def update_state(state_update: dict):
    """更新内核状态快照（任务完成后调用）"""
    state = load_json(STATE_FILE)
    if not state:
        state = {}
    state.update(state_update)
    state["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    save_json(STATE_FILE, state)
    return {"status": "updated", "last_updated": state["last_updated"]}

@app.get("/api/v1/anchor/summary")
def get_summary():
    """快速摘要（任务开始前一键获取）"""
    state = load_json(STATE_FILE)
    reg = load_json(REGISTRY_FILE)
    return {
        "kernel": state.get("kernel_id"),
        "latest_protocol": state.get("latest_protocol"),
        "services": f"{len([s for s in state.get('services',[]) if s.get('status')=='running'])}/{len(state.get('services',[]))} 运行中",
        "vector_docs": state.get("assets", {}).get("vector_docs"),
        "total_tasks": reg.get("total_tasks"),
        "pending_issues": len([i for i in state.get("known_issues",[]) if i.get("status")=="pending"]),
        "next_ports": reg.get("port_allocation", {}).get("next_available", []),
        "access_urls": state.get("api_endpoints", {})
    }

@app.get("/api/v1/sync/manifest")
def sync_manifest():
    """主内核资产清单：返回所有可同步文件的版本+哈希+Merkle根"""
    state = load_json(STATE_FILE)
    sync_dirs = ["autonomous_kernel_protocol", "truth_architecture"]
    files = []
    for d in sync_dirs:
        dirpath = os.path.join(INSTALL_DIR, d)
        if os.path.exists(dirpath):
            for fname in sorted(os.listdir(dirpath)):
                fpath = os.path.join(dirpath, fname)
                if os.path.isfile(fpath) and fname.endswith(('.json', '.md')):
                    h = hashlib.sha256(open(fpath, 'rb').read()).hexdigest()
                    files.append({"path": f"{d}/{fname}", "sha256": h, "size": os.path.getsize(fpath), "mtime": os.path.getmtime(fpath)})
    all_hashes = sorted([f["sha256"] for f in files])
    merkle = hashlib.sha256(''.join(all_hashes).encode()).hexdigest()
    return {
        "kernel_id": state.get("kernel_id"),
        "latest_protocol": state.get("latest_protocol"),
        "registry_version": state.get("registry_version"),
        "total_files": len(files),
        "merkle_root": merkle,
        "files": files,
        "sync_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    }

class SyncPullRequest(BaseModel):
    files: List[str]

@app.post("/api/v1/sync/pull")
def sync_pull(req: SyncPullRequest):
    """从主内核拉取指定文件内容（BASE64编码）"""
    import base64
    result = []
    for fpath in req.files:
        full = os.path.join(INSTALL_DIR, fpath)
        if os.path.exists(full) and os.path.isfile(full):
            content = base64.b64encode(open(full, 'rb').read()).decode()
            h = hashlib.sha256(open(full, 'rb').read()).hexdigest()
            result.append({"path": fpath, "content_b64": content, "sha256": h, "size": os.path.getsize(full)})
        else:
            result.append({"path": fpath, "error": "not_found"})
    return {"pulled": len([r for r in result if "content_b64" in r]), "files": result}

@app.post("/api/v1/sync/verify")
def sync_verify(local_manifest: dict):
    """验证从内核与主内核一致性，返回差异列表"""
    master = sync_manifest()
    master_files = {f["path"]: f["sha256"] for f in master["files"]}
    local_files = {f["path"]: f["sha256"] for f in local_manifest.get("files", [])}
    added = [p for p in master_files if p not in local_files]
    modified = [p for p in master_files if p in local_files and master_files[p] != local_files[p]]
    removed = [p for p in local_files if p not in master_files]
    consistent = len(added) == 0 and len(modified) == 0
    return {
        "consistent": consistent,
        "master_protocol": master["latest_protocol"],
        "master_merkle": master["merkle_root"],
        "diff": {"added": added, "modified": modified, "removed": removed},
        "summary": f"新增{len(added)} 修改{len(modified)} 本地独有{len(removed)}"
    }


@app.get("/api/v1/sync/handshake")
def sync_handshake():
    """握手端点: 返回云内核精简状态,用于本地内核判断是否需要同步"""
    state = load_json(STATE_FILE)
    omega_idx = ROOT / "Ω-Brainμ" / "truth_index.json"
    omega_data = json.loads(omega_idx.read_text()) if omega_idx.exists() else {}
    return {
        "kernel_id": state.get("kernel_id"),
        "did": state.get("did", "DID-BR-000002"),
        "truth_version": omega_data.get("version", "unknown"),
        "truth_count": omega_data.get("truth_count", 0),
        "protocol_count": len(list((ROOT / "autonomous_kernel_protocol").glob("*.json"))) if (ROOT / "autonomous_kernel_protocol").exists() else 0,
        "merkle_root": state.get("merkle_root", ""),
        "services_active": sum(1 for s in ["omega-brain","loip","ance","vector","monitor","gov-ai","anchor"] if subprocess.run(["systemctl","is-active",f"zongyuan-{s}"],capture_output=True,text=True).stdout.strip()=="active"),
        "services_total": state.get("services_total", 7),
        "latest_protocol": state.get("latest_protocol"),
        "memory_chain_seeds": len(list((ROOT / "memory_chain").glob("seed-*.json"))) if (ROOT / "memory_chain").exists() else 0,
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "sync_endpoints": {
            "manifest": "/api/v1/sync/manifest",
            "pull": "/api/v1/sync/pull",
            "verify": "/api/v1/sync/verify",
            "truth_pull": "/api/v1/sync/truth-pull",
            "truth_push": "/api/v1/sync/truth-push"
        }
    }


class TruthPullRequest(BaseModel):
    since_version: str = ""
    ids: List[str] = []


@app.post("/api/v1/sync/truth-pull")
def sync_truth_pull(req: TruthPullRequest):
    """拉取真值增量: 返回指定版本之后新增的真值"""
    omega_idx = ROOT / "Ω-Brainμ" / "truth_index.json"
    if not omega_idx.exists():
        return {"error": "truth_index not found", "truths": []}
    data = json.loads(omega_idx.read_text())
    all_truths = data.get("truths", [])
    # 如果指定了ids,只返回这些
    if req.ids:
        result = [t for t in all_truths if t.get("id") in req.ids]
    else:
        result = all_truths  # 全量返回,本地端自行比对
    return {
        "version": data.get("version"),
        "total": len(all_truths),
        "returned": len(result),
        "truths": result
    }


class TruthPushRequest(BaseModel):
    truths: List[dict]
    source: str = "local_kernel"
    signature: str = ""


@app.post("/api/v1/sync/truth-push")
def sync_truth_push(req: TruthPushRequest):
    """本地内核推送新真值到云Ω-Brainμ(带去重)"""
    omega_idx = ROOT / "Ω-Brainμ" / "truth_index.json"
    if not omega_idx.exists():
        return {"error": "truth_index not found", "added": 0}
    data = json.loads(omega_idx.read_text())
    existing_ids = {t.get("id") for t in data.get("truths", [])}
    added = []
    for t in req.truths:
        tid = t.get("id")
        if tid and tid not in existing_ids:
            t["source"] = req.source
            t["pushed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
            data["truths"].append(t)
            existing_ids.add(tid)
            added.append(tid)
    data["truth_count"] = len(data["truths"])
    data["last_sync"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    omega_idx.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return {
        "added": len(added),
        "added_ids": added,
        "total_after": data["truth_count"],
        "status": "ok"
    }


class RecallRequest(BaseModel):
    query: str
    top_k: int = 8


@app.post("/api/v1/omega/recall")
def omega_recall(req: RecallRequest):
    """Ω-Brainμ语义召回：TF-IDF + 五维路由"""
    try:
        import sys
        sys.path.insert(0, "/opt/ZONGYUAN-ROOT")
        from local_semantic_recall import LocalSemanticRecall
        engine = LocalSemanticRecall()
        return engine.recall(req.query, top_k=req.top_k)
    except Exception as e:
        return {"error": str(e), "query": req.query}


@app.get("/api/v1/dashboard")
def dashboard():
    """云内核可视化控制台聚合数据"""
    import os, json, time
    from pathlib import Path
    ROOT = Path("/opt/ZONGYUAN-ROOT")
    services = {}
    for svc in ["omega-brain", "loip", "ance", "vector", "monitor", "gov-ai", "anchor"]:
        try:
            services[svc] = os.popen("systemctl is-active zongyuan-%s" % svc).read().strip()
        except:
            services[svc] = "unknown"
    proto_dir = ROOT / "autonomous_kernel_protocol"
    protos = sorted(proto_dir.glob("*.json")) if proto_dir.exists() else []
    latest_proto = protos[-1].stem.replace("AUTOKERN-PROTO-", "") if protos else "none"
    truth_dir = ROOT / "truth_architecture"
    truths = list(truth_dir.glob("*.json")) if truth_dir.exists() else []
    omega_idx = ROOT / "Ω-Brainμ" / "truth_index.json"
    omega_count = 0
    if omega_idx.exists():
        try:
            omega_count = json.loads(omega_idx.read_text()).get("truth_count", 0)
            omega_version = json.loads(omega_idx.read_text()).get("version", "unknown")
        except: pass
    mem = os.popen("free -m | grep Mem").read().split()
    disk = os.popen("df -h / | tail -1").read().split()
    load = os.popen("cat /proc/loadavg").read().split()[0]
    env_file = ROOT / ".env"
    llm_router = {}
    if env_file.exists():
        env_text = env_file.read_text()
        llm_router["doubao"] = "active" if "DOUBAO" in env_text else "not_configured"
        llm_router["zhipu"] = "configured" if "ZHIPU" in env_text or "GLM" in env_text else "not_configured"
        llm_router["hunyuan"] = "configured" if "HUNYUAN_API_KEY" in env_text else "not_configured"
        llm_router["nvidia_nim"] = "configured" if "NVIDIA_API_KEY" in env_text else "not_configured"
    lock_manifests = list(ROOT.glob("GLOBAL-LOCK-MANIFEST-*.json"))
    latest_lock = None
    if lock_manifests:
        try:
            latest_lock = json.loads(sorted(lock_manifests)[-1].read_text())
        except: pass
    meta_core = ROOT / "truth_architecture" / "META-CORE-TRUTH-V1.0.json"
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "kernel_id": "ZONGYUAN-ROOT-AUTONOMOUS-KERNEL",
        "did": "DID-BR-000002",
        "sovereign_root": "Ω-TAN-7-001",
        "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
        "services": services,
        "services_active": sum(1 for v in services.values() if v == "active"),
        "services_total": len(services),
        "protocols": {"total": len(protos), "latest": latest_proto},
        "truths": {"files": len(truths), "omega_brain_count": omega_count, "omega_brain_version": omega_version, "meta_core": "active" if meta_core.exists() else "not_found"},
        "system": {
            "cpu_load": float(load),
            "memory_used_mb": int(mem[2]) if len(mem) > 2 else 0,
            "memory_total_mb": int(mem[1]) if len(mem) > 1 else 0,
            "memory_percent": round(int(mem[2])/int(mem[1])*100, 1) if len(mem) > 2 else 0,
            "disk_used": disk[2] if len(disk) > 2 else "?",
            "disk_total": disk[1] if len(disk) > 1 else "?",
            "disk_percent": disk[4] if len(disk) > 4 else "?"
        },
        "llm_router": llm_router,
        "lock": {
            "manifests": len(lock_manifests),
            "latest": latest_lock.get("lock_id") if latest_lock else None,
            "merkle_root": latest_lock.get("merkle_root") if latest_lock else None,
            "total_assets": latest_lock.get("total_assets") if latest_lock else 0
        },
        "semantic_recall": {"endpoint": "/api/v1/omega/recall", "engine": "local_tfidf_five_dim_router_v2", "status": "active"}
    }



@app.get("/api/v1/harness/capabilities")
def harness_capabilities():
    """豆包基座高阶能力清单"""
    try:
        import sys
        sys.path.insert(0, "/opt/ZONGYUAN-ROOT")
        from doubao_harness import DoubaoHarness
        return DoubaoHarness().capabilities()
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/v1/harness/chat")
def harness_chat(req: dict):
    """豆包基座对话（通用/Agent模型）"""
    try:
        import sys
        sys.path.insert(0, "/opt/ZONGYUAN-ROOT")
        from doubao_harness import DoubaoHarness
        h = DoubaoHarness()
        messages = req.get("messages", [{"role": "user", "content": req.get("query", "ping")}])
        model = req.get("model")
        return h.chat(messages, model=model)
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/v1/harness/embed")
def harness_embed(req: dict):
    """豆包多模态向量化（2048维）"""
    try:
        import sys
        sys.path.insert(0, "/opt/ZONGYUAN-ROOT")
        from doubao_harness import DoubaoHarness
        return DoubaoHarness().embed(req.get("text", ""), dimensions=req.get("dimensions", 2048))
    except Exception as e:
        return {"error": str(e)}



# ============ 云控本地内核端点 ============
CONTROL_FILE = ROOT / "control_commands.json"
CONTROL_RESULT_FILE = ROOT / "control_results.json"

def _load_control():
    if CONTROL_FILE.exists():
        return json.loads(CONTROL_FILE.read_text())
    return {"pending": {}, "completed": {}}

def _save_control(data):
    CONTROL_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

@app.post("/api/v1/control/heartbeat")
async def control_heartbeat(req: dict):
    """本地节点心跳注册"""
    node_id = req.get("node_id", "unknown")
    commands = _load_control()
    pending = [c for c in commands["pending"].values()
               if c.get("target_node") in [node_id, "all"]
               and c.get("status") == "pending"]
    return {
        "node_id": node_id,
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "pending_commands": len(pending),
        "next_poll_interval": 30,
        "config_version": "v2.3",
        "truth_version": omega_data.get("version", "unknown") if 'omega_data' in dir() else "unknown"
    }

@app.get("/api/v1/control/commands")
async def control_fetch_commands(node_id: str = "unknown"):
    """本地节点拉取待执行指令"""
    commands = _load_control()
    pending = []
    for cid, cmd in commands["pending"].items():
        if cmd.get("target_node") in [node_id, "all"] and cmd.get("status") == "pending":
            cmd["status"] = "dispatched"
            cmd["dispatched_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
            pending.append(cmd)
    _save_control(commands)
    return {"commands": pending}

@app.post("/api/v1/control/result")
async def control_result(req: dict):
    """本地节点回报执行结果"""
    cmd_id = req.get("cmd_id", "")
    commands = _load_control()
    if cmd_id in commands["pending"]:
        cmd = commands["pending"].pop(cmd_id)
        cmd["status"] = req.get("status", "unknown")
        cmd["result"] = req.get("result")
        cmd["executed_at"] = req.get("executed_at")
        cmd["node_id"] = req.get("node_id")
        commands["completed"][cmd_id] = cmd
        _save_control(commands)
    return {"received": True, "cmd_id": cmd_id}

@app.post("/api/v1/control/issue")
async def control_issue(req: dict):
    """管理员下发指令"""
    cmd_id = f"CMD-{time.strftime('%Y%m%d%H%M%S')}-{os.urandom(2).hex()}"
    cmd = {
        "cmd_id": cmd_id,
        "type": req.get("type", "config_update"),
        "priority": req.get("priority", "P1"),
        "payload": req.get("payload", {}),
        "target_node": req.get("target_node", "all"),
        "status": "pending",
        "issued_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    }
    commands = _load_control()
    commands["pending"][cmd_id] = cmd
    _save_control(commands)
    return {"cmd_id": cmd_id, "status": "queued", "target_node": cmd["target_node"]}

@app.get("/api/v1/control/status")
async def control_status():
    """查看指令队列状态"""
    commands = _load_control()
    pending_count = len(commands["pending"])
    completed_count = len(commands["completed"])
    recent = list(commands["completed"].values())[-5:]
    return {
        "pending": pending_count,
        "completed": completed_count,
        "recent_completed": recent
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006, workers=1)


