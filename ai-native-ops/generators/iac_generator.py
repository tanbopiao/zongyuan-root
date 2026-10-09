"""
ANCE IaC生成器
根据部署计划生成Terraform HCL / Ansible Playbook / Shell脚本
"""
import os
import json
from typing import Dict, List, Optional
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.intent_parser import DeploymentPlan


class TerraformGenerator:
    """Terraform HCL生成器"""

    def __init__(self, output_dir: str = "output/terraform"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, plan: DeploymentPlan) -> Dict[str, str]:
        """生成Terraform配置"""
        files = {}

        # main.tf
        files["main.tf"] = self._gen_main(plan)
        # variables.tf
        files["variables.tf"] = self._gen_variables(plan)
        # outputs.tf
        files["outputs.tf"] = self._gen_outputs()
        # provider.tf
        files["provider.tf"] = self._gen_provider(plan)

        # 写入文件
        for name, content in files.items():
            path = os.path.join(self.output_dir, name)
            with open(path, "w") as f:
                f.write(content)

        return files

    def _gen_provider(self, plan: DeploymentPlan) -> str:
        if plan.cloud_provider == "tencent":
            return '''terraform {
  required_providers {
    tencentcloud = {
      source  = "tencentcloudstack/tencentcloud"
      version = ">= 1.81.0"
    }
  }
}

provider "tencentcloud" {
  secret_id  = var.tencent_secret_id
  secret_key = var.tencent_secret_key
  region     = var.region
}
'''
        elif plan.cloud_provider == "aliyun":
            return '''terraform {
  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = ">= 1.220.0"
    }
  }
}

provider "alicloud" {
  access_key = var.aliyun_access_key
  secret_key = var.aliyun_secret_key
  region     = var.region
}
'''
        return "# 请配置云厂商provider\n"

    def _gen_main(self, plan: DeploymentPlan) -> str:
        if not plan.resources:
            return "# 无资源定义\n"

        r = plan.resources[0]
        if plan.cloud_provider == "tencent":
            return f'''# 腾讯云CVM实例
resource "tencentcloud_instance" "web_server" {{
  instance_name              = "ance-web-server"
  availability_zone          = "${{var.region}}-3"
  image_id                   = "img-22trbn9r"  # Ubuntu 22.04
  instance_type              = "S5.MEDIUM{r['cpu']}"  # {r['cpu']}核{r['memory_gb']}GB
  system_disk_type           = "CLOUD_PREMIUM"
  system_disk_size           = {r.get('disk_gb', 50)}
  vpc_id                     = var.vpc_id
  subnet_id                  = var.subnet_id
  key_name                   = var.ssh_key_name
  internet_max_bandwidth_out = 100
  charge_type                = "POSTPAID_BY_HOUR"

  tags = {{
    managed_by = "ANCE"
    pattern    = "ai-native-ops"
  }}
}}
'''
        return f'''# 云服务器实例（{plan.cloud_provider}）
# CPU: {r['cpu']}核, 内存: {r['memory_gb']}GB, 磁盘: {r.get('disk_gb', 50)}GB
# 请根据云厂商文档补充具体资源定义
'''

    def _gen_variables(self, plan: DeploymentPlan) -> str:
        return f'''variable "region" {{
  description = "云区域"
  type        = string
  default     = "{plan.region if plan.region != 'auto' else 'ap-guangzhou'}"
}}

variable "vpc_id" {{
  description = "VPC ID"
  type        = string
  default     = ""
}}

variable "subnet_id" {{
  description = "子网ID"
  type        = string
  default     = ""
}}

variable "ssh_key_name" {{
  description = "SSH密钥名称"
  type        = string
  default     = "ance-deploy-key"
}}

variable "tencent_secret_id" {{
  description = "腾讯云SecretId"
  type        = string
  sensitive   = true
}}

variable "tencent_secret_key" {{
  description = "腾讯云SecretKey"
  type        = string
  sensitive   = true
}}
'''

    def _gen_outputs(self) -> str:
        return '''output "instance_id" {
  description = "实例ID"
  value       = tencentcloud_instance.web_server.id
}

output "public_ip" {
  description = "公网IP"
  value       = tencentcloud_instance.web_server.public_ip
}

output "private_ip" {
  description = "内网IP"
  value       = tencentcloud_instance.web_server.private_ip
}
'''


