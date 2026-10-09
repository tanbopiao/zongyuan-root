#!/usr/bin/env python3
"""
腾讯云COS同步通道 (cos_sync.py)
ZONGYUAN-ROOT 元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

通过腾讯云对象存储(COS)实现大文件高效同步：
- 分片上传（大文件自动分片）
- 断点续传
- 并发上传
- 版本管理
- 内网高速访问（腾讯云服务器）

【配置说明】
使用前需在 cos_config.json 中配置：
{
    "secret_id": "你的SecretId",
    "secret_key": "你的SecretKey",
    "region": "ap-guangzhou",
    "bucket": "your-bucket-name-1250000000",
    "prefix": "zongyuan-root/sync/"
}

用法：
  python3 cos_sync.py --upload --file <文件路径>
  python3 cos_sync.py --download --key <对象键> --output <输出路径>
  python3 cos_sync.py --list
  python3 cos_sync.py --delete --key <对象键>
  python3 cos_sync.py --sync --dir <本地目录>
"""
import json
import os
import hashlib
import argparse
from datetime import datetime

DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"
CONFIG_FILE = "cos_config.json"


def load_config():
    """加载COS配置"""
    if not os.path.exists(CONFIG_FILE):
        print(f"  ⚠ 配置文件不存在: {CONFIG_FILE}")
        print(f"  请创建配置文件，填入腾讯云SecretId/SecretKey/Bucket信息")
        return None
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_cos_sdk():
    """检查COS SDK是否安装"""
    try:
        from qcloud_cos import CosConfig, CosS3Client
        return True
    except ImportError:
        print(f"  ⚠ 腾讯云COS SDK未安装")
        print(f"  请执行: pip install cos-python-sdk-v5")
        return False


def sha256_file(filepath):
    """计算文件SHA256"""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest().upper()


def upload_file(file_path, config):
    """上传文件到COS（支持分片上传和断点续传）"""
    from qcloud_cos import CosConfig, CosS3Client

    if not os.path.exists(file_path):
        print(f"  ✗ 文件不存在: {file_path}")
        return False

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    file_hash = sha256_file(file_path)
    key = f"{config.get('prefix', '')}{file_name}"

    print(f"[COS-SYNC] 上传文件")
    print(f"  文件: {file_path}")
    print(f"  大小: {file_size / 1024 / 1024:.2f} MB")
    print(f"  哈希: {file_hash[:32]}...")
    print(f"  对象键: {key}")

    cos_config = CosConfig(
        Region=config['region'],
        SecretId=config['secret_id'],
        SecretKey=config['secret_key']
    )
    client = CosS3Client(cos_config)

    try:
        # 大文件使用分片上传
        if file_size > 100 * 1024 * 1024:  # >100MB
            print(f"  使用分片上传...")
            response = client.upload_file(
                Bucket=config['bucket'],
                Key=key,
                LocalFilePath=file_path,
                PartSize=10,  # 10MB分片
                MAXThread=5,  # 5线程并发
                EnableMD5=False
            )
        else:
            print(f"  使用简单上传...")
            with open(file_path, 'rb') as f:
                response = client.put_object(
                    Bucket=config['bucket'],
                    Key=key,
                    Body=f
                )

        etag = response.get('ETag', 'unknown')
        print(f"  ✓ 上传成功，ETag: {etag}")

        # 设置自定义元数据
        client.put_object_tagging(
            Bucket=config['bucket'],
            Key=key,
            Tag={
                'TagSet': [
                    {'Key': 'did', 'Value': DID},
                    {'Key': 'trace_mark', 'Value': TRACE_MARK},
                    {'Key': 'sha256', 'Value': file_hash},
                    {'Key': 'upload_time', 'Value': datetime.now().isoformat()}
                ]
            }
        )
        return True
    except Exception as e:
        print(f"  ✗ 上传失败: {str(e)[:100]}")
        return False


