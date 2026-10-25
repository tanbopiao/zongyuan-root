#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 应用标准化部署工具
功能：校验->哈希计算->部署->Nginx配置->注册->验收->报告
"""
import argparse
import json
import hashlib
import os
import shutil
import time
from datetime import datetime

class AppDeployer:
    def __init__(self, app_id, source_dir, developer, version):
        self.app_id = app_id
        self.source_dir = source_dir
        self.developer = developer
        self.version = version
        self.deploy_root = "/www/wwwroot/www.huodouai.com/apps"
        self.app_dir = os.path.join(self.deploy_root, app_id)
        self.registry_path = "/opt/ZONGYUAN-ROOT/app_governance/registry/app_registry.json"
        self.log_path = "/opt/ZONGYUAN-ROOT/app_governance/registry/deploy_log.jsonl"
        self.errors = []
        self.warnings = []
    
    def run(self):
        print("=" * 60)
        print("ZONGYUAN-ROOT 应用标准化部署工具")
        print("Omega_0 subset Circle_Infinity subset Omega | DID-BR-000002")
        print("=" * 60)
        print("应用ID: " + self.app_id)
        print("源目录: " + self.source_dir)
        print("开发窗口: " + self.developer)
        print("版本: " + self.version)
        print()
        
        print("[步骤1/8] 前置校验...")
        if not self._pre_check():
            print("FAIL: 前置校验失败，部署终止")
            return False
        print("PASS: 前置校验通过")
        
        print("[步骤2/8] 目录结构校验...")
        if not self._check_structure():
            print("FAIL: 目录结构校验失败，部署终止")
            return False
        print("PASS: 目录结构校验通过")
        
        print("[步骤3/8] manifest.json校验...")
        if not self._check_manifest():
            print("FAIL: manifest.json校验失败，部署终止")
            return False
        print("PASS: manifest.json校验通过")
        
        print("[步骤4/8] 敏感文件检查...")
        self._check_sensitive_files()
        print("PASS: 敏感文件检查完成")
        
        print("[步骤5/8] 计算内容哈希...")
        content_hash = self._calculate_hash()
        print("PASS: 内容哈希: " + content_hash[:24] + "...")
        
        print("[步骤6/8] 备份旧版本并部署...")
        if not self._deploy():
            print("FAIL: 部署失败")
            return False
        print("PASS: 部署完成")
        
        print("[步骤7/8] 更新manifest并生成Nginx配置...")
        self._update_manifest(content_hash)
        self._generate_nginx_config()
        print("PASS: manifest和Nginx配置已更新")
        
        print("[步骤8/8] 注册到应用注册表并验收...")
        self._register_app(content_hash)
        acceptance = self._run_acceptance()
        
        print()
        print("=" * 60)
        print("部署完成报告")
        print("=" * 60)
        print("应用ID: " + self.app_id)
        print("版本: " + self.version)
        print("部署路径: " + self.app_dir)
        print("访问地址: https://www.huodouai.com/apps/" + self.app_id + "/")
        print("内容哈希: " + content_hash)
        accept_result = "PASS" if acceptance["passed"] else "FAIL"
        print("验收结果: " + accept_result)
        if self.warnings:
            print("警告: " + str(len(self.warnings)) + "项")
            for w in self.warnings:
                print("  WARN: " + w)
        print("=" * 60)
        
        self._log_deploy(content_hash, acceptance)
        return acceptance["passed"]
    
    def _pre_check(self):
        if not os.path.isdir(self.source_dir):
            self.errors.append("源目录不存在: " + self.source_dir)
            return False
        if not os.path.isfile(os.path.join(self.source_dir, "index.html")):
            self.errors.append("源目录缺少index.html")
            return False
        if not os.path.isfile(os.path.join(self.source_dir, "manifest.json")):
            self.errors.append("源目录缺少manifest.json")
            return False
        return True
    
    def _check_structure(self):
        required_files = ["index.html", "manifest.json"]
        for f in required_files:
            if not os.path.isfile(os.path.join(self.source_dir, f)):
                self.errors.append("缺少必须文件: " + f)
                return False
        return True
    
    def _check_manifest(self):
        manifest_path = os.path.join(self.source_dir, "manifest.json")
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        except Exception as e:
            self.errors.append("manifest.json解析失败: " + str(e))
            return False
        
        required_fields = ["app_id", "app_name", "app_version", "entry_point", "did", "trace_mark"]
        for field in required_fields:
            if field not in manifest:
                self.errors.append("manifest.json缺少必填字段: " + field)
                return False
        
        if manifest["app_id"] != self.app_id:
            self.errors.append("manifest.json中的app_id与部署应用ID不一致")
            return False
        
        if manifest["did"] != "DID-BR-000002":
            self.errors.append("manifest.json中的did不正确")
            return False
        
        return True
    
    def _check_sensitive_files(self):
        sensitive_patterns = [".env", ".git", ".key", ".pem", ".log", ".tmp", "node_modules", "__pycache__"]
        for root, dirs, files in os.walk(self.source_dir):
            for pattern in sensitive_patterns:
                if pattern in dirs:
                    self.warnings.append("发现敏感目录: " + os.path.join(root, pattern))
                    dirs.remove(pattern)
                for f in files:
                    if pattern in f:
                        self.warnings.append("发现敏感文件: " + os.path.join(root, f))
    
    def _calculate_hash(self):
        hasher = hashlib.sha256()
        for root, dirs, files in os.walk(self.source_dir):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "__pycache__"]]
            for f in sorted(files):
                if f.endswith((".log", ".tmp", ".key", ".pem", ".env")):
                    continue
                filepath = os.path.join(root, f)
                rel_path = os.path.relpath(filepath, self.source_dir)
                hasher.update(rel_path.encode())
                try:
                    with open(filepath, "rb") as fp:
                        hasher.update(fp.read())
                except:
                    pass
        return hasher.hexdigest().upper()
    
    def _deploy(self):
        try:
            if os.path.isdir(self.app_dir):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = os.path.join(self.deploy_root, "archive", self.app_id + "_" + timestamp)
                os.makedirs(os.path.dirname(backup_dir), exist_ok=True)
                shutil.move(self.app_dir, backup_dir)
                print("  旧版本已备份: " + backup_dir)
            
            os.makedirs(self.app_dir, exist_ok=True)
            shutil.copytree(self.source_dir, self.app_dir, dirs_exist_ok=True,
                          ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__", "*.log", "*.tmp", ".env", "*.key", "*.pem"))
            return True
        except Exception as e:
            self.errors.append("部署失败: " + str(e))
            return False
    
    def _update_manifest(self, content_hash):
        manifest_path = os.path.join(self.app_dir, "manifest.json")
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        manifest["app_version"] = self.version
        manifest["updated_at"] = datetime.now().isoformat()
        manifest["hash"] = content_hash
        manifest["deployed_by"] = self.developer
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    def _generate_nginx_config(self):
        nginx_config = """
