"""文本算子组 - 4算子：剧本生成、分镜设计、旁白提炼、文案优化"""
import requests, time

class TextOperators:
    def __init__(self, config):
        self.config = config
        self.ai_proxy = config.get("ai_proxy_url", "http://127.0.0.1:8021")
    
    def generate_script(self, template_name, style="纯东方神女", timeout=90):
        """算子T1：剧本生成"""
        try:
            r = requests.post(f"{self.ai_proxy}/chat", json={
                "message": f"生成{template_name}短剧剧本，3分镜，{style}风格，含旁白金句",
                "node_type": "script", "model": "auto", "max_tokens": 500
            }, timeout=timeout)
            return {"success": True, "script": r.json().get("result", ""), "operator": "T1_script"}
        except Exception as e:
            return {"success": False, "error": str(e), "operator": "T1_script"}
    
    def generate_storyboard(self, script, timeout=90):
        """算子T2：分镜设计"""
        try:
            r = requests.post(f"{self.ai_proxy}/chat", json={
                "message": f"基于剧本生成分镜表：{script[:300]}",
                "node_type": "storyboard", "model": "auto", "max_tokens": 500
            }, timeout=timeout)
            return {"success": True, "storyboard": r.json().get("result", ""), "operator": "T2_storyboard"}
        except Exception as e:
            return {"success": False, "error": str(e), "operator": "T2_storyboard"}
    
    def extract_narration(self, script, max_len=200):
        """算子T3：旁白提炼"""
        text = script.replace("#","").replace("*","").replace("\n","")
        return {"success": True, "narration": text[:max_len], "operator": "T3_narration"}
    
    def optimize_prompt(self, prompt, style="电影级"):
        """算子T4：提示词优化"""
        optimized = f"{prompt}，{style}画质，9:16竖屏，纯东方神女，零雄性化，零西方铠甲"
        return {"success": True, "optimized_prompt": optimized, "operator": "T4_prompt"}
