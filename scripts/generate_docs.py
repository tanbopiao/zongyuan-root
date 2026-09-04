#!/usr/bin/env python3
"""
P2-7: API文档生成器
自动扫描所有模块，生成Markdown API文档
"""
import json
import inspect
import importlib
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
DOCS_DIR = ROOT / "docs"

def scan_module(module_path: str, module_name: str) -> dict:
    """扫描模块，提取函数/类文档"""
    sys.path.insert(0, str(ROOT))
    try:
        mod = importlib.import_module(module_path)
    except Exception as e:
        return {"module": module_name, "error": str(e)}
    
    functions = []
    classes = []
    
    for name, obj in inspect.getmembers(mod):
        if inspect.isfunction(obj) and not name.startswith("_"):
            try:
                sig = str(inspect.signature(obj))
            except:
                sig = "()"
            functions.append({
                "name": name,
                "signature": sig,
                "doc": (obj.__doc__ or "").strip()[:200]
            })
        elif inspect.isclass(obj) and not name.startswith("_"):
            methods = []
            for mname, mobj in inspect.getmembers(obj):
                if inspect.isfunction(mobj) and not mname.startswith("_"):
                    methods.append(mname)
            classes.append({
                "name": name,
                "doc": (obj.__doc__ or "").strip()[:200],
                "methods": methods[:10]
            })
    
    return {
        "module": module_name,
        "doc": (mod.__doc__ or "").strip()[:300],
        "functions": functions,
        "classes": classes
    }

def generate_docs():
    """生成完整API文档"""
    DOCS_DIR.mkdir(exist_ok=True)
    
    modules = [
        ("omega_brain.daemon_manager", "守护进程管理器"),
        ("omega_brain.evolution_loop", "自进化循环"),
        ("omega_brain.horizontal_expansion", "横向扩展引擎"),
        ("omega_brain.load_balancer", "负载均衡器"),
        ("omega_brain.function_call_layer", "Function Call层"),
        ("omega_brain.rag_engine", "RAG引擎"),
        ("scripts.merkle_tree", "Merkle树"),
        ("scripts.backup_manager", "备份管理器"),
        ("scripts.quota_monitor_v2", "配额监控"),
        ("scripts.asset_aggregation", "资产聚合"),
        ("scripts.image_watermark", "图像暗印"),
        ("config.config_center", "配置中心"),
    ]
    
    all_docs = []
    for module_path, desc in modules:
        doc = scan_module(module_path, desc)
        all_docs.append(doc)
    
    # 生成Markdown
    md = f"""# ZONGYUAN-ROOT API 文档

> 自动生成时间: {datetime.now().isoformat()}
> 模块数: {len(all_docs)}

---

## 目录

"""
    for i, doc in enumerate(all_docs, 1):
        md += f"{i}. [{doc['module']}](#{doc['module'].replace(' ', '-')})\n"
    
    md += "\n---\n\n"
    
    for doc in all_docs:
        md += f"## {doc['module']}\n\n"
        if doc.get("doc"):
            md += f"{doc['doc']}\n\n"
        if doc.get("error"):
            md += f"> ⚠️ 加载失败: {doc['error']}\n\n"
            continue
        
        if doc.get("classes"):
            md += "### 类\n\n"
            for cls in doc["classes"]:
                md += f"#### {cls['name']}\n"
                if cls["doc"]:
                    md += f"{cls['doc']}\n"
                if cls["methods"]:
                    md += f"方法: {', '.join(cls['methods'])}\n"
                md += "\n"
        
        if doc.get("functions"):
            md += "### 函数\n\n"
            for func in doc["functions"]:
                md += f"#### `{func['name']}{func['signature']}`\n"
                if func["doc"]:
                    md += f"{func['doc']}\n"
                md += "\n"
        
        md += "---\n\n"
    
    doc_file = DOCS_DIR / "API_REFERENCE.md"
    with open(doc_file, "w") as f:
        f.write(md)
    
    return {"doc_file": str(doc_file), "modules": len(all_docs), "size": len(md)}

if __name__ == "__main__":
    result = generate_docs()
    print(json.dumps(result, ensure_ascii=False, indent=2))
