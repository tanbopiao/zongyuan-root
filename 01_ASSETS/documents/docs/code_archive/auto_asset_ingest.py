#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑洞天短剧资产一键入库工具
功能：剪贴板读取视频URL → 自动下载 → 计算SHA256 → 写入飞书Base资产台账
作者：元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

使用方法：
  1. 复制视频URL到剪贴板
  2. 运行: python auto_asset_ingest.py
  3. 或指定URL: python auto_asset_ingest.py --url "https://..."
  4. 或指定文件名: python auto_asset_ingest.py --url "https://..." --name "KD-S01-EP01.mp4"

依赖：pip install requests
（Windows自带tkinter用于剪贴板，无需额外安装）
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


# ==================== 配置 ====================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "asset_ingest_config.json")

DEFAULT_CONFIG = {
    "feishu": {
        "app_id": "cli_aa1387fc6b635d14",
        "app_secret": "uXbPoDiMrkmo8SJOh8ixWdaPngBDSH68",
        "base_token": "请填写你的多维表格app_token",
        "table_id": "请填写你的数据表table_id"
    },
    "save_dir": "./昆仑洞天资产库",
    "asset_prefix": "KD",
    "auto_rename": True,
    "field_mapping": {
        "asset_name": "资产名称",
        "sha256": "SHA256哈希",
        "file_size": "文件大小(MB)",
        "source_url": "原始URL",
        "created_at": "入库时间",
        "asset_type": "资产类型",
        "description": "描述",
        "did": "DID标识",
        "trace_mark": "溯源标识"
    }
}


def load_config():
    """加载配置文件，不存在则创建默认模板"""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        print(f"[配置] 已生成默认配置文件: {CONFIG_FILE}")
        print("[配置] 请编辑该文件，填写 base_token 和 table_id 后重新运行")
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_clipboard_url():
    """从剪贴板读取URL（Windows/macOS/Linux兼容）"""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        text = text.strip()
        if text.startswith("http"):
            return text
    except Exception:
        pass

    # Windows备用方案
    try:
        import subprocess
        result = subprocess.run(["powershell", "-Command", "Get-Clipboard"],
                                capture_output=True, text=True, timeout=5)
        text = result.stdout.strip()
        if text.startswith("http"):
            return text
    except Exception:
        pass

    return None


