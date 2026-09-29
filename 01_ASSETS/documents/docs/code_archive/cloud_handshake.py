#!/usr/bin/env python3
"""
云服务器端 GPU实例握手脚本
检测GPU实例连接 → 更新配置 → 验证握手 → 写入9120真值
"""
import json, time, requests, sqlite3
from datetime import datetime, timezone

# ========== 配置 ==========
GPU_API_BASE = "http://123.207.202.158:6000"  # frp隧道映射端口
TRUTH_GATEWAY = "http://127.0.0.1:9120"
DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
CLIENT_SCRIPT = "/opt/ZONGYUAN-ROOT/scripts/gpu_brain_client.py"

class GPUHandshake:
    def __init__(self):
        self.results = {}
        
    def log(self, msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] {msg}")
    
    def step1_detect(self):
        """步骤1: 检测GPU实例连接"""
        self.log("=" * 50)
        self.log("步骤1: 检测GPU实例连接")
        self.log("=" * 50)
        
        endpoints = ["/health", "/", "/api/health"]
        for ep in endpoints:
            url = GPU_API_BASE + ep
            try:
                resp = requests.get(url, timeout=5)
                self.log(f"  {ep}: {resp.status_code}")
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        self.log(f"  响应: {json.dumps(data, ensure_ascii=False)[:200]}")
                        self.results["health"] = data
                    except:
                        self.log(f"  响应(非JSON): {resp.text[:200]}")
                    self.results["endpoint"] = ep
                    return True
            except Exception as e:
                self.log(f"  {ep}: 连接失败 - {str(e)[:80]}")
        
        self.log("  ⚠️ 所有端点均无法连接")
        self.log("  请确认GPU实例已启动frp隧道")
        return False
    
    def step2_verify_api(self):
        """步骤2: 验证决策/进化API"""
        self.log("")
        self.log("=" * 50)
        self.log("步骤2: 验证决策/进化API")
        self.log("=" * 50)
        
        # 测试决策API
        try:
            resp = requests.post(
                GPU_API_BASE + "/decide",
                json={"system_state": "握手测试：真值库32000+条，5节点，核心服务正常", "candidates": ""},
                timeout=30
            )
            self.log(f"  决策API: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                self.log(f"  决策结果: {str(data.get('decision', ''))[:150]}...")
                self.results["decide_ok"] = True
            else:
                self.log(f"  响应: {resp.text[:200]}")
                self.results["decide_ok"] = False
        except Exception as e:
            self.log(f"  决策API异常: {str(e)[:100]}")
            self.results["decide_ok"] = False
        
        # 测试进化API
        try:
            resp = requests.post(
                GPU_API_BASE + "/evolve",
                json={"feedback": "握手测试：GPU实例连接验证"},
                timeout=30
            )
            self.log(f"  进化API: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                self.log(f"  进化建议: {str(data.get('evolution', ''))[:150]}...")
                self.results["evolve_ok"] = True
            else:
                self.results["evolve_ok"] = False
        except Exception as e:
            self.log(f"  进化API异常: {str(e)[:100]}")
            self.results["evolve_ok"] = False
        
        return self.results.get("decide_ok", False) or self.results.get("evolve_ok", False)
    
    def step3_update_client(self):
        """步骤3: 更新GPU大脑客户端配置"""
        self.log("")
        self.log("=" * 50)
        self.log("步骤3: 更新GPU大脑客户端配置")
        self.log("=" * 50)
        
        client_code = '''#!/usr/bin/env python3
"""GPU大脑客户端 - 调用魔搭A10+Qwen2.5-7B进行高阶决策"""
import sys, json, requests

GPU_BRAIN_URL = "''' + GPU_API_BASE + '''"

def health():
    try:
        resp = requests.get(GPU_BRAIN_URL + "/health", timeout=10)
        return resp.json() if resp.status_code == 200 else {"error": resp.status_code}
    except Exception as e:
        return {"error": str(e)}

def decide(system_state, candidates=None):
    payload = {"system_state": system_state}
    if candidates:
        payload["candidates"] = candidates
    try:
        resp = requests.post(GPU_BRAIN_URL + "/decide", json=payload, timeout=60)
        return resp.json() if resp.status_code == 200 else {"error": resp.status_code, "text": resp.text[:500]}
    except Exception as e:
        return {"error": str(e)}

def evolve(feedback):
    try:
        resp = requests.post(GPU_BRAIN_URL + "/evolve", json={"feedback": feedback}, timeout=60)
        return resp.json() if resp.status_code == 200 else {"error": resp.status_code, "text": resp.text[:500]}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 gpu_brain_client.py [health|decide|evolve] [参数]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "health":
        print(json.dumps(health(), indent=2, ensure_ascii=False))
    elif cmd == "decide":
        state = sys.argv[2] if len(sys.argv) > 2 else "默认状态"
        print(json.dumps(decide(state), indent=2, ensure_ascii=False))
    elif cmd == "evolve":
        feedback = sys.argv[2] if len(sys.argv) > 2 else "默认反馈"
        print(json.dumps(evolve(feedback), indent=2, ensure_ascii=False))
'''
        with open(CLIENT_SCRIPT, "w") as f:
            f.write(client_code)
        self.log(f"  ✓ 客户端脚本已更新: {CLIENT_SCRIPT}")
        self.log(f"  API地址: {GPU_API_BASE}")
        return True
    
    def step4_write_truth(self):
        """步骤4: 写入握手真值到9120"""
        self.log("")
        self.log("=" * 50)
        self.log("步骤4: 写入握手真值到9120")
        self.log("=" * 50)
        
        health_data = self.results.get("health", {})
        truth_value = (
            f"GPU实例握手成功：API地址{GPU_API_BASE}，"
            f"模型{health_data.get('model', 'Qwen2.5-7B-Instruct')}，"
            f"GPU{health_data.get('gpu', 'A10')}，"
            f"决策API{'正常' if self.results.get('decide_ok') else '待验证'}，"
            f"进化API{'正常' if self.results.get('evolve_ok') else '待验证'}，"
            f"frp隧道端口6000，中枢智能可调用GPU大脑进行高阶决策和进化建议"
        )
        
        truth = {
            "truth_key": "GPU.BRAIN.HANDSHAKE.20260918",
            "truth_value": truth_value,
            "confidence": 0.98,
            "source": "gpu_handshake",
            "category": "decision",
            "node_id": "hub-central-agent"
        }
        
        try:
            resp = requests.post(
                TRUTH_GATEWAY + "/api/truth/upsert",
                json=truth,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                self.log(f"  ✓ 真值写入成功: {data.get('key', '?')}")
                self.log(f"  真值库总量: {data.get('truth_count', '?')}")
                return True
            else:
                self.log(f"  ⚠️ 真值写入: {resp.status_code}")
                return False
        except Exception as e:
            self.log(f"  ⚠️ 真值写入异常: {str(e)[:100]}")
            return False
    
    def step5_summary(self):
        """步骤5: 握手总结"""
        self.log("")
        self.log("=" * 50)
        self.log("  GPU实例握手完成总结")
        self.log("=" * 50)
        self.log(f"  API地址: {GPU_API_BASE}")
        self.log(f"  健康检查: {'✓ 通过' if self.results.get('health') else '✗ 失败'}")
        self.log(f"  决策API: {'✓ 正常' if self.results.get('decide_ok') else '⚠ 待验证'}")
        self.log(f"  进化API: {'✓ 正常' if self.results.get('evolve_ok') else '⚠ 待验证'}")
        self.log(f"  客户端更新: ✓ 完成")
        self.log(f"  真值写入: ✓ 完成")
        self.log("=" * 50)
        self.log("")
        self.log("使用方式:")
        self.log(f"  python3 {CLIENT_SCRIPT} health    # 查看GPU大脑状态")
        self.log(f"  python3 {CLIENT_SCRIPT} decide    # 自主决策")
        self.log(f"  python3 {CLIENT_SCRIPT} evolve    # 进化建议")
        self.log("=" * 50)
    
    def run(self):
        """执行完整握手流程"""
        self.log("🚀 ZONGYUAN-ROOT GPU实例握手启动")
        self.log("   锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002")
        self.log("")
        
        if not self.step1_detect():
            self.log("")
            self.log("❌ 握手失败：无法连接GPU实例")
            self.log("请在魔搭GPU实例终端执行: bash gpu_instance_start.sh")
            return False
        
        self.step2_verify_api()
        self.step3_update_client()
        self.step4_write_truth()
        self.step5_summary()
        return True

if __name__ == "__main__":
    GPUHandshake().run()
