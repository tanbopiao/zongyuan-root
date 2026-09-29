#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 资产流水线调度端（内核侧）
功能：视频生成结果 → 预计算SHA256 → 写入飞书Base → 下发本地桥接下载任务 → 等待回执 → 更新台账
作者：元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

使用方法：
  python asset_pipeline_trigger.py --cdn-url "https://视频链接" --name "元极启元15s" --desc "描述"
  python asset_pipeline_trigger.py --task-file task.json  # 从文件读取任务
"""
import os
import sys
import json
import hashlib
import datetime
import argparse
import urllib.request
import urllib.parse
import ssl
import time
import tempfile


# ==================== 配置 ====================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline_config.json")

DEFAULT_CONFIG = {
    "feishu": {
        "app_id": "cli_aa1387fc6b635d14",
        "app_secret": "uXbPoDiMrkmo8SJOh8ixWdaPngBDSH68",
        "base_token": "请填写base_token",
        "table_id": "请填写table_id"
    },
    "local_bridge": {
        "ngrok_url": "请填写ngrok公网地址，如 https://xxxx.ngrok.io",
        "token": "请填写与local_bridge.py一致的SECRET_TOKEN"
    },
    "pipeline": {
        "asset_prefix": "KD",
        "download_timeout_seconds": 300,
        "poll_retry_count": 10,
        "poll_interval_seconds": 5
    },
    "field_mapping": {
        "asset_id": "资产ID",
        "asset_name": "资产名称",
        "asset_type": "资产类型",
        "description": "描述",
        "cdn_url": "CDN临时链接",
        "sha256": "SHA256哈希",
        "local_path": "本地路径",
        "download_status": "下载状态",
        "create_time": "创建时间",
        "trace_mark": "溯源标识"
    }
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        print(f"[配置] 已生成默认配置: {CONFIG_FILE}")
        print("[配置] 请填写 base_token / table_id / ngrok_url / token 后重新运行")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def http_post(url, data, headers=None, timeout=30):
    """通用HTTP POST"""
    if headers is None:
        headers = {}
    if "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def http_get(url, headers=None, timeout=30):
    """通用HTTP GET"""
    if headers is None:
        headers = {}
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def get_feishu_token(app_id, app_secret):
    """获取飞书tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    result = http_post(url, {"app_id": app_id, "app_secret": app_secret})
    if result.get("code") == 0:
        return result["tenant_access_token"]
    raise Exception(f"飞书token获取失败: {result}")