class AnsibleGenerator:
    """Ansible Playbook生成器"""

    def __init__(self, output_dir: str = "output/ansible"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, plan: DeploymentPlan) -> Dict[str, str]:
        files = {}
        files["playbook.yml"] = self._gen_playbook(plan)
        files["inventory.ini"] = self._gen_inventory(plan)

        for name, content in files.items():
            path = os.path.join(self.output_dir, name)
            with open(path, "w") as f:
                f.write(content)
        return files

    def _gen_playbook(self, plan: DeploymentPlan) -> str:
        tasks = []

        # 系统更新
        tasks.append('''    - name: 更新系统包
      apt:
        update_cache: yes
        upgrade: dist
      when: ansible_os_family == "Debian"''')

        # 软件安装
        pkg_map = {
            "nginx": "nginx",
            "docker": ["docker.io", "docker-compose"],
            "mysql": "mysql-server",
            "redis": "redis-server",
            "certbot": ["certbot", "python3-certbot-nginx"],
            "ufw": "ufw",
            "nodejs": ["nodejs", "npm"],
            "python": ["python3", "python3-pip", "python3-venv"],
        }

        for sw in plan.software_stack:
            if sw in pkg_map:
                pkgs = pkg_map[sw] if isinstance(pkg_map[sw], list) else [pkg_map[sw]]
                tasks.append(f'''    - name: 安装 {sw}
      apt:
        name: {json.dumps(pkgs)}
        state: present''')

        # Docker服务启动
        if "docker" in plan.software_stack:
            tasks.append('''    - name: 启动Docker服务
      systemd:
        name: docker
        state: started
        enabled: yes''')

        # Nginx配置
        if "nginx" in plan.software_stack and plan.domain:
            tasks.append(f'''    - name: 配置Nginx站点
      template:
        src: nginx.conf.j2
        dest: /etc/nginx/sites-available/{plan.domain}
      notify: reload nginx

    - name: 启用站点
      file:
        src: /etc/nginx/sites-available/{plan.domain}
        dest: /etc/nginx/sites-enabled/{plan.domain}
        state: link''')

        # SSL
        if plan.ssl_enabled and plan.domain:
            tasks.append(f'''    - name: 申请SSL证书
      command: certbot --nginx -d {plan.domain} --non-interactive --agree-tos -m admin@{plan.domain}
      args:
        creates: /etc/letsencrypt/live/{plan.domain}/fullchain.pem''')

        # 防火墙
        tasks.append('''    - name: 配置防火墙
      ufw:
        rule: allow
        port: "{{ item }}"
        proto: tcp
      loop:
        - "22"
        - "80"
        - "443"

    - name: 启用防火墙
      ufw:
        state: enabled''')

        return f'''---
- name: ANCE 部署Playbook
  hosts: web_servers
  become: yes
  vars:
    domain: {plan.domain or "example.com"}

  tasks:
{chr(10).join(tasks)}

  handlers:
    - name: reload nginx
      systemd:
        name: nginx
        state: reloaded
'''

    def _gen_inventory(self, plan: DeploymentPlan) -> str:
        return f'''[web_servers]
# 部署后填入服务器IP
# server1 ansible_host=YOUR_SERVER_IP ansible_user=root ansible_ssh_private_key_file=~/.ssh/ance_key

[web_servers:vars]
ansible_python_interpreter=/usr/bin/python3
domain={plan.domain or "example.com"}
'''


class ShellGenerator:
    """Shell脚本生成器（轻量级部署）"""

    def __init__(self, output_dir: str = "output/shell"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, plan: DeploymentPlan) -> Dict[str, str]:
        script = f"""#!/bin/bash
# ANCE 自动部署脚本
# 云厂商: {plan.cloud_provider}
# 软件栈: {', '.join(plan.software_stack)}
# 域名: {plan.domain or '无'}

set -e

echo "=== ANCE 部署开始 ==="

# 1. 系统更新
echo "[1/5] 更新系统..."
apt-get update -qq
apt-get upgrade -y -qq

# 2. 安装基础工具
echo "[2/5] 安装基础工具..."
apt-get install -y curl wget git unzip ufw

# 3. 安装软件栈
echo "[3/5] 安装软件栈..."
"""
        pkg_map = {
            "nginx": "nginx",
            "docker": "docker.io docker-compose",
            "mysql": "mysql-server",
            "redis": "redis-server",
            "certbot": "certbot python3-certbot-nginx",
            "nodejs": "nodejs npm",
            "python": "python3 python3-pip python3-venv",
        }
        pkgs = [pkg_map[s] for s in plan.software_stack if s in pkg_map]
        if pkgs:
            script += f"apt-get install -y {' '.join(pkgs)}\n"

        script += f"""
# 4. 配置防火墙
echo "[4/5] 配置防火墙..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 5. 配置服务
echo "[5/5] 配置服务..."
"""
        if "docker" in plan.software_stack:
            script += "systemctl enable --now docker\n"
        if "nginx" in plan.software_stack:
            script += "systemctl enable --now nginx\n"
        if plan.ssl_enabled and plan.domain:
            script += f"certbot --nginx -d {plan.domain} --non-interactive --agree-tos -m admin@{plan.domain}\n"

        script += """
echo "=== 部署完成 ==="
echo "服务器IP: $(curl -s ifconfig.me)"
"""

        path = os.path.join(self.output_dir, "deploy.sh")
        with open(path, "w") as f:
            f.write(script)
        os.chmod(path, 0o755)
        return {"deploy.sh": script}


import json


class IacGenerator:
    """IaC统一生成器"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.terraform = TerraformGenerator(os.path.join(output_dir, "terraform"))
        self.ansible = AnsibleGenerator(os.path.join(output_dir, "ansible"))
        self.shell = ShellGenerator(os.path.join(output_dir, "shell"))

    def generate_all(self, plan: DeploymentPlan) -> Dict:
        """生成全部IaC产物"""
        return {
            "terraform": self.terraform.generate(plan),
            "ansible": self.ansible.generate(plan),
            "shell": self.shell.generate(plan),
        }
