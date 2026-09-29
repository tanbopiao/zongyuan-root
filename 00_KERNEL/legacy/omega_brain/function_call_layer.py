#!/usr/bin/env python3
"""
P1-4: Function Call 接入层
将8个工具接入豆包模型的Function Call机制，实现工具自动调用闭环
"""
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Callable

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")

# 工具注册表
TOOL_REGISTRY = {}

def register_tool(name: str, description: str, parameters: dict):
    """装饰器：注册工具到Function Call"""
    def decorator(func: Callable):
        TOOL_REGISTRY[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            },
            "handler": func
        }
        return func
    return decorator

@register_tool(
    name="query_truth_base",
    description="查询ZONGYUAN-ROOT真值基座中的公式和配置",
    parameters={"type": "object", "properties": {"keyword": {"type": "string", "description": "搜索关键词"}}, "required": ["keyword"]}
)
def query_truth_base(keyword: str) -> dict:
    results = []
    truth_dir = ROOT / "truth_base"
    if truth_dir.exists():
        for fp in truth_dir.glob("*.json"):
            with open(fp) as f:
                data = json.load(f)
            for formula in data.get("formulas", []) + data.get("truth_formulas", []):
                if isinstance(formula, dict) and keyword.lower() in json.dumps(formula, ensure_ascii=False).lower():
                    results.append(formula)
    return {"query": keyword, "results": results[:5], "count": len(results)}

@register_tool(
    name="get_asset_status",
    description="获取ZONGYUAN-ROOT资产状态和统计",
    parameters={"type": "object", "properties": {"domain": {"type": "string", "description": "体系域(可选)"}}, "required": []}
)
def get_asset_status(domain: str = None) -> dict:
    assets = []
    for fp in ROOT.rglob("*"):
        if fp.is_file() and "cache" not in str(fp):
            rel = str(fp.relative_to(ROOT))
            d = rel.split("/")[0]
            if domain is None or d == domain:
                assets.append({"path": rel, "domain": d, "size": fp.stat().st_size})
    return {"total": len(assets), "domain": domain, "assets": assets[:10]}

@register_tool(
    name="execute_evolution_cycle",
    description="触发一次自进化循环",
    parameters={"type": "object", "properties": {"trigger": {"type": "string", "description": "触发来源"}}, "required": []}
)
def execute_evolution_cycle(trigger: str = "function_call") -> dict:
    import sys
    sys.path.insert(0, str(ROOT / "omega_brain"))
    from evolution_loop import EvolutionLoop
    loop = EvolutionLoop()
    return loop.execute_evolution_cycle(trigger)

@register_tool(
    name="lock_asset",
    description="对指定资产执行SHA256锁档",
    parameters={"type": "object", "properties": {"path": {"type": "string", "description": "资产相对路径"}}, "required": ["path"]}
)
def lock_asset(path: str) -> dict:
    fp = ROOT / path
    if not fp.exists():
        return {"error": "file_not_found", "path": path}
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return {"path": path, "sha256": h.hexdigest(), "status": "locked"}

@register_tool(
    name="horizontal_expansion",
    description="执行横向功能扩展任务",
    parameters={"type": "object", "properties": {"phase": {"type": "string", "description": "P0/P1/P2/P3/auto"}}, "required": []}
)
def horizontal_expansion(phase: str = "auto") -> dict:
    import sys
    sys.path.insert(0, str(ROOT / "omega_brain"))
    from horizontal_expansion import HorizontalExpansionEngine
    engine = HorizontalExpansionEngine()
    return engine.execute_daily_expansion(phase)

@register_tool(
    name="create_backup",
    description="创建ZONGYUAN-ROOT全量备份",
    parameters={"type": "object", "properties": {}, "required": []}
)
def create_backup() -> dict:
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from backup_manager import create_backup
    return create_backup()

@register_tool(
    name="get_quota_status",
    description="获取API配额使用状态",
    parameters={"type": "object", "properties": {}, "required": []}
)
def get_quota_status() -> dict:
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from quota_monitor_v2 import get_status
    return get_status()

@register_tool(
    name="system_health_check",
    description="执行系统健康检查（服务/循环/负载均衡）",
    parameters={"type": "object", "properties": {}, "required": []}
)
def system_health_check() -> dict:
    import urllib.request
    results = {}
    # FastAPI服务
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=3) as resp:
            results["fastapi_service"] = json.loads(resp.read())
    except Exception as e:
        results["fastapi_service"] = {"status": "down", "error": str(e)}
    # 资产计数
    results["total_assets"] = sum(1 for _ in ROOT.rglob("*") if _.is_file() and "cache" not in str(_))
    return results

def get_tools_schema() -> List[dict]:
    """获取所有工具的Function Call Schema（供模型调用）"""
    return [tool["type"] and tool for tool in TOOL_REGISTRY.values()]

def get_function_definitions() -> List[dict]:
    """获取OpenAI格式的function definitions"""
    return [
        {
            "name": v["function"]["name"],
            "description": v["function"]["description"],
            "parameters": v["function"]["parameters"]
        }
        for v in TOOL_REGISTRY.values()
    ]

def execute_function(name: str, arguments: dict) -> dict:
    """执行指定工具函数"""
    if name not in TOOL_REGISTRY:
        return {"error": "unknown_function", "available": list(TOOL_REGISTRY.keys())}
    try:
        result = TOOL_REGISTRY[name]["handler"](**arguments)
        return {"function": name, "status": "success", "result": result}
    except Exception as e:
        return {"function": name, "status": "error", "error": str(e)}

def handle_model_response(response: dict) -> dict:
    """
    处理模型返回的function_call，自动执行并返回结果
    模型响应格式: {"function_call": {"name": "...", "arguments": "{...}"}}
    """
    if "function_call" not in response:
        return {"has_function_call": False, "content": response.get("content", "")}
    
    call = response["function_call"]
    name = call.get("name", "")
    try:
        arguments = json.loads(call.get("arguments", "{}"))
    except:
        arguments = {}
    
    result = execute_function(name, arguments)
    return {"has_function_call": True, "function": name, "arguments": arguments, "result": result}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print(json.dumps(get_function_definitions(), ensure_ascii=False, indent=2))
    elif len(sys.argv) > 2 and sys.argv[1] == "call":
        name = sys.argv[2]
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        print(json.dumps(execute_function(name, args), ensure_ascii=False, indent=2))
    else:
        print(f"已注册工具: {list(TOOL_REGISTRY.keys())}")
        print(f"工具数量: {len(TOOL_REGISTRY)}")
