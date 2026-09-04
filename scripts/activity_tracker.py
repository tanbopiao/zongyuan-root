#!/usr/bin/env python3
"""
P2-8: 资产活跃度统计
统计关联飞书文档的PV/UV，识别冷数据
"""
import json
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")

def get_file_statistics(doc_id: str) -> dict:
    """调用飞书API获取文件统计"""
    try:
        result = subprocess.run(
            ["lark-cli", "api", "GET", f"/open-apis/drive/v1/files/{doc_id}/statistics"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr[:200]}
    except Exception as e:
        return {"error": str(e)}

def scan_linked_documents() -> list:
    """扫描所有含document_id的资产"""
    linked = []
    # 从Base资产表获取
    try:
        result = subprocess.run(
            ["lark-cli", "base", "+record-list",
             "--base-token", "GRqwbQrwhaXNoesxzRVcwUu6n6b",
             "--table-id", "tbl3Je9wQeJnacGo",
             "--page-size", "100"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for record in data.get("data", {}).get("items", []):
                fields = record.get("fields", {})
                doc_id = fields.get("document_id") or fields.get("关联文档")
                if doc_id:
                    linked.append({
                        "record_id": record.get("record_id"),
                        "name": fields.get("资产名称", "unknown"),
                        "doc_id": doc_id
                    })
    except Exception as e:
        pass
    
    # 本地文件中的document_id
    for fp in ROOT.rglob("*.json"):
        if "cache" in str(fp):
            continue
        try:
            with open(fp) as f:
                content = f.read()
            if "document_id" in content or "doc_token" in content:
                data = json.loads(content)
                doc_id = data.get("document_id") or data.get("doc_token")
                if doc_id:
                    linked.append({"name": fp.name, "doc_id": doc_id, "source": "local"})
        except:
            pass
    
    return linked

def generate_activity_report() -> dict:
    """生成活跃度报告"""
    linked = scan_linked_documents()
    total_pv = 0
    total_uv = 0
    cold_data = []
    active = []
    
    for item in linked[:20]:  # 限制API调用次数
        stats = get_file_statistics(item["doc_id"])
        pv = stats.get("data", {}).get("pv", 0)
        uv = stats.get("data", {}).get("uv", 0)
        total_pv += pv
        total_uv += uv
        item["pv"] = pv
        item["uv"] = uv
        if pv == 0:
            cold_data.append(item)
        else:
            active.append(item)
    
    report = {
        "report_id": f"ACT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "generated_at": datetime.now().isoformat(),
        "linked_documents": len(linked),
        "scanned": min(len(linked), 20),
        "total_pv": total_pv,
        "total_uv": total_uv,
        "cold_data_count": len(cold_data),
        "cold_data_ratio": f"{len(cold_data)/max(len(linked),1):.1%}",
        "cold_data": cold_data,
        "top_active": sorted(active, key=lambda x: -x.get("pv", 0))[:5],
        "recommendation": "冷数据资产建议推广激活或归档"
    }
    
    report_file = ROOT / "logs" / f"activity_report_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report

if __name__ == "__main__":
    report = generate_activity_report()
    print(json.dumps({
        "linked_docs": report["linked_documents"],
        "total_pv": report["total_pv"],
        "cold_data": report["cold_data_count"],
        "cold_ratio": report["cold_data_ratio"]
    }, ensure_ascii=False, indent=2))