def download_file(key, output_path, config):
    """从COS下载文件"""
    from qcloud_cos import CosConfig, CosS3Client

    print(f"[COS-SYNC] 下载文件")
    print(f"  对象键: {key}")
    print(f"  输出: {output_path}")

    cos_config = CosConfig(
        Region=config['region'],
        SecretId=config['secret_id'],
        SecretKey=config['secret_key']
    )
    client = CosS3Client(cos_config)

    try:
        response = client.get_object(
            Bucket=config['bucket'],
            Key=key
        )
        response['Body'].get_stream_to_file(output_path)
        file_hash = sha256_file(output_path)
        print(f"  ✓ 下载成功，哈希: {file_hash[:32]}...")
        return True
    except Exception as e:
        print(f"  ✗ 下载失败: {str(e)[:100]}")
        return False


def list_objects(config, prefix=None):
    """列出COS对象"""
    from qcloud_cos import CosConfig, CosS3Client

    print(f"[COS-SYNC] 列出对象")
    target_prefix = prefix or config.get('prefix', '')

    cos_config = CosConfig(
        Region=config['region'],
        SecretId=config['secret_id'],
        SecretKey=config['secret_key']
    )
    client = CosS3Client(cos_config)

    try:
        response = client.list_objects(
            Bucket=config['bucket'],
            Prefix=target_prefix,
            MaxKeys=100
        )
        objects = response.get('Contents', [])
        print(f"  找到 {len(objects)} 个对象:")
        for obj in objects:
            size_mb = int(obj.get('Size', 0)) / 1024 / 1024
            print(f"    - {obj.get('Key', 'unknown'):50s} | {size_mb:8.2f} MB | {obj.get('LastModified', 'unknown')}")
        return True
    except Exception as e:
        print(f"  ✗ 列出失败: {str(e)[:100]}")
        return False


def sync_directory(dir_path, config):
    """同步整个目录到COS"""
    print(f"[COS-SYNC] 同步目录: {dir_path}")
    if not os.path.isdir(dir_path):
        print(f"  ✗ 目录不存在")
        return False

    success_count = 0
    fail_count = 0
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            if upload_file(file_path, config):
                success_count += 1
            else:
                fail_count += 1

    print(f"\n  同步完成: 成功 {success_count}, 失败 {fail_count}")
    return fail_count == 0


def main():
    parser = argparse.ArgumentParser(description='腾讯云COS同步通道')
    parser.add_argument('--upload', action='store_true', help='上传文件')
    parser.add_argument('--download', action='store_true', help='下载文件')
    parser.add_argument('--list', action='store_true', help='列出对象')
    parser.add_argument('--delete', action='store_true', help='删除对象')
    parser.add_argument('--sync', action='store_true', help='同步目录')
    parser.add_argument('--file', type=str, help='文件路径')
    parser.add_argument('--key', type=str, help='对象键')
    parser.add_argument('--output', type=str, help='输出路径')
    parser.add_argument('--dir', type=str, help='目录路径')
    parser.add_argument('--prefix', type=str, help='前缀过滤')

    args = parser.parse_args()

    print("=" * 60)
    print("  腾讯云COS同步通道")
    print(f"  DID: {DID} | {TRACE_MARK}")
    print("=" * 60)

    config = load_config()
    if not config:
        print("\n  配置模板（保存为 cos_config.json）:")
        print(json.dumps({
            "secret_id": "你的SecretId",
            "secret_key": "你的SecretKey",
            "region": "ap-guangzhou",
            "bucket": "your-bucket-name-1250000000",
            "prefix": "zongyuan-root/sync/"
        }, indent=2, ensure_ascii=False))
        return

    if not check_cos_sdk():
        return

    if args.upload and args.file:
        upload_file(args.file, config)
    elif args.download and args.key and args.output:
        download_file(args.key, args.output, config)
    elif args.list:
        list_objects(config, args.prefix)
    elif args.sync and args.dir:
        sync_directory(args.dir, config)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
