"""验证算子组 - 3算子：文件完整性、视频可播放、漂移检测"""
import os, hashlib, sqlite3, time

class VerificationOperators:
    def __init__(self, config):
        self.config = config
    
    def check_file_integrity(self, file_path, min_size=1000):
        """算子V1：文件完整性校验"""
        if not os.path.exists(file_path):
            return {"success": False, "error": "文件不存在", "operator": "VF1_integrity"}
        size = os.path.getsize(file_path)
        if size < min_size:
            return {"success": False, "error": f"文件过小({size}字节)，疑似0字节", "operator": "VF1_integrity"}
        with open(file_path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        return {"success": True, "size": size, "sha256": h[:16], "operator": "VF1_integrity"}
    
    def check_video_playable(self, video_url):
        """算子V2：视频可播放校验（检查URL非空+文件存在）"""
        if not video_url:
            return {"success": False, "error": "视频URL为空", "operator": "VF2_playable"}
        # 本地文件检查
        if video_url.startswith("/"):
            full_path = "/www/wwwroot/huodouai.com" + video_url
            if os.path.exists(full_path):
                size = os.path.getsize(full_path)
                return {"success": size > 1000, "size": size, "operator": "VF2_playable"}
            return {"success": False, "error": "本地文件不存在", "operator": "VF2_playable"}
        return {"success": True, "url": video_url[:50], "operator": "VF2_playable"}
    
    def drift_detection(self, current_hash, expected_hash):
        """算子V3：漂移检测"""
        drifted = current_hash != expected_hash
        return {
            "success": True, "drifted": drifted,
            "current": current_hash[:16], "expected": expected_hash[:16],
            "operator": "VF3_drift"
        }
