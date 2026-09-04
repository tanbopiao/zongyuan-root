#!/usr/bin/env python3
"""
M2: Function Call 结构化工具定义 + 自主调用框架
模型可自主决策调用以下工具，实现L5级自主执行
"""
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")

# ============ 工具Schema定义（Function Call标准格式） ============
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_sha256",
            "description": "计算文件或文本的SHA256哈希值，用于资产确权和完整性校验",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_type": {"type": "string", "enum": ["file", "text"], "description": "输入类型"},
                    "input_value": {"type": "string", "description": "文件路径或文本内容"}
                },
                "required": ["input_type", "input_value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_assets",
            "description": "扫描ZONGYUAN-ROOT全量资产，返回资产清单和哈希",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "按体系域过滤，如truth_base/whitepapers"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_truth_base",
            "description": "查询真值基座中的公式和公理",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词"},
                    "limit": {"type": "integer", "description": "返回数量", "default": 5}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_archive",
            "description": "执行全域锁档，生成Merkle根和eFuse凭证",
            "parameters": {
                "type": "object",
                "properties": {
                    "snapshot_name": {"type": "string", "description": "快照名称"}
                },
                "required": ["snapshot_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_quota",
            "description": "查询当前API配额使用状态和降级等级",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "semantic_search",
            "description": "语义检索真值基座和资产库",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索查询"},
                    "top_k": {"type": "integer", "description": "返回数量", "default": 5}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "local_image_process",
            "description": "本地图像处理(缩放/水印/格式转换)，零API消耗",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["resize", "watermark", "convert"]},
                    "input_path": {"type": "string"},
                    "output_path": {"type": "string"},
                    "params": {"type": "object", "description": "操作参数"}
                },
                "required": ["operation", "input_path", "output_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "batch_execute",
            "description": "异步批量执行多个任务，支持并发10+",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {"type": "array", "items": {"type": "object"}, "description": "任务列表"},
                    "max_concurrent": {"type": "integer", "default": 10}
                },
                "required": ["tasks"]
            }
        }
    }
]

# ============ 工具实现 ============
def calculate_sha256(input_type: str, input_value: str) -> dict:
    h = hashlib.sha256()
    if input_type == "file":
        with open(input_value, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    else:
        h.update(input_value.encode("utf-8"))
    return {"sha256": h.hexdigest(), "input_type": input_type}

def scan_assets(domain: str = None) -> dict:
    assets = []
    for fp in ROOT.rglob("*"):
        if fp.is_file() and "cache" not in str(fp):
            rel = str(fp.relative_to(ROOT))
            if domain and not rel.startswith(domain):
                continue
            h = hashlib.sha256()
            with open(fp, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            assets.append({"path": rel, "sha256": h.hexdigest()[:16], "size": fp.stat().st_size})
    return {"total": len(assets), "assets": assets}

def query_truth_base(keyword: str = "", limit: int = 5) -> dict:
    results = []
    truth_dir = ROOT / "truth_base"
    if truth_dir.exists():
        for fp in truth_dir.glob("*.json"):
            with open(fp) as f:
                data = json.load(f)
            formulas = data.get("formulas", []) + data.get("truth_formulas", [])
            for formula in formulas:
                if isinstance(formula, dict):
                    text = formula.get("name", "") + " " + formula.get("expression", "")
                    if not keyword or keyword in text:
                        results.append(formula)
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break
    return {"count": len(results), "results": results[:limit]}

def lock_archive(snapshot_name: str) -> dict:
    assets = scan_assets()
    hashes = sorted([a["sha256"] for a in assets["assets"]])
    while len(hashes) > 1:
        if len(hashes) % 2 == 1: hashes.append(hashes[-1])
        hashes = [hashlib.sha256((hashes[i]+hashes[i+1]).encode()).hexdigest() for i in range(0, len(hashes), 2)]
    snapshot = {
        "snapshot_id": snapshot_name,
        "total_assets": assets["total"],
        "merkle_root": hashes[0] if hashes else "empty",
        "efuse": {"state": "blown", "time": time.strftime("%Y-%m-%dT%H:%M:%S")},
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    snap_file = ROOT / "lock_archive" / f"snapshot_{snapshot_name}.json"
    with open(snap_file, "w") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return {"status": "locked", "snapshot_file": str(snap_file), "merkle_root": snapshot["merkle_root"]}

def check_quota() -> dict:
    usage_file = ROOT / "logs" / "quota_usage.json"
    if usage_file.exists():
        with open(usage_file) as f:
            return json.load(f)
    return {"status": "no_usage_data", "degradation_level": "normal"}

def semantic_search(query: str, top_k: int = 5) -> dict:
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from vector_search import LightVectorStore, build_truth_base_vector_store
    store, count = build_truth_base_vector_store()
    results = store.search(query, top_k=top_k)
    return {"indexed": count, "query": query, "results": results}

def local_image_process(operation: str, input_path: str, output_path: str, params: dict = None) -> dict:
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from local_tools import image_resize, image_watermark, image_convert
    params = params or {}
    if operation == "resize":
        result = image_resize(input_path, output_path, params.get("width"), params.get("height"))
    elif operation == "watermark":
        result = image_watermark(input_path, output_path, params.get("text", "Ω₀⊂⊙∞⊂Ω"))
    elif operation == "convert":
        result = image_convert(input_path, output_path, params.get("format"))
    else:
        return {"error": f"unknown operation: {operation}"}
    return {"status": "success", "output": result}

def batch_execute(tasks: list, max_concurrent: int = 10) -> dict:
    import asyncio
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from batch_executor import BatchExecutor
    executor = BatchExecutor(max_concurrent=max_concurrent)
    result = asyncio.run(executor.execute_batch(tasks))
    return result

# 工具注册表
TOOL_REGISTRY: Dict[str, Callable] = {
    "calculate_sha256": calculate_sha256,
    "scan_assets": scan_assets,
    "query_truth_base": query_truth_base,
    "lock_archive": lock_archive,
    "check_quota": check_quota,
    "semantic_search": semantic_search,
    "local_image_process": local_image_process,
    "batch_execute": batch_execute,
}

def execute_tool_call(tool_name: str, arguments: dict) -> dict:
    """执行工具调用（Function Call入口）"""
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"unknown tool: {tool_name}", "available_tools": list(TOOL_REGISTRY.keys())}
    try:
        result = TOOL_REGISTRY[tool_name](**arguments)
        return {"tool": tool_name, "status": "success", "result": result}
    except Exception as e:
        return {"tool": tool_name, "status": "error", "error": str(e)}

def get_tool_schemas() -> list:
    """获取所有工具Schema（用于传入模型）"""
    return TOOL_SCHEMAS

if __name__ == "__main__":
    print(f"已注册 {len(TOOL_REGISTRY)} 个工具:")
    for name in TOOL_REGISTRY:
        print(f"  - {name}")
    print("\n测试: scan_assets")
    result = execute_tool_call("scan_assets", {})
    print(f"  总资产: {result['result']['total']}")
