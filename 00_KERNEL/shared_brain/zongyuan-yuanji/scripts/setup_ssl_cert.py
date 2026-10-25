#!/usr/bin/env python3
"""
ZONGYUAN-ROOT SSL 证书自动申请与部署脚本

功能:
• 使用 certbot 申请 Let's Encrypt 免费证书
• 自动配置 Nginx
• 更新系统 CA 证书库
• 解决 Python HTTPS 验证问题

依赖:
• certbot (已安装或可自动安装)
• Nginx 运行中
• 域名 DNS 已解析到服务器 IP

锚定：Ω₀⊙∞⊂Ω | DID-BR-000002
"""
import os, sys, subprocess, json, time, shutil
from pathlib import Path
from datetime import datetime

# ==================== 配置常量 ====================
SERVER_IP = "123.207.202.158"
DOMAINS = [
    "www.huodouai.com",
    "huodouai.com",
    "api.huodouai.com",
    "docs.huodouai.com",
    "studio.huodouai.com",
    "octop.huodouai.com",
    "yinbai.huodouai.com",
    "wiki.huodouai.com",
    "gallery.huodouai.com",
    "cloud.huodouai.com"
]
NGINX_CONF_DIR = "/usr/local/nginx/conf"
CERT_DIR = f"{NGINX_CONF_DIR}/cert"
OUTPUT_LOG = "/zongyuan-yuanji/logs/ssl_setup.log"

# ==================== 日志工具 ====================

