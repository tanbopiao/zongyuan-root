#!/usr/bin/env python3
"""
飞书Base → 9120 记忆网关同步脚本
- 定时拉取飞书Base中指定表的记录
- 增量同步（记录上次同步时间）
- 写入9120真值库
- 同步结果上报审计
"""
import json
import time
import os
import sys
import urllib.request
from datetime import datetime

sys.path.insert(0, "/opt/ZONGYUAN-ROOT/scripts")
from config_loader import get_feishu

# 配置（从统一配置读取，失败时fallback到默认值）
FEISHU_APP_ID = get_feishu("app_id", "cli_aa1387fc6b635d14")
FEISHU_APP_SECRET = get_feishu("app_secret", "uXbPoDiMrkmo8SJOh8ixWdaPngBDSH68")
BASE_APP_TOKEN = get_feishu("base_app_token", "DpTQbldkfazAwKsALa5ceaeinRb")
TABLE_ID = get_feishu("core_truth_table_id", "tblIMQDqm2ADwWa5")
GATEWAY_URL = "http://127.0.0.1:9120"
STATE_FILE = "/opt/ZONGYUAN-ROOT/data/feishu_sync_state.json"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"

def retry_request(url, data=None, headers=None, max_retries=3, timeout=10):
    """带重试的HTTP请求（指数退避）"""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers or {})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            time.sleep(wait)
    return {}

def get_tenant_token():
    """获取飞书tenant_access_token（带重试）"""
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    result = retry_request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=data, headers={'Content-Type': 'application/json'}
    )
    return result.get("tenant_access_token", "")

def fetch_records(token, page_size=100):
    """从飞书Base拉取记录（带重试）"""
    records = []
    page_token = ""
    while True:
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_APP_TOKEN}/tables/{TABLE_ID}/records?page_size={page_size}"
        if page_token:
            url += f"&page_token={page_token}"
        data = retry_request(url, headers={'Authorization': f'Bearer {token}'})
        items = data.get("data", {}).get("items", []) or []
        records.extend(items)
        page_token = data.get("data", {}).get("page_token", "")
        if not page_token or not data.get("data", {}).get("has_more"):
            break
    return records

def upsert_truth(key, value, source="feishu_base", truth_type="core_truth"):
    """写入9120"""
    data = json.dumps({
        "key": key,
        "value": value,
        "source": source,
        "did": DID,
        "anchor": ANCHOR,
        "confidence": 1.0,
        "truth_type": truth_type
    }).encode()
    req = urllib.request.Request(
        f"{GATEWAY_URL}/api/truth/upsert",
        data=data, headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_sync": "1970-01-01T00:00:00", "synced_keys": []}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def main():
    print(f"[{datetime.now()}] 飞书Base→9120同步开始")
    
    token = get_tenant_token()
    if not token:
        print("ERROR: 获取飞书token失败")
        return
    
    records = fetch_records(token)
    print(f"拉取到 {len(records)} 条记录")
    
    state = load_state()
    synced = 0
    skipped = 0
    
    for record in records:
        fields = record.get("fields", {})
        record_id = record.get("record_id", "")
        
        # 字段映射：真值Key→key, 真值内容→value, 真值类型→truth_type, 置信度→confidence, 来源→source
        key_field = fields.get("真值Key", "")
        value_field = fields.get("真值内容", "")
        truth_type = fields.get("真值类型", "core_truth")
        confidence = fields.get("置信度", 1.0)
        source = fields.get("来源", "feishu_base")
        sync_status = fields.get("同步状态", "待同步")
        
        # 跳过空记录或已同步的
        if not key_field or sync_status == "已同步":
            skipped += 1
            continue
        
        # 处理富文本格式
        def extract_text(field):
            if isinstance(field, list):
                return "".join([seg.get("text", "") for seg in field if isinstance(seg, dict)])
            return str(field) if field else ""
        
        key_text = extract_text(key_field)
        value_text = extract_text(value_field)
        
        if not key_text.strip():
            skipped += 1
            continue
        
        # 用真值Key做唯一key
        truth_key = f"feishu.{key_text}"
        value = value_text if value_text else f"[飞书Base同步] {key_text}"
        
        try:
            result = upsert_truth(truth_key, value, source=extract_text(source), truth_type=extract_text(truth_type))
            if result.get("success"):
                synced += 1
        except Exception as e:
            print(f"  写入失败: {truth_key} - {e}")
    
    state["last_sync"] = datetime.now().isoformat()
    state["last_count"] = len(records)
    save_state(state)
    
    # 上报同步结果
    try:
        upsert_truth(
            f"feishu_sync.{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            f"飞书Base同步完成: 拉取{len(records)}条, 写入{synced}条, 跳过{skipped}条",
            source="feishu_sync",
            truth_type="sync_log"
        )
    except:
        pass
    
    print(f"[{datetime.now()}] 同步完成: 拉取{len(records)}, 写入{synced}, 跳过{skipped}")

if __name__ == '__main__':
    main()
