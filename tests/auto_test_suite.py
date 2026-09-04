#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT云内核 自动化测试体系 P1-3
测试所有API接口和服务健康状态
"""

import subprocess
import json
import time
from datetime import datetime

class ServiceTester:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def run_curl(self, url, method="GET", timeout=5, data=None):
        """执行curl请求"""
        try:
            cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", str(timeout), "-X", method]
            if data:
                cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(data)])
            cmd.append(url)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+2)
            return int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        except:
            return 0
    
    def test_service(self, name, url, expected_code=200, description=""):
        """测试单个服务"""
        start_time = time.time()
        status_code = self.run_curl(url)
        response_time = round((time.time() - start_time) * 1000)
        
        if status_code == expected_code:
            result = "PASS"
            self.passed += 1
            icon = "✅"
        elif status_code == 0:
            result = "FAIL"
            self.failed += 1
            icon = "❌"
        else:
            result = "WARN"
            self.warnings += 1
            icon = "⚠️"
        
        self.results.append({
            "name": name,
            "url": url,
            "expected": expected_code,
            "actual": status_code,
            "response_time": response_time,
            "result": result,
            "description": description
        })
        
        print(f"  {icon} {name}: HTTP {status_code} ({response_time}ms) - {description}")
        return result == "PASS"
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 70)
        print("ZONGYUAN-ROOT云内核 自动化测试 P1-3")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # 1. 基础服务健康检查
        print("\n【1. 基础服务健康检查】")
        self.test_service("Nginx HTTP", "http://127.0.0.1/", 200, "Web服务器")
        self.test_service("Nginx HTTPS", "https://127.0.0.1/", 200, "HTTPS服务")
        self.test_service("AIOS健康检查", "http://127.0.0.1:8765/health", 200, "AI智能体工作台")
        self.test_service("Ω-Brainμ健康检查", "http://127.0.0.1:8000/health", 200, "内核健康检查")
        self.test_service("LOIP API", "http://127.0.0.1:8001/api/v1/status", 200, "逻辑本体智能协议")
        self.test_service("Anchor同步API", "http://127.0.0.1:8006/api/v1/sync/handshake", 200, "双内核同步")
        self.test_service("政务中台", "http://127.0.0.1:8010/health", 200, "政务AI中台")
        
        # 2. AIOS API端点测试
        print("\n【2. AIOS API端点测试】")
        self.test_service("AIOS模型列表", "http://127.0.0.1:8765/api/v1/models", 200, "大模型列表")
        self.test_service("AIOS智能体列表", "http://127.0.0.1:8765/api/v1/agents", 200, "智能体列表")
        self.test_service("AIOS工作流列表", "http://127.0.0.1:8765/api/v1/agents/workflows", 200, "工作流列表")
        self.test_service("AIOS知识库统计", "http://127.0.0.1:8765/api/v1/knowledge/stats", 200, "知识库统计")
        
        # 3. 外部域名访问测试
        print("\n【3. 外部域名访问测试】")
        self.test_service("官网首页", "https://www.huodouai.com/", 200, "产品展示页")
        self.test_service("技术页", "https://huodouai.com/", 200, "技术展示页")
        self.test_service("AI工作台", "https://www.huodouai.com/workbench/", 200, "AI智能体工作台")
        self.test_service("政务中台", "https://www.huodouai.com/gov/", 200, "政务AI中台")
        self.test_service("API代理", "https://www.huodouai.com/workbench-api/v1/models", 200, "API反向代理")
        self.test_service("健康检查代理", "https://www.huodouai.com/workbench-health", 200, "健康检查代理")
        
        # 4. 端口监听测试
        print("\n【4. 端口监听测试】")
        ports_to_check = [
            (22, "SSH"),
            (80, "HTTP"),
            (443, "HTTPS"),
            (8765, "AIOS"),
            (8000, "Ω-Brainμ"),
            (8001, "LOIP"),
            (8006, "Anchor"),
            (8010, "政务中台"),
            (7100, "FRP服务端"),
            (8888, "宝塔面板"),
            (3306, "MySQL(本地)"),
            (6379, "Redis(本地)"),
        ]
        
        for port, name in ports_to_check:
            result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
            is_listening = f":{port}" in result.stdout
            if is_listening:
                self.passed += 1
                print(f"  ✅ {name} (端口{port}): 监听中")
            else:
                self.failed += 1
                print(f"  ❌ {name} (端口{port}): 未监听")
            
            self.results.append({
                "name": f"{name}端口",
                "url": f"port:{port}",
                "expected": "LISTEN",
                "actual": "LISTEN" if is_listening else "CLOSED",
                "response_time": 0,
                "result": "PASS" if is_listening else "FAIL",
                "description": name
            })
        
        # 5. 系统资源检查
        print("\n【5. 系统资源检查】")
        # CPU
        result = subprocess.run(["top", "-bn1"], capture_output=True, text=True)
        cpu_usage = 0
        for line in result.stdout.split("\n"):
            if "%Cpu" in line:
                parts = line.replace(",", " ").split()
                for i, part in enumerate(parts):
                    if "id" in part.lower():
                        cpu_usage = round(100 - float(parts[i-1].replace("%", "")), 1)
                        break
        
        cpu_status = "PASS" if cpu_usage < 80 else "WARN"
        if cpu_status == "PASS":
            self.passed += 1
            print(f"  ✅ CPU使用率: {cpu_usage}% (正常)")
        else:
            self.warnings += 1
            print(f"  ⚠️ CPU使用率: {cpu_usage}% (偏高)")
        
        # 内存
        result = subprocess.run(["free", "-m"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        mem_total = 0
        mem_available = 0
        if len(lines) >= 2:
            parts = lines[1].split()
            mem_total = int(parts[1])
            mem_available = int(parts[6]) if len(parts) > 6 else int(parts[3])
        
        mem_usage = round((1 - mem_available/mem_total) * 100, 1) if mem_total > 0 else 0
        mem_status = "PASS" if mem_usage < 90 else "WARN"
        if mem_status == "PASS":
            self.passed += 1
            print(f"  ✅ 内存使用率: {mem_usage}% ({mem_available}MB可用, 正常)")
        else:
            self.warnings += 1
            print(f"  ⚠️ 内存使用率: {mem_usage}% ({mem_available}MB可用, 偏高)")
        
        # 磁盘
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        disk_usage = 0
        if len(lines) >= 2:
            parts = lines[1].split()
            disk_usage = int(parts[4].replace("%", ""))
        
        disk_status = "PASS" if disk_usage < 85 else "WARN"
        if disk_status == "PASS":
            self.passed += 1
            print(f"  ✅ 磁盘使用率: {disk_usage}% (正常)")
        else:
            self.warnings += 1
            print(f"  ⚠️ 磁盘使用率: {disk_usage}% (偏高)")
        
        # 汇总
        print("\n" + "=" * 70)
        total = self.passed + self.failed + self.warnings
        print(f"测试汇总: {total}项测试 | ✅通过: {self.passed} | ❌失败: {self.failed} | ⚠️警告: {self.warnings}")
        print(f"通过率: {round(self.passed/total*100, 1)}%" if total > 0 else "无测试")
        
        if self.failed == 0:
            print("✅ 所有关键服务正常运行！")
        else:
            print("❌ 存在失败项，请检查！")
            print("\n失败项详情:")
            for r in self.results:
                if r["result"] == "FAIL":
                    print(f"  - {r['name']}: {r['url']} (期望{r['expected']}, 实际{r['actual']})")
        
        print("=" * 70)
        
        # 保存测试报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings,
                "pass_rate": round(self.passed/total*100, 1) if total > 0 else 0
            },
            "results": self.results
        }
        
        report_path = "/opt/ZONGYUAN-ROOT/tests/test_report_latest.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n测试报告已保存: {report_path}")
        
        return self.failed == 0

if __name__ == "__main__":
    tester = ServiceTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
