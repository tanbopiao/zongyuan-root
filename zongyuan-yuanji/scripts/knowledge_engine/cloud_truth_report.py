"""
云端真值上报脚本
用途：将本地知识库更新上报到云端记忆网关
API: POST https://www.huodouai.com/api/report/truth
鉴权: X-DID: DID-BR-000002
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
import requests

# 配置
TRUTH_API_URL = "https://www.huodouai.com/api/report/truth"
X_DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"


def compute_hash(path: str) -> str:
    """计算文件哈希"""
    p = Path(path)
    if p.is_file():
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    elif p.is_dir():
        files = [f for f in p.glob("*") if f.is_file()]
        h = hashlib.sha256()
        for f in sorted(files, key=lambda x: x.name):
            h.update(f.read_bytes())
        return h.hexdigest()[:16]
    return ""


def upload_truth(payload: dict) -> dict:
    """上报真值到云端"""
    headers = {
        "Content-Type": "application/json",
        "X-DID": X_DID
    }
    try:
        resp = requests.post(TRUTH_API_URL, json=payload, headers=headers, timeout=30)
        result = {
            "status_code": resp.status_code,
            "ok": resp.status_code == 200,
            "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:200]
        }
        if result["ok"]:
            data = result["response"]
            print(f"  ✅ seq={data.get('seq', '?')} | {payload['key']}")
        else:
            print(f"  ❌ HTTP {resp.status_code} | {payload['key']}")
            print(f"     响应: {str(result['response'])[:200]}")
        return result
    except Exception as e:
        print(f"  ❌ 异常: {str(e)[:200]}")
        return {"status_code": 0, "ok": False, "error": str(e)}


def report_seed_manifest():
    """上报种子清单"""
    manifest_path = "/zongyuan-yuanji/persist/seed_truth/manifest.json"
    if not Path(manifest_path).exists():
        print(f"[SKIP] 种子清单不存在: {manifest_path}")
        return None

    manifest = json.loads(Path(manifest_path).read_text())
    seed_count = len(manifest.get("seed_list", []))
    level_stats = manifest.get("level_stats", {})

    payload = {
        "key": f"KERNEL.SEED.MANIFEST.{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "value": {
            "namespace": "KERNEL.SEED",
            "manifest_id": f"SEED-MANIFEST.{datetime.now().strftime('%Y%m%d')}.V1",
            "seed_version": manifest.get("seed_version", "unknown"),
            "seed_count": seed_count,
            "level_stats": level_stats,
            "base_weight_path": manifest.get("base_weight_path", ""),
            "torch_seed": manifest.get("torch_seed", 42),
            "env_fingerprint": manifest.get("env_fingerprint", {}),
            "hash": compute_hash(manifest_path),
            "reported_at": datetime.now().isoformat(),
            "anchor": ANCHOR,
            "did": X_DID,
            "candidate_only": True
        }
    }
    return upload_truth(payload)


def report_memory_structure():
    """上报知识索引结构"""
    memory_dir = "/.octop/workspaces/main/memory"
    if not Path(memory_dir).exists():
        print(f"[SKIP] 知识目录不存在: {memory_dir}")
        return None

    files = [f.name for f in sorted(Path(memory_dir).glob("*.md"))]

    payload = {
        "key": f"KERNEL.MEMORY.STRUCTURE.{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "value": {
            "namespace": "KERNEL.MEMORY",
            "memory_structure": {
                "root": "/.octop/workspaces/main/memory",
                "files": files,
                "file_count": len(files),
                "index_type": "submodule_split",
                "updated_at": datetime.now().isoformat()
            },
            "hash": compute_hash(memory_dir),
            "reported_at": datetime.now().isoformat(),
            "anchor": ANCHOR,
            "did": X_DID,
            "candidate_only": True
        }
    }
    return upload_truth(payload)


def report_engine_scripts():
    """上报引擎脚本部署状态"""
    engine_dir = "/zongyuan-yuanji/scripts/knowledge_engine"
    if not Path(engine_dir).exists():
        print(f"[SKIP] 引擎目录不存在: {engine_dir}")
        return None

    scripts = [f.name for f in sorted(Path(engine_dir).glob("*.py"))]

    payload = {
        "key": f"KERNEL.ENGINE.Scripts.{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "value": {
            "namespace": "KERNEL.ENGINE",
            "engine_scripts": {
                "root": "/zongyuan-yuanji/scripts/knowledge_engine",
                "scripts": scripts,
                "script_count": len(scripts),
                "deployed_at": datetime.now().isoformat()
            },
            "hash": compute_hash(engine_dir),
            "reported_at": datetime.now().isoformat(),
            "anchor": ANCHOR,
            "did": X_DID,
            "candidate_only": True
        }
    }
    return upload_truth(payload)


def main():
    print("=" * 60)
    print("☁️  云端真值上报")
    print(f"   端点: {TRUTH_API_URL}")
    print(f"   身份: X-DID: {X_DID}")
    print(f"   锚点: {ANCHOR}")
    print("=" * 60)

    results = []

    print("\n[1/3] 种子真值池清单上报...")
    r = report_seed_manifest()
    results.append(r)

    print("\n[2/3] 知识索引结构上报...")
    r = report_memory_structure()
    results.append(r)

    print("\n[3/3] 引擎脚本部署状态上报...")
    r = report_engine_scripts()
    results.append(r)

    print("\n" + "=" * 60)
    print("📊 上报汇总")
    print("=" * 60)
    success = sum(1 for r in results if r and r.get("ok"))
    total = len([r for r in results if r])
    print(f"  成功: {success}/{total}")

    for i, r in enumerate(results, 1):
        if r and r.get("ok"):
            print(f"  ✅ [{i}] {r.get('response', {}).get('seq', '?')}")
        else:
            print(f"  ❌ [{i}] 失败")

    print(f"\n✅ 云端真值上报完成")
    return results


if __name__ == "__main__":
    main()