"""图像算子组 - 4算子：关键帧生成、风格迁移、图像增强、批量生成"""
import requests, time

class ImageOperators:
    def __init__(self, config):
        self.config = config
        self.ai_proxy = config.get("ai_proxy_url", "http://127.0.0.1:8021")
    
    def generate_keyframe(self, prompt, ratio="9:16", timeout=180, max_retries=2):
        """算子I1：关键帧生成（带指数退避重试）"""
        last_error = "未知错误"
        for attempt in range(max_retries + 1):
            try:
                r = requests.post(self.ai_proxy + "/image/generate", json={
                    "prompt": prompt, "ratio": ratio, "mode": "public"
                }, timeout=30)
                tid = r.json().get("task_id")
                if not tid:
                    last_error = "无task_id"
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    return {"success": False, "error": last_error, "operator": "I1_keyframe"}
                waited = 0
                while waited < timeout:
                    time.sleep(5)
                    waited += 5
                    try:
                        s = requests.get(self.ai_proxy + "/image/status?task_id=" + tid, timeout=10).json()
                        if s.get("status") == "completed":
                            return {"success": True, "image_url": s.get("image_url"), "operator": "I1_keyframe"}
                        if s.get("status") == "failed":
                            last_error = "生成失败"
                            break
                    except: pass
                if attempt < max_retries:
                    print("[算子I] 图像生成超时，第%d次重试" % (attempt+1))
                    time.sleep(2 ** attempt)
                    continue
                return {"success": False, "error": "超时", "operator": "I1_keyframe"}
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue
        return {"success": False, "error": last_error, "operator": "I1_keyframe"}
    
    def style_transfer(self, image_url, style="东方水墨"):
        """算子I2：风格迁移（预留）"""
        return {"success": True, "image_url": image_url, "style": style, "operator": "I2_style"}
    
    def enhance_image(self, image_url):
        """算子I3：图像增强（预留）"""
        return {"success": True, "image_url": image_url, "operator": "I3_enhance"}
    
    def batch_generate(self, prompts, ratio="9:16"):
        """算子I4：批量生成"""
        results = []
        for p in prompts:
            results.append(self.generate_keyframe(p, ratio))
        return {"success": True, "results": results, "operator": "I4_batch"}
