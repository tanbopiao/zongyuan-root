#!/usr/bin/env python3
import json, urllib.request, hashlib

report_path = '/opt/ZONGYUAN-ROOT/archive/reports/2026-09/zero-cost-audit-20260913.html'
with open(report_path, 'rb') as f:
    content = f.read()
file_hash = hashlib.sha256(content).hexdigest()

truth = {
    "truth_key": "REPORT.ZERO_COST_AUDIT.20260913",
    "truth_value": json.dumps({
        "report_name": "零成本运行体系检查报告",
        "report_date": "2026-09-13",
        "file_path": "/opt/ZONGYUAN-ROOT/archive/reports/2026-09/zero-cost-audit-20260913.html",
        "web_url": "https://huodouai.com/whitepapers/zero-cost-audit-20260913.html",
        "file_hash": file_hash,
        "file_size": len(content),
        "key_findings": {
            "cos_status": "disconnected_local_simulation",
            "external_api_calls": 0,
            "configured_models": 12,
            "monthly_cost": "0yuan",
            "local_llm_usage": "92.1%",
            "mr021_locked": True
        },
        "did": "DID-BR-000002",
        "trace": "Ω₀⊂⊙∞⊂Ω"
    }, ensure_ascii=False),
    "category": "report",
    "tags": ["report", "zero_cost", "audit", "2026-09-13"],
    "node_id": "system",
    "version": 1,
    "source": "manual_audit"
}

req = urllib.request.Request(
    'http://127.0.0.1:9120/api/truth/upsert',
    data=json.dumps(truth).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=10) as resp:
    result = json.loads(resp.read().decode())
    print('记忆网关上报告:', json.dumps(result, ensure_ascii=False))
