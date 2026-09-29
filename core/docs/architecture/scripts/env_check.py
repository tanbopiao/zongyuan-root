#!/usr/bin/env python3
"""
火斗云智AIOS 一键环境检测脚本
检测服务器环境是否满足部署要求
"""
import sys
import os
import shutil
import platform
import subprocess
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    ok = version >= (3, 8)
    return {
        "name": "Python版本",
        "current": f"{version.major}.{version.minor}.{version.micro}",
        "required": ">= 3.8",
        "ok": ok,
        "suggestion": "请升级Python到3.8以上" if not ok else ""
    }

def check_disk_space(path="/"):
    """检查磁盘空间"""
    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024**3)
    ok = free_gb >= 10
    return {
        "name": "磁盘空间",
        "current": f"剩余 {free_gb:.1f} GB",
        "required": ">= 10 GB",
        "ok": ok,
        "suggestion": "磁盘空间不足，请清理至少10GB" if not ok else ""
    }

def check_memory():
    """检查内存"""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if "MemTotal" in line:
                    total_kb = int(line.split()[1])
                    total_gb = total_kb / (1024**2)
                    ok = total_gb >= 1
                    return {
                        "name": "内存",
                        "current": f"{total_gb:.1f} GB",
                        "required": ">= 1 GB",
                        "ok": ok,
                        "suggestion": "内存不足，建议至少1GB" if not ok else ""
                    }
    except Exception:
        pass
    return {"name": "内存", "current": "未知", "required": ">= 1 GB", "ok": True, "suggestion": ""}

def check_network():
    """检查网络连通性"""
    import urllib.request
    try:
        req = urllib.request.Request("https://www.huodouai.com", method="HEAD")
        with urllib.request.urlopen(req, timeout=5) as resp:
            ok = resp.status == 200
            return {
                "name": "网络连通性",
                "current": f"HTTP {resp.status}",
                "required": "可访问外网",
                "ok": ok,
                "suggestion": "无法访问外网，请检查网络" if not ok else ""
            }
    except Exception as e:
        return {
            "name": "网络连通性",
            "current": f"连接失败: {str(e)[:30]}",
            "required": "可访问外网",
            "ok": False,
            "suggestion": "无法访问外网，请检查网络连接"
        }

def check_git():
    """检查Git"""
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        ok = result.returncode == 0
        return {
            "name": "Git",
            "current": result.stdout.strip() if ok else "未安装",
            "required": "已安装",
            "ok": ok,
            "suggestion": "请安装Git: apt install git" if not ok else ""
        }
    except FileNotFoundError:
        return {"name": "Git", "current": "未安装", "required": "已安装", "ok": False, "suggestion": "请安装Git"}

def check_port(port=80):
    """检查端口占用"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        return {"name": f"端口{port}", "current": "可用", "required": "可用", "ok": True, "suggestion": ""}
    except OSError:
        return {"name": f"端口{port}", "current": "已占用", "required": "可用", "ok": False, "suggestion": f"端口{port}已被占用，请释放"}
    finally:
        s.close()

def main():
    print("=" * 50)
    print("  火斗云智AIOS 环境检测")
    print("=" * 50)
    print()

    checks = [
        check_python_version(),
        check_disk_space(),
        check_memory(),
        check_network(),
        check_git(),
        check_port(80),
        check_port(443),
    ]

    passed = 0
    failed = 0

    for check in checks:
        status = "✓ 通过" if check["ok"] else "✗ 失败"
        print(f"  [{status}] {check['name']}")
        print(f"         当前: {check['current']}")
        print(f"         要求: {check['required']}")
        if not check["ok"] and check["suggestion"]:
            print(f"         建议: {check['suggestion']}")
        print()

        if check["ok"]:
            passed += 1
        else:
            failed += 1

    print("=" * 50)
    print(f"  检测完成: {passed} 通过, {failed} 失败")
    print("=" * 50)

    if failed == 0:
        print("  ✓ 环境检查全部通过，可以部署！")
    else:
        print("  ✗ 存在问题，请先修复后再部署")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
