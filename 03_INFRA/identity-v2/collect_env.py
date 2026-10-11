#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""采集当前沙箱环境配置，生成环境指纹（作为身份派生的环境盐料）"""
import os, json, socket, hashlib, platform, subprocess

def sh(cmd, default=""):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=10).stdout.strip()
    except Exception:
        return default

env = {
    "hostname": socket.gethostname(),
    "container_id": sh("cat /etc/hostname"),
    "env_tag": os.environ.get("HOSTNAME", ""),          # VM-195-72-tencentos
    "workspace_id": "2f8a7d30-9c21-4f0b-1d3c-5be5c50e6000",
    "ide_space_host": os.environ.get("X_IDE_SPACE_HOST", ""),
    "preview_domain": os.environ.get("X_IDE_PREVIEW_DOMAIN", ""),
    "python": platform.python_version(),
    "platform": platform.platform(),
    "machine": platform.machine(),
    "os_release": sh("cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2").strip('"'),
    "kernel": platform.release(),
}

# 环境指纹：对稳定标识做 SHA256（不含易变的 IP）
stable = "|".join([
    env["container_id"], env["env_tag"], env["workspace_id"],
    env["ide_space_host"], env["preview_domain"], env["machine"],
])
env["env_fingerprint"] = hashlib.sha256(stable.encode()).hexdigest()
env["env_fingerprint_short"] = env["env_fingerprint"][:16].upper()

print(json.dumps(env, ensure_ascii=False, indent=2))