def prefetch_and_hash(cdn_url, timeout=120):
    """预下载视频到临时文件，计算SHA256"""
    print(f"[预下载] 从CDN拉取视频用于哈希计算...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(cdn_url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    tmp_path = None
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            sha256 = hashlib.sha256()
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tmp_path = tmp.name
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                tmp.write(chunk)
                sha256.update(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded / total * 100
                    print(f"\r[预下载] {pct:.1f}% ({downloaded//1024}KB)", end="", flush=True)
            tmp.close()
            print()
        file_hash = sha256.hexdigest().upper()
        file_size_mb = round(os.path.getsize(tmp_path) / 1024 / 1024, 2)
        print(f"[预下载] ✅ 完成，大小: {file_size_mb}MB, SHA256: {file_hash[:16]}...")
        return file_hash, file_size_mb, tmp_path
    except Exception as e:
        print(f"\n[预下载] ❌ 失败: {e}")
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return None, 0, None


def create_feishu_record(config, token, record_data):
    """创建飞书Base记录，返回record_id"""
    feishu = config["feishu"]
    mapping = config["field_mapping"]
    fields = {}
    for key, field_name in mapping.items():
        if key in record_data:
            fields[field_name] = record_data[key]

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{feishu['base_token']}/tables/{feishu['table_id']}/records"
    result = http_post(url, {"fields": fields}, headers={"Authorization": f"Bearer {token}"})
    if result.get("code") == 0:
        record_id = result["data"]["record"]["record_id"]
        print(f"[飞书] ✅ 台账已创建，record_id: {record_id}")
        return record_id
    else:
        print(f"[飞书] ❌ 创建失败: {result}")
        return None


def update_feishu_record(config, token, record_id, fields):
    """更新飞书Base记录"""
    feishu = config["feishu"]
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{feishu['base_token']}/tables/{feishu['table_id']}/records/{record_id}"
    req = urllib.request.Request(
        url,
        data=json.dumps({"fields": fields}, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="PATCH"
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        result = json.loads(resp.read().decode())
        return result.get("code") == 0


def dispatch_to_local_bridge(config, task_data):
    """下发下载任务到本地桥接网关"""
    bridge = config["local_bridge"]
    url = f"{bridge['ngrok_url'].rstrip('/')}/asset/download"
    headers = {
        "X-Bridge-Token": bridge["token"],
        "Content-Type": "application/json"
    }
    print(f"[本地桥接] 下发下载任务: {task_data['asset_name']}")
    try:
        result = http_post(url, task_data, headers=headers, timeout=config["pipeline"]["download_timeout_seconds"])
        if result.get("code") == 200:
            print(f"[本地桥接] ✅ 下载完成")
            print(f"  本地路径: {result.get('local_path')}")
            print(f"  SHA256: {result.get('sha256','')[:16]}...")
            print(f"  哈希匹配: {result.get('hash_match')}")
            return result
        else:
            print(f"[本地桥接] ❌ 下载失败: {result}")
            return None
    except Exception as e:
        print(f"[本地桥接] ❌ 连接异常: {e}")
        return None


def generate_asset_id(config):
    """生成资产ID"""
    prefix = config["pipeline"]["asset_prefix"]
    now = datetime.datetime.now()
    return f"{prefix}-{now.strftime('%Y%m%d-%H%M%S')}"


def run_pipeline(cdn_url, asset_name, description="", asset_type="视频"):
    """执行完整流水线"""
    print("=" * 60)
    print("  ZONGYUAN-ROOT 资产流水线调度")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 60)

    config = load_config()

    # 检查配置
    bridge = config["local_bridge"]
    if "请填写" in bridge["ngrok_url"] or "请填写" in bridge["token"]:
        print("[错误] 请先配置 local_bridge 的 ngrok_url 和 token")
        sys.exit(1)

    # Step1: 生成资产ID
    asset_id = generate_asset_id(config)
    print(f"\n[Step1] 资产ID: {asset_id}")

    # Step2: 预下载计算SHA256
    print(f"\n[Step2] 预下载计算哈希...")
    file_hash, file_size_mb, tmp_path = prefetch_and_hash(cdn_url)
    if not file_hash:
        print("[错误] 预下载失败，流水线终止")
        sys.exit(1)

    # Step3: 获取飞书token
    print(f"\n[Step3] 获取飞书凭证...")
    try:
        feishu_token = get_feishu_token(config["feishu"]["app_id"], config["feishu"]["app_secret"])
        print("[Step3] ✅ 飞书token获取成功")
    except Exception as e:
        print(f"[Step3] ❌ {e}")
        feishu_token = None

    # Step4: 写入飞书台账（状态：待下载）
    record_id = None
    if feishu_token:
        print(f"\n[Step4] 写入飞书资产台账...")
        record_data = {
            "asset_id": asset_id,
            "asset_name": asset_name,
            "asset_type": asset_type,
            "description": description,
            "cdn_url": cdn_url,
            "sha256": file_hash,
            "download_status": "待下载",
            "create_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trace_mark": "Ω₀⊂⊙∞⊂Ω"
        }
        record_id = create_feishu_record(config, feishu_token, record_data)

    # Step5: 下发本地桥接下载任务
    print(f"\n[Step5] 下发本地桥接下载任务...")
    task_data = {
        "asset_id": asset_id,
        "asset_name": asset_name,
        "cdn_url": cdn_url,
        "expect_sha256": file_hash
    }
    bridge_result = dispatch_to_local_bridge(config, task_data)

    # Step6: 更新飞书台账状态
    if record_id and feishu_token:
        print(f"\n[Step6] 更新台账状态...")
        if bridge_result and bridge_result.get("code") == 200:
            update_fields = {
                config["field_mapping"]["download_status"]: "已完成" if bridge_result.get("hash_match") else "哈希校验失败",
                config["field_mapping"]["local_path"]: bridge_result.get("local_path", "")
            }
            ok = update_feishu_record(config, feishu_token, record_id, update_fields)
            print(f"[Step6] {'✅ 台账已更新为已完成' if ok else '⚠️ 台账更新失败'}")
        else:
            update_fields = {config["field_mapping"]["download_status"]: "下载失败"}
            update_feishu_record(config, feishu_token, record_id, update_fields)
            print("[Step6] ⚠️ 台账已标记为下载失败")

    # 清理临时文件
    if tmp_path and os.path.exists(tmp_path):
        os.unlink(tmp_path)

    # 总结
    print("\n" + "=" * 60)
    print("  流水线执行完成")
    print("=" * 60)
    print(f"  资产ID: {asset_id}")
    print(f"  名称: {asset_name}")
    print(f"  大小: {file_size_mb} MB")
    print(f"  SHA256: {file_hash}")
    print(f"  飞书台账: {'✅ 已写入' if record_id else '⚠️ 未写入'}")
    print(f"  本地下载: {'✅ 成功' if bridge_result and bridge_result.get('code')==200 else '❌ 失败'}")
    print("=" * 60)

    return {
        "asset_id": asset_id,
        "sha256": file_hash,
        "record_id": record_id,
        "local_download_success": bridge_result and bridge_result.get("code") == 200
    }


def main():
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 资产流水线调度端")
    parser.add_argument("--cdn-url", help="视频CDN链接")
    parser.add_argument("--name", help="资产名称")
    parser.add_argument("--desc", default="", help="资产描述")
    parser.add_argument("--type", default="视频", help="资产类型")
    parser.add_argument("--task-file", help="从JSON文件读取任务（包含cdn_url/name/desc）")
    args = parser.parse_args()

    if args.task_file:
        with open(args.task_file, "r", encoding="utf-8") as f:
            task = json.load(f)
        run_pipeline(task["cdn_url"], task.get("name", "未命名"), task.get("desc", ""), task.get("type", "视频"))
    elif args.cdn_url and args.name:
        run_pipeline(args.cdn_url, args.name, args.desc, args.type)
    else:
        parser.print_help()
        print("\n示例:")
        print('  python asset_pipeline_trigger.py --cdn-url "https://..." --name "元极启元15s" --desc "昆仑洞天启元段落"')
        sys.exit(1)


if __name__ == "__main__":
    main()
