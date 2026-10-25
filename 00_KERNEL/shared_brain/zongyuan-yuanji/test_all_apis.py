#!/usr/bin/env python3
# ZONGYUAN-ROOT - 全量 API 测试脚本
# 用途：测试所有已配置 API 端点的可用性和延迟

import requests, time, os
from typing import Dict, List

class APITester:
    def __init__(self):
        self.results = []
        
    def test_endpoint(self, name: str, url: str, headers: Dict = None, 
                     data: Dict = None, timeout: int = 10) -> Dict:
        """测试单个 API 端点"""
        print(f"🔌 测试 {name}...", end=" ", flush=True)
        
        try:
            start = time.time()
            r = requests.post(url, json=data or {}, headers=headers, timeout=timeout)
            latency = (time.time() - start) * 1000
            
            result = {
                "name": name,
                "url": url,
                "status_code": r.status_code,
                "latency_ms": round(latency, 2),
                "success": r.status_code in [200, 401]  # 401 表示 API Key 错误但服务可达
            }
            
            if result["success"]:
                print(f"✅ HTTP {r.status_code} ({round(latency)}ms)")
            else:
                print(f"❌ HTTP {r.status_code}")
                
            return result
            
        except requests.exceptions.Timeout:
            print("⏰ TIMEOUT")
            return {"name": name, "url": url, "error": "timeout"}
            
        except requests.exceptions.ConnectionError:
            print("🚫 CONNECTION ERROR")
            return {"name": name, "url": url, "error": "connection_error"}
            
        except Exception as e:
            print(f"❌ {str(e)[:50]}")
            return {"name": name, "url": url, "error": str(e)[:100]}
    
    def run_all_tests(self):
        """运行全部 API 测试"""
        print("\n" + "="*60)
        print("🧪 ZONGYUAN-ROOT 全量 API 测试")
        print("="*60 + "\n")
        
        # ===== 已知的 API 端点（根据您实际配置）=====
        apis = [
            # 智谱 (BigModel) - 已授权
            ("Zhipu GLM-4.7-Flash", "https://open.bigmodel.cn/api/paas/v4/chat/completions", {
                "Authorization": "Bearer 1dfa...quIk",
                "Content-Type": "application/json"
            }, {
                "model": "GLM-4.7-Flash",
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 10
            }),
            
            # ModelScope - 已授权
            ("ModelScope Qwen", "https://api-inference.modelscope.cn/v1/chat/completions", {
                "Authorization": "Bearer ms-6...3ce7",
                "Content-Type": "application/json"
            }, {
                "model": "Qwen/Qwen3.5-122B-A10B",
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 10
            }),
            
            # SenseNova - 已授权
            ("SenseNova", "https://token.sensenova.cn/v1/responses", {
                "Authorization": "Bearer sk-w...aXmi",
                "Content-Type": "application/json"
            }, {
                "model": "sensenova-6.8-flash-lite",
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 10
            }),
            
            # SHUSHENG (Intern) - 已授权
            ("SHUSHENG intern-s2", "https://discovery-api.intern-ai.org.cn/v1/chat/completions", {
                "Authorization": "Bearer sk-e...f4c4",
                "Content-Type": "application/json"
            }, {
                "model": "intern-s2",
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 10
            }),
            
            # WorkBuddy 云同步
            ("WorkBuddy Cloud", "https://www.workbuddy.cn/space/home", None, None),
            
            # 记忆网关
            ("Memory Gateway DAL", "https://www.huodouai.com/dal/health", None, None),
            
            # 真值上报 API
            ("Truth Report API", "https://www.huodouai.com/api/report/truth", None, {
                "did": "DID-BR-000002",
                "test": True
            }),
        ]
        
        for api_config in apis:
            name = api_config[0]
            url = api_config[1]
            headers = api_config[2] if len(api_config) > 2 else None
            data = api_config[3] if len(api_config) > 3 else None
            
            result = self.test_endpoint(name, url, headers, data)
            self.results.append(result)
            
            time.sleep(0.5)  # 避免太快请求
        
        return self.results
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("📊 API 测试结果汇总")
        print("="*60 + "\n")
        
        total = len(self.results)
        success = sum(1 for r in self.results if r.get("success"))
        failed = total - success
        
        print(f"总计：{total} 个 API")
        print(f"✅ 成功：{success}")
        print(f"❌ 失败：{failed}\n")
        
        # 按性能排序
        successful = [r for r in self.results if r.get("success")]
        if successful:
            successful.sort(key=lambda x: x.get("latency_ms", float('inf')))
            
            print("🏆 性能排名 Top 5:")
            print("-"*60)
            for i, r in enumerate(successful[:5], 1):
                print(f"{i}. {r['name']:30s} {r['latency_ms']:.0f}ms")
        
        print("\n详细结果:")
        print("-"*60)
        for r in self.results:
            status = "✅" if r.get("success") else "❌"
            latency = f"{r['latency_ms']:.0f}ms" if r.get("latency_ms") else "N/A"
            code = f"HTTP {r['status_code']}" if r.get("status_code") else r.get("error", "Unknown")
            print(f"{status} {r['name']:30s} | {code:20s} | {latency}")


if __name__ == "__main__":
    tester = APITester()
    results = tester.run_all_tests()
    tester.generate_report()
    
    # 保存结果
    import json
    with open("/zongyuan-yuanji/logs/api_test_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 结果已保存到：/zongyuan-yuanji/logs/api_test_results.json")