# ZONGYUAN-ROOT 应用: """ + self.app_id + """
# 自动生成于 """ + datetime.now().isoformat() + """
location /apps/""" + self.app_id + """/ {
    alias """ + self.app_dir + """/;
    index index.html;
    try_files $uri $uri/ /apps/""" + self.app_id + """/index.html;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    location ~* \\.(css|js|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
    location ~* \\.html$ {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}
"""
        config_path = "/opt/ZONGYUAN-ROOT/app_governance/templates/nginx_" + self.app_id + ".conf"
        with open(config_path, "w") as f:
            f.write(nginx_config)
        print("  Nginx配置已生成: " + config_path)
    
    def _register_app(self, content_hash):
        registry = self._load_registry()
        registry["apps"][self.app_id] = {
            "app_id": self.app_id,
            "app_name": self._get_app_name(),
            "current_version": self.version,
            "developer": self.developer,
            "entry_point": "/apps/" + self.app_id + "/",
            "deploy_path": self.app_dir,
            "content_hash": content_hash,
            "deployed_at": datetime.now().isoformat(),
            "status": "active",
            "violations": []
        }
        registry["last_updated"] = datetime.now().isoformat()
        registry["total_apps"] = len(registry["apps"])
        self._save_registry(registry)
    
    def _run_acceptance(self):
        checks = []
        
        index_path = os.path.join(self.app_dir, "index.html")
        checks.append({"name": "index.html存在", "passed": os.path.isfile(index_path)})
        
        manifest_path = os.path.join(self.app_dir, "manifest.json")
        manifest_ok = False
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path) as f:
                    m = json.load(f)
                manifest_ok = all(k in m for k in ["app_id", "app_name", "app_version", "did", "trace_mark", "hash"])
            except:
                pass
        checks.append({"name": "manifest.json完整", "passed": manifest_ok})
        
        sensitive_found = False
        for root, dirs, files in os.walk(self.app_dir):
            for f in files:
                if f.endswith((".env", ".key", ".pem")):
                    sensitive_found = True
            for d in dirs:
                if d in [".git", "node_modules"]:
                    sensitive_found = True
        checks.append({"name": "无敏感文件", "passed": not sensitive_found})
        
        did_ok = False
        if manifest_ok:
            with open(manifest_path) as f:
                m = json.load(f)
            did_ok = m.get("did") == "DID-BR-000002" and m.get("trace_mark") == "Omega_0 subset Circle_Infinity subset Omega"
        checks.append({"name": "确权标识正确", "passed": did_ok})
        
        passed = all(c["passed"] for c in checks)
        return {"passed": passed, "checks": checks}
    
    def _load_registry(self):
        if os.path.isfile(self.registry_path):
            with open(self.registry_path) as f:
                return json.load(f)
        return {"apps": {}, "total_apps": 0, "created_at": datetime.now().isoformat()}
    
    def _save_registry(self, registry):
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        with open(self.registry_path, "w") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    
    def _get_app_name(self):
        manifest_path = os.path.join(self.app_dir, "manifest.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path) as f:
                    return json.load(f).get("app_name", self.app_id)
            except:
                pass
        return self.app_id
    
    def _log_deploy(self, content_hash, acceptance):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "app_id": self.app_id,
            "version": self.version,
            "developer": self.developer,
            "content_hash": content_hash,
            "acceptance_passed": acceptance["passed"],
            "warnings": self.warnings,
            "errors": self.errors
        }
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def main():
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 应用标准化部署工具")
    parser.add_argument("--app-id", required=True, help="应用ID")
    parser.add_argument("--source-dir", required=True, help="源目录路径")
    parser.add_argument("--developer", required=True, help="开发窗口")
    parser.add_argument("--version", required=True, help="版本号")
    args = parser.parse_args()
    
    deployer = AppDeployer(args.app_id, args.source_dir, args.developer, args.version)
    success = deployer.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
