#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 修复 Python SSL 问题的备用方案

方案:
1. pip install --upgrade certifi (使用纯 Python 实现)
2. 手动下载 Mozilla CA 证书 bundle
3. 设置 PYTHONSSL_CERT环境指北新证书

锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""
import os, sys, subprocess, ssl, urllib.request, json
from pathlib import Path
from datetime import datetime

# ==================== 日志工具 ====================

def log(message, level="INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

# ==================== 检测当前状态 ====================

def check_current_ssl_status():
    """检查当前 SSL 环境状态"""
    log("=" * 70)
    log(" 🔍 检测当前 Python SSL 环境")
    log("=" * 70)
    
    # 检查 Python 版本
    log(f"\nPython 版本：{sys.version}")
    
    # 检查 OpenSSL 版本
    try:
        ssl_version = ssl.OPENSSL_VERSION
        log(f"OpenSSL 版本：{ssl_version}")
    except Exception as e:
        log(f"❌ 无法获取 OpenSSL 版本：{e}", "ERROR")
    
    # 检查 certifi 是否安装
    try:
        import certifi
        ca_bundle = certifi.where()
        log(f"✅ certifi 已安装：{ca_bundle}")
        
        # 验证证书文件是否存在
        if os.path.exists(ca_bundle):
            file_size = os.path.getsize(ca_bundle)
            log(f"   证书文件大小：{file_size:,} bytes ({file_size/1024:.1f} KB)")
        else:
            log(f"   ⚠️  证书文件不存在", "WARNING")
    except ImportError:
        log("⚠️  certifi 未安装", "WARNING")
        ca_bundle = None
    
    # 测试 HTTPS 请求
    log("\n测试 HTTPS 请求...")
    test_https_request()
    
    return ca_bundle

def test_https_request(url="https://www.huodouai.com/dal/health"):
    """测试 HTTPS 请求"""
    try:
        response = urllib.request.urlopen(url, timeout=10)
        data = response.read().decode('utf-8')
        status_code = response.status
        log(f"✅ HTTPS 请求成功")
        log(f"   URL: {url}")
        log(f"   状态码：{status_code}")
        log(f"   响应：{data[:100]}")
        return True
    except ssl.SSLCertVerificationError as e:
        log(f"❌ SSL 证书验证失败：{e}", "ERROR")
        return False
    except urllib.error.URLError as e:
        log(f"❌ URL 错误：{e.reason}", "ERROR")
        return False
    except Exception as e:
        log(f"❌ 异常：{e}", "ERROR")
        return False

# ==================== 修复方案 ====================

def upgrade_certifi():
    """升级 certifi 包（最推荐的方式）"""
    log("\n开始升级 certifi 包...")
    
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "certifi"]
    
    log(f"执行命令：{' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        log("✅ certifi 升级成功")
        
        # 显示新版本信息
        try:
            import certifi
            ca_bundle = certifi.where()
            log(f"   CA 证书路径：{ca_bundle}")
            
            # 尝试再次测试 HTTPS
            test_https_request()
            return True
        except ImportError:
            log("⚠️  certifi 导入失败", "WARNING")
            return False
    else:
        log(f"❌ certifi 升级失败", "ERROR")
        log(f"   输出：{result.stderr}", "DEBUG")
        return False

def download_mozilla_ca_bundle():
    """手动下载 Mozilla CA 证书 bundle"""
    log("\n手动下载 Mozilla CA 证书 bundle...")
    
    target_dir = Path("/etc/pki/ca-trust/source/anchors")
    target_file = target_dir / "mozilla-ca-bundle.pem"
    backup_file = target_dir / "mozilla-ca-bundle.bak.pem"
    
    # 确保目录存在
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 备份现有证书
    if target_file.exists():
        shutil.copy(target_file, backup_file)
        log(f"   已备份原有证书到：{backup_file}")
    
    # 下载新证书
    url = "https://curl.se/ca/cacert.pem"
    log(f"   从 {url} 下载...")
    
    try:
        response = urllib.request.urlopen(url, timeout=30)
        cert_data = response.read().decode('utf-8')
        
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(cert_data)
        
        log(f"✅ CA 证书 bundle 下载成功")
        log(f"   路径：{target_file}")
        log(f"   大小：{len(cert_data):,} bytes")
        
        # 更新系统信任库
        update_system_trust()
        
        return True
    except Exception as e:
        log(f"❌ 下载失败：{e}", "ERROR")
        return False

def update_system_trust():
    """更新系统信任库"""
    log("\n更新系统信任库...")
    
    commands = [
        "update-ca-trust force-enable",
        "update-ca-trust"
    ]
    
    for cmd in commands:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                log(f"✅ 命令成功：{cmd}")
            else:
                log(f"⚠️  命令返回非零但继续：{cmd}", "WARNING")
        except Exception as e:
            log(f"⚠️  命令执行异常：{cmd} - {e}", "WARNING")

def set_python_ssl_env_vars(ca_bundle_path=None):
    """设置 Python SSL 环境变量"""
    if not ca_bundle_path:
        try:
            import certifi
            ca_bundle_path = certifi.where()
        except:
            log("❌ 找不到 CA 证书路径", "ERROR")
            return False
    
    log(f"\n设置 Python SSL 环境变量...")
    log(f"   REQUESTS_CA_BUNDLE={ca_bundle_path}")
    log(f"   SSL_CERT_FILE={ca_bundle_path}")
    
    # 在当前会话中设置
    os.environ['REQUESTS_CA_BUNDLE'] = ca_bundle_path
    os.environ['SSL_CERT_FILE'] = ca_bundle_path
    
    log("✅ 环境变量已设置")
    
    # 创建启动脚本
    script_content = f"""#!/bin/bash
export REQUESTS_CA_BUNDLE={ca_bundle_path}
export SSL_CERT_FILE={ca_bundle_path}
echo "Python SSL 环境变量已加载"
"""
    
    script_path = Path("/zongyuan-yuanji/scripts/load_ssl_env.sh")
    script_path.write_text(script_content)
    os.chmod(script_path, 0o755)
    
    log(f"ℹ️  永久生效请运行：source {script_path}")
    log(f"ℹ️  或添加到 ~/.bashrc:")
    log(f"   export REQUESTS_CA_BUNDLE={ca_bundle_path}")
    log(f"   export SSL_CERT_FILE={ca_bundle_path}")
    
    return True

# ==================== 完整修复流程 ====================

def full_fix():
    """完整的 SSL 修复流程"""
    log("=" * 70)
    log(" 🛠️  ZONGYUAN-ROOT Python SSL 环境修复")
    log("=" * 70)
    
    start_time = datetime.now()
    
    # Step 1: 检查当前状态
    check_current_ssl_status()
    
    # Step 2: 升级 certifi（首选方案）
    log("\n" + "-" * 70)
    log("[Step 1/3] 升级 certifi 包 (首选方案)")
    log("-" * 70)
    if upgrade_certifi():
        log("\n✅ 首选方案成功，无需继续后续步骤")
    else:
        log("\n⚠️  首选方案失败，尝试备用方案...", "WARNING")
        
        # Step 3: 下载 Mozilla CA bundle（备选方案）
        log("\n" + "-" * 70)
        log("[Step 2/3] 下载 Mozilla CA 证书 bundle (备选方案)")
        log("-" * 70)
        if download_mozilla_ca_bundle():
            log("\n✅ 备选方案成功")
        else:
            log("\n⚠️  备选方案也失败，尝试环境变量方案...", "WARNING")
    
    # Step 4: 设置环境变量（兜底方案）
    log("\n" + "-" * 70)
    log("[Step 3/3] 设置 Python SSL 环境变量 (兜底方案)")
    log("-" * 70)
    try:
        import certifi
        set_python_ssl_env_vars(certifi.where())
    except ImportError:
        log("⚠️  certifi 不可用，跳过此步", "WARNING")
    
    # Step 5: 最终验证
    log("\n" + "=" * 70)
    log(" 📊 最终验证")
    log("=" * 70)
    
    success_count = 0
    total_tests = 3
    
    test_urls = [
        "https://www.huodouai.com/dal/health",
        "https://www.huodouai.com/api/status",
        "https://api.huodouai.com/a2a/nodes"
    ]
    
    for url in test_urls:
        if test_https_request(url):
            success_count += 1
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    log("\n" + "=" * 70)
    log(" 🏆 SSL 修复结果统计")
    log("=" * 70)
    log(f"   ✅ 耗时：{elapsed:.2f} 秒")
    log(f"   ✅ 成功测试：{success_count}/{total_tests} 个 URL")
    
    if success_count == total_tests:
        log("   🎉 所有测试通过！Python SSL 环境完全正常")
        log("\n现在可以正常使用以下功能:")
        log("   • 双核同步引擎 (sync.py)")
        log("   • 真值上报客户端 (report_truth_no_token.py)")
        log("   • 同源节点申请 (apply_homologous_node.py)")
    else:
        log("   ⚠️  仍有部分 URL 测试失败", "WARNING")
        log("\n建议:")
        log("   1. 检查网络连接是否正常")
        log("   2. 确认域名 DNS 解析是否正确")
        log("   3. 查看完整日志了解详细错误")
    log("=" * 70)
    
    return success_count == total_tests

# ==================== 主入口 ====================

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT Python SSL 环境修复工具")
    parser.add_argument("--full", action="store_true", help="执行完整修复流程")
    parser.add_argument("--check", action="store_true", help="仅检查当前状态")
    parser.add_argument("--upgrade-certifi", action="store_true", help="仅升级 certifi 包")
    parser.add_argument("--download-ca", action="store_true", help="仅下载 CA 证书 bundle")
    parser.add_argument("--set-env", action="store_true", help="仅设置环境变量")
    parser.add_argument("--test", action="store_true", help="测试 HTTPS 连接")
    
    args = parser.parse_args()
    
    if args.check:
        check_current_ssl_status()
    elif args.upgrade_certifi:
        upgrade_certifi()
    elif args.download_ca:
        download_mozilla_ca_bundle()
    elif args.set_env:
        try:
            import certifi
            set_python_ssl_env_vars(certifi.where())
        except ImportError:
            log("❌ certifi 未安装，请先运行--upgrade-certifi", "ERROR")
    elif args.test:
        test_https_request()
    elif args.full:
        full_fix()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
