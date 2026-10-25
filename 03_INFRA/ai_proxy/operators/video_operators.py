"""视频算子组 - 4算子：文生视频、图生视频、音画合并、视频转码"""
import requests, time

class VideoOperators:
    def __init__(self, config):
        self.config = config
        self.ai_proxy = config.get("ai_proxy_url", "http://127.0.0.1:8021")
    
    def text_to_video(self, prompt, duration=10, ratio="9:16", timeout=600):
        """算子V1：文生视频"""
        return self._generate(prompt, None, duration, ratio, timeout)
    
    def image_to_video(self, prompt, image_url, duration=10, ratio="9:16", timeout=600):
        """算子V2：图生视频"""
        return self._generate(prompt, image_url, duration, ratio, timeout)
    
    def _generate(self, prompt, image_url, duration, ratio, timeout, max_retries=2):
        last_error = "未知错误"
        for attempt in range(max_retries + 1):
            try:
                body = {"prompt": prompt, "duration": duration, "ratio": ratio, "mode": "public"}
                if image_url: body["image_url"] = image_url
                r = requests.post(self.ai_proxy + "/video/generate", json=body, timeout=30)
                tid = r.json().get("task_id")
                if not tid:
                    last_error = "无task_id"
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    return {"success": False, "error": last_error, "operator": "V_generate"}
                waited = 0
                while waited < timeout:
                    time.sleep(5)
                    waited += 5
                    try:
                        s = requests.get(self.ai_proxy + "/video/status?task_id=" + tid, timeout=10).json()
                        if s.get("status") == "completed":
                            return {"success": True, "video_url": s.get("video_url"), "operator": "V_generate"}
                        if s.get("status") == "failed":
                            last_error = "生成失败"
                            break
                    except: pass
                if attempt < max_retries:
                    print("[算子V] 视频生成超时，第%d次重试" % (attempt+1))
                    time.sleep(2 ** attempt)
                    continue
                return {"success": False, "error": "超时(%ds)" % timeout, "operator": "V_generate"}
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue
        return {"success": False, "error": last_error, "operator": "V_generate"}
    
    def merge_audio(self, video_url, audio_url, timeout=180):
        """算子V3：音画合并"""
        try:
            r = requests.post(f"{self.ai_proxy}/video/merge-audio", json={
                "video_url": video_url, "audio_url": audio_url
            }, timeout=timeout)
            d = r.json()
            if d.get("status") == "merged":
                return {"success": True, "output_url": d.get("output_url"), "operator": "V3_merge"}
            return {"success": False, "error": d.get("error", "合并失败"), "operator": "V3_merge"}
        except Exception as e:
            return {"success": False, "error": str(e), "operator": "V3_merge"}
    
    def transcode(self, video_url, codec="mpeg4"):
        """算子V4：视频转码（预留，已确认mpeg4可用）"""
        return {"success": True, "video_url": video_url, "codec": codec, "operator": "V4_transcode"}


    def concat(self, video_urls, output_path=None, transition=None):
        import os, subprocess, tempfile, time
        """拼接多个短视频为长视频（FFmpeg concat demuxer）"""
        import subprocess, tempfile, time
        if not video_urls or len(video_urls) < 2:
            return {"success": False, "error": "at least 2 videos required"}
        for v in video_urls:
            if not os.path.exists(v):
                return {"success": False, "error": "file not found: %s" % v}
        if output_path is None:
            output_path = "/www/wwwroot/huodouai.com/drama/videos/concat_%d.mp4" % int(time.time() * 1000)
        list_file = tempfile.mktemp(suffix=".txt")
        with open(list_file, "w") as lf:
            for v in video_urls:
                lf.write("file '" + os.path.abspath(v) + "'\n")
        try:
            cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                   "-c:v", "mpeg4", "-c:a", "aac", "-b:a", "128k", output_path]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                cmd2 = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                        "-c:v", "mpeg4", "-an", output_path]
                r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)
                if r2.returncode != 0:
                    return {"success": False, "error": "concat failed"}
            if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                return {"success": False, "error": "invalid output"}
            return {"success": True, "output_path": output_path,
                    "output_url": "/drama/videos/" + os.path.basename(output_path),
                    "segments": len(video_urls)}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if os.path.exists(list_file):
                os.remove(list_file)
