"""
视频拼接算子 - 将多个短视频拼接为一个长视频
基于FFmpeg concat demuxer
"""
import os
import subprocess
import tempfile
import time

def concat_videos(video_urls, output_path=None, transition=None):
    """
    拼接多个视频文件
    
    Args:
        video_urls: 视频文件路径列表（本地路径）
        output_path: 输出路径，None则自动生成
        transition: 转场效果（预留，当前仅硬切）
    
    Returns:
        dict: {success, output_path, duration, error}
    """
    start = time.time()
    
    # 验证输入
    if not video_urls or len(video_urls) < 2:
        return {"success": False, "error": "至少需要2个视频文件"}
    
    # 检查所有文件存在
    for v in video_urls:
        if not os.path.exists(v):
            return {"success": False, "error": "文件不存在: %s" % v}
    
    # 生成输出路径
    if output_path is None:
        output_dir = "/www/wwwroot/huodouai.com/drama/videos"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "concat_%s.mp4" % int(time.time() * 1000))
    
    # 创建concat列表文件
    list_file = tempfile.mktemp(suffix=".txt")
    with open(list_file, "w") as f:
        for v in video_urls:
            abs_path = os.path.abspath(v)
            f.write("file '%s'\n" % abs_path)
    
    try:
        # FFmpeg concat demuxer（重新编码以确保兼容性）
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c:v", "mpeg4",
            "-c:a", "aac",
            "-b:a", "128k",
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            # 尝试无音频拼接（部分视频可能无音频）
            cmd2 = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c:v", "mpeg4",
                "-an",
                output_path
            ]
            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)
            if result2.returncode != 0:
                return {"success": False, "error": "FFmpeg拼接失败: %s" % result2.stderr[-200:]}
        
        # 验证输出
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
            return {"success": False, "error": "输出文件无效"}
        
        # 获取时长
        duration = 0
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", output_path],
                capture_output=True, text=True, timeout=10
            )
            duration = float(probe.stdout.strip())
        except:
            pass
        
        elapsed = time.time() - start
        return {
            "success": True,
            "output_path": output_path,
            "output_url": "/drama/videos/" + os.path.basename(output_path),
            "duration": round(duration, 2),
            "segments": len(video_urls),
            "file_size": os.path.getsize(output_path),
            "elapsed": round(elapsed, 2)
        }
    
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "拼接超时"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)


# 算子注册接口
def register(registry):
    registry.register("video", "concat", concat_videos)