def download_file(url, save_path):
    """下载文件，支持重定向和大文件"""
    print(f"[下载] 开始下载: {url[:80]}...")

    # 创建不验证SSL的上下文（部分CDN证书问题）
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(save_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = downloaded / total_size * 100
                        print(f"\r[下载] 进度: {pct:.1f}% ({downloaded//1024}KB/{total_size//1024}KB)", end="", flush=True)
            print()  # 换行
        return True, os.path.getsize(save_path)
    except Exception as e:
        print(f"\n[下载] 失败: {e}")
        return False, 0


def calc_sha256(file_path):
    """计算文件SHA256哈希"""
    print("[哈希] 计算SHA256...")
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest().upper()


def get_feishu_token(app_id, app_secret):
    """获取飞书tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode())
        if result.get("code") == 0:
            return result["tenant_access_token"]
        else:
            raise Exception(f"获取飞书token失败: {result}")


def write_to_feishu_base(config, record_data):
    """写入飞书多维表格"""
    feishu = config["feishu"]
    mapping = config["field_mapping"]

    # 检查是否填写了base_token
    if "请填写" in feishu["base_token"] or "请填写" in feishu["table_id"]:
        print("[飞书] ⚠️ 未配置 base_token 或 table_id，跳过飞书写入")
        print("[飞书] 请编辑 asset_ingest_config.json 填写后重新运行")
        return False

    try:
        token = get_feishu_token(feishu["app_id"], feishu["app_secret"])
        print(f"[飞书] 获取token成功")

        # 构建字段映射
        fields = {}
        for key, field_name in mapping.items():
            if key in record_data:
                fields[field_name] = record_data[key]

        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{feishu['base_token']}/tables/{feishu['table_id']}/records"
        data = json.dumps({"fields": fields}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if result.get("code") == 0:
                record_id = result["data"]["record"]["record_id"]
                print(f"[飞书] ✅ 写入成功，record_id: {record_id}")
                return True
            else:
                print(f"[飞书] ❌ 写入失败: {result}")
                return False
    except Exception as e:
        print(f"[飞书] ❌ 写入异常: {e}")
        return False


def generate_asset_name(config, url, custom_name=None):
    """生成资产文件名"""
    if custom_name:
        return custom_name

    if config.get("auto_rename", True):
        now = datetime.datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        prefix = config.get("asset_prefix", "KD")
        return f"{prefix}-{date_str}-{time_str}.mp4"
    else:
        # 从URL提取文件名
        path = urllib.parse.urlparse(url).path
        filename = os.path.basename(path)
        if not filename or "." not in filename:
            filename = f"asset_{int(datetime.datetime.now().timestamp())}.mp4"
        return filename


def main():
    parser = argparse.ArgumentParser(description="昆仑洞天资产一键入库工具")
    parser.add_argument("--url", help="视频URL（不填则从剪贴板读取）")
    parser.add_argument("--name", help="自定义文件名")
    parser.add_argument("--desc", help="资产描述", default="")
    parser.add_argument("--type", help="资产类型", default="视频")
    args = parser.parse_args()

    print("=" * 60)
    print("  昆仑洞天短剧资产一键入库工具")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 60)

    # 1. 加载配置
    config = load_config()

    # 2. 获取URL
    url = args.url or get_clipboard_url()
    if not url:
        print("[错误] 未找到URL，请先复制视频链接到剪贴板，或使用 --url 参数")
        sys.exit(1)
    print(f"[URL] {url}")

    # 3. 准备保存目录
    save_dir = config.get("save_dir", "./昆仑洞天资产库")
    os.makedirs(save_dir, exist_ok=True)

    # 4. 生成文件名
    filename = generate_asset_name(config, url, args.name)
    save_path = os.path.join(save_dir, filename)
    print(f"[文件] 保存路径: {save_path}")

    # 5. 下载
    success, file_size = download_file(url, save_path)
    if not success:
        sys.exit(1)

    file_size_mb = round(file_size / 1024 / 1024, 2)
    print(f"[下载] ✅ 完成，大小: {file_size_mb} MB")

    # 6. 计算SHA256
    sha256 = calc_sha256(save_path)
    print(f"[哈希] SHA256: {sha256[:16]}...{sha256[-16:]}")

    # 7. 构建记录数据
    record_data = {
        "asset_name": filename,
        "sha256": sha256,
        "file_size": file_size_mb,
        "source_url": url,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "asset_type": args.type,
        "description": args.desc,
        "did": "DID-BR-000002",
        "trace_mark": "Ω₀⊂⊙∞⊂Ω"
    }

    # 8. 写入飞书Base
    feishu_ok = write_to_feishu_base(config, record_data)

    # 9. 生成本地入库清单
    manifest_path = os.path.join(save_dir, "资产入库清单.jsonl")
    with open(manifest_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record_data, ensure_ascii=False) + "\n")
    print(f"[本地] ✅ 已追加到本地清单: {manifest_path}")

    # 10. 总结
    print()
    print("=" * 60)
    print("  入库完成")
    print("=" * 60)
    print(f"  文件名: {filename}")
    print(f"  大小: {file_size_mb} MB")
    print(f"  SHA256: {sha256}")
    print(f"  飞书台账: {'✅ 已写入' if feishu_ok else '⚠️ 未写入（需配置base_token）'}")
    print(f"  本地清单: ✅ 已记录")
    print("=" * 60)


if __name__ == "__main__":
    main()