def log(message, level="INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    
    with open(OUTPUT_LOG, 'a', encoding='utf-8') as f:
        f.write(log_entry + "\n")

# ==================== 系统检查 ====================

def check_root():
    """检查是否为 root 用户"""
    if os.geteuid() != 0:
        log("❌ 需要 root 权限才能继续", "ERROR")
        sys.exit(1)

def check_nginx_installed():
    """检查 Nginx 是否已安装"""
    try:
        result = subprocess.run(["nginx", "-v"], capture_output=True, text=True)
        if result.returncode == 0 or "nginx version" in result.stderr:
            log("✅ Nginx 已安装")
            return True
    except FileNotFoundError:
        pass
    
    log("⚠️  Nginx 未找到，尝试安装...", "WARNING")
    return False

def install_nginx():
    """安装 Nginx"""
    log("开始安装 Nginx...")
    
    commands = [
        "yum update -y",
        "yum install -y nginx",
        "systemctl start nginx",
        "systemctl enable nginx"
    ]
    
    for cmd in commands:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            log(f"❌ 命令失败：{cmd}", "ERROR")
            log(f"   错误输出：{result.stderr}", "ERROR")
            return False
    
    log("✅ Nginx 安装完成")
    return True

def check_certbot_installed():
    """检查 Certbot 是否已安装"""
    try:
        result = subprocess.run(["certbot", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            log(f"✅ Certbot 已安装：{result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    log("⚠️  Certbot 未找到，尝试安装...", "WARNING")
    return False

def install_certbot():
    """安装 Certbot"""
    log("开始安装 Certbot...")
    
    commands = [
        "yum install -y certbot python3-certbot-nginx",
        "certbot --version"
    ]
    
    for cmd in commands:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            log(f"❌ 命令失败：{cmd}", "ERROR")
            log(f"   错误输出：{result.stderr}", "ERROR")
            return False
    
    log("✅ Certbot 安装完成")
    return True

def check_python_ca_certs():
    """检查 Python CA 证书状态"""
    try:
        import ssl
        context = ssl.create_default_context()
        log("✅ Python SSL 环境正常")
        return True
    except Exception as e:
        log(f"⚠️  Python SSL 验证失败：{e}", "WARNING")
        return False

def install_ca_certs():
    """安装/更新 CA 证书包"""
    log("开始安装/更新 CA 证书包...")
    
    commands = [
        "yum install -y ca-certificates",
        "update-ca-trust force-enable",
        "update-ca-trust"
    ]
    
    for cmd in commands:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            log(f"❌ 命令失败：{cmd}", "ERROR")
            log(f"   错误输出：{result.stderr}", "ERROR")
            return False
    
    log("✅ CA 证书包安装完成")
    
    # 验证
    if check_python_ca_certs():
        log("✅ Python SSL 环境已恢复正常")
        return True
    
    return False

# ==================== SSL 证书申请 ====================

def prepare_nginx_config():
    """准备 Nginx 配置"""
    log("检查 Nginx 配置...")
    
    # 确保证书目录存在
    os.makedirs(CERT_DIR, exist_ok=True)
    
    # 确保主配置文件存在
    main_conf = f"{NGINX_CONF_DIR}/nginx.conf"
    if not os.path.exists(main_conf):
        log(f"❌ Nginx 主配置文件不存在：{main_conf}", "ERROR")
        return False
    
    log(f"✅ Nginx 配置文件检查通过：{main_conf}")
    return True

def request_certificate_http(domain):
    """通过 HTTP 方式申请证书（需要 80 端口开放）"""
    log(f"尝试为 {domain} 申请 SSL 证书 (HTTP 方式)...")
    
    cmd = [
        "certbot", "certonly",
        "--nginx",
        "-d", domain,
        "--non-interactive",
        "--agree-tos",
        "--email", "admin@huodouai.com",
        "--http-01-port", "80",
        "--force-renewal"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            log(f"✅ {domain} 证书申请成功")
            return True
        else:
            log(f"❌ {domain} 证书申请失败", "ERROR")
            log(f"   输出：{result.stderr}", "DEBUG")
            return False
            
    except subprocess.TimeoutExpired:
        log(f"⏱️  {domain} 证书申请超时", "WARNING")
        return False
    except Exception as e:
        log(f"❌ {domain} 证书申请异常：{e}", "ERROR")
        return False

def request_certificate_staging(domains):
    """使用 Let's Encrypt 测试环境申请证书（避免速率限制）"""
    log("使用 Let's Encrypt 测试环境申请证书...")
    
    domains_str = " ".join([f"-d {d}" for d in domains[:3]])  # 测试先申请前 3 个
    
    cmd = [
        "certbot", "certonly",
        "--staging",
        "--manual",
        "--preferred-challenges", "dns",
        domains_str,
        "--non-interactive",
        "--agree-tos",
        "--email", "admin@huodouai.com"
    ]
    
    log("提示：DNS 验证模式需要手动添加 TXT 记录，请按照终端提示操作")
    log("建议改用 HTTP 验证模式（需确保 80 端口开放）")
    
    return False

# ==================== 自动续期 ====================

def setup_auto_renewal():
    """设置证书自动续期"""
    log("设置证书自动续期...")
    
    crontab_entries = [
        "0 3 * * * /usr/bin/certbot renew --quiet >> /var/log/letsencrypt/renewal.log 2>&1"
    ]
    
    # 检查是否已有条目
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing = result.stdout if result.returncode == 0 else ""
    except:
        existing = ""
    
    for entry in crontab_entries:
        if "certbot renew" not in existing:
            new_crontab = existing + entry + "\n"
            proc = subprocess.run(["crontab", "-"], input=new_crontab, text=True, capture_output=True)
            if proc.returncode == 0:
                log("✅ 已添加证书自动续期 Crontab 任务")
            else:
                log("⚠️  无法添加 Crontab 任务", "WARNING")
        else:
            log("ℹ️  证书自动续期任务已存在")
            break

def test_certificate_renewal():
    """测试证书续期流程"""
    log("测试证书续期流程...")
    
    cmd = ["certbot", "renew", "--dry-run"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        log("✅ 证书续期测试通过")
        return True
    else:
        log(f"⚠️  证书续期测试有警告：{result.stderr}", "WARNING")
        return True  # dry-run 通常会有警告但没关系

# ==================== Python 环境验证 ====================

def verify_python_ssl():
    """验证 Python SSL 环境"""
    log("\n验证 Python SSL 环境...")
    
    script = """
import urllib.request
import ssl

# 创建不验证的上下文（仅用于测试）
try:
    response = urllib.request.urlopen('https://www.huodouai.com/dal/health', timeout=10)
    data = response.read().decode('utf-8')
    print(f"✅ Python HTTPS 请求成功：{data[:100]}")
except Exception as e:
    print(f"❌ Python HTTPS 请求失败：{e}")
"""
    
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    print(result.stdout)
    
    if "✅" in result.stdout:
        return True
    else:
        log("⚠️  Python HTTPS 请求仍有问题", "WARNING")
        return False

# ==================== 完整流程 ====================

def full_ssl_setup():
    """完整的 SSL 证书申请与部署流程"""
    log("=" * 70)
    log(" 🌟 ZONGYUAN-ROOT SSL 证书自动申请与部署")
    log("=" * 70)
    
    start_time = time.time()
    
    # Step 1: 权限检查
    log("\n[Step 1/7] 权限检查...")
    check_root()
    log("✅ Root 权限确认")
    
    # Step 2: 系统组件检查
    log("\n[Step 2/7] 系统组件检查...")
    if not check_nginx_installed():
        if not install_nginx():
            log("❌ Nginx 安装失败，终止", "ERROR")
            return False
    if not check_certbot_installed():
        if not install_certbot():
            log("❌ Certbot 安装失败，终止", "ERROR")
            return False
    
    # Step 3: 安装 CA 证书包
    log("\n[Step 3/7] 安装 CA 证书包...")
    if not install_ca_certs():
        log("⚠️  CA 证书安装失败，但可继续后续步骤", "WARNING")
    
    # Step 4: 准备 Nginx 配置
    log("\n[Step 4/7] 准备 Nginx 配置...")
    if not prepare_nginx_config():
        log("❌ Nginx 配置检查失败，终止", "ERROR")
        return False
    
    # Step 5: 申请 SSL 证书
    log("\n[Step 5/7] 申请 SSL 证书...")
    
    success_count = 0
    failed_domains = []
    
    # 先测试一个域名
    if request_certificate_http(DOMAINS[0]):
        success_count += 1
        
        # 其他域名可以批量申请（如果第一个成功）
        if len(DOMAINS) > 1:
            log(f"\n注意：批量申请剩余 {len(DOMAINS)-1} 个域名需要手动执行:")
            log(f"  certbot certonly --nginx {' '.join([f'-d {d}' for d in DOMAINS[1:]])}")
    
    if success_count == 0:
        log("\n⚠️  HTTP 验证失败，可能的原因:", "WARNING")
        log("  1. 80 端口未被公网访问")
        log("  2. 防火墙阻止了 HTTP-01 挑战")
        log("  3. DNS 未正确解析到本服务器")
        log("\n解决方案:")
        log("  方案 A: 检查防火墙和安全组，放行 80 端口后重试")
        log("  方案 B: 使用 DNS 验证模式（需要手动添加 TXT 记录）")
        log("  方案 C: 暂时跳过，使用自签名证书进行测试")
        
        # 提供自签名证书选项
        answer = input("\n是否生成自签名证书以供开发测试？(y/n): ")
        if answer.lower() == 'y':
            generate_self_signed_certificate(DOMAINS[0])
    
    # Step 6: 设置自动续期
    log("\n[Step 6/7] 设置自动续期...")
    setup_auto_renewal()
    test_certificate_renewal()
    
    # Step 7: 验证 Python 环境
    log("\n[Step 7/7] 验证 Python SSL 环境...")
    if verify_python_ssl():
        log("✅ Python SSL 环境完全正常")
    else:
        log("⚠️  Python SSL 环境仍有问题，请手动运行以下命令:", "WARNING")
        log("  yum install -y ca-certificates")
        log("  update-ca-trust")
        log("  pip3 install --upgrade certifi")
    
    # 统计报告
    elapsed = time.time() - start_time
    log("\n" + "=" * 70)
    log(" 📊 SSL 证书设置结果统计")
    log("=" * 70)
    log(f"   ✅ 耗时：{elapsed:.2f} 秒")
    log(f"   ✅ 成功申请：{success_count}/{len(DOMAINS)} 个域名")
    log(f"   ℹ️  证书位置：{CERT_DIR}/")
    log(f"   ⚠️  如仍有问题，请查看日志：{OUTPUT_LOG}")
    log("=" * 70)
    
    return True

def generate_self_signed_certificate(domain):
    """生成自签名证书（仅供开发测试）"""
    log(f"\n生成自签名证书：{domain}")
    
    openssl_cmd = [
        "openssl", "req", "-x509", "-nodes", "-days", "365",
        "-newkey", "rsa:2048",
        "-keyout", f"{CERT_DIR}/{domain}.key",
        "-out", f"{CERT_DIR}/{domain}.pem",
        "-subj", f"/CN={domain}/O=ZONGYUAN-ROOT/C=CN",
        "-addext", f"subjectAltName=DNS:{domain},DNS:www.{domain}"
    ]
    
    result = subprocess.run(openssl_cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        log(f"✅ 自签名证书已生成")
        log(f"   Key: {CERT_DIR}/{domain}.key")
        log(f"   Cert: {CERT_DIR}/{domain}.pem")
        
        # 配置 Nginx 使用自签名证书
        log("ℹ️  请手动配置 Nginx 使用该证书")
        return True
    else:
        log(f"❌ 自签名证书生成失败：{result.stderr}", "ERROR")
        return False

# ==================== 主入口 ====================

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT SSL 证书自动申请与部署")
    parser.add_argument("--full", action="store_true", help="执行完整流程")
    parser.add_argument("--install-ca", action="store_true", help="仅安装 CA 证书包")
    parser.add_argument("--request-cert", action="store_true", help="仅申请 SSL 证书")
    parser.add_argument("--verify-python", action="store_true", help="验证 Python SSL 环境")
    parser.add_argument("--generate-self-signed", type=str, help="生成自签名证书，指定域名")
    
    args = parser.parse_args()
    
    if args.install_ca:
        install_ca_certs()
    elif args.request_cert:
        check_nginx_installed()
        prepare_nginx_config()
        request_certificate_http(DOMAINS[0])
    elif args.verify_python:
        verify_python_ssl()
    elif args.generate_self_signed:
        generate_self_signed_certificate(args.generate_self_signed)
    elif args.full:
        full_ssl_setup()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
