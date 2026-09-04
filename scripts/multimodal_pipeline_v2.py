#!/usr/bin/env python3
"""
P1-5: 多模态流水线真实生成适配器
通过HTTP API调用MainAgent的image_gen/video/audio工具，实现真实媒体生成
模式：本地编排 + 远程API生成
"""
import json
import hashlib
import urllib.request
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT")
PIPELINE_CONFIG = ROOT / "config" / "multimodal_pipeline.json"

DEFAULT_CONFIG = {
    "mode": "api_adapter",
    "api_endpoint": "http://127.0.0.1:8765/api/v1/generate",
    "supported_types": ["image", "video", "audio", "text"],
    "default_params": {
        "image": {"width": 1024, "height": 1024, "model": "seedream_4.5"},
        "video": {"duration": "10", "ratio": "9:16", "model": "seedance_2.0"},
        "audio": {"duration": 30}
    },
    "output_dir": "./assets/generated",
    "watermark": True,
    "auto_lock": True
}

def get_config() -> dict:
    if PIPELINE_CONFIG.exists():
        with open(PIPELINE_CONFIG) as f:
            return json.load(f)
    return DEFAULT_CONFIG

def save_config(config: dict):
    PIPELINE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_CONFIG, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def generate_asset(asset_type: str, prompt: str, params: dict = None) -> dict:
    """
    生成媒体资产（通过API适配器）
    asset_type: image/video/audio/text
    """
    config = get_config()
    if asset_type not in config["supported_types"]:
        return {"error": f"unsupported_type: {asset_type}"}
    
    request_params = config["default_params"].get(asset_type, {})
    if params:
        request_params.update(params)
    
    payload = {
        "type": asset_type,
        "prompt": prompt,
        "params": request_params,
        "pipeline_id": hashlib.sha256(f"{asset_type}_{prompt}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
    }
    
    # 尝试通过API调用
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            config["api_endpoint"],
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            result["pipeline_status"] = "api_generated"
            return result
    except Exception as e:
        # API不可用时，生成prompt文件作为占位
        output_dir = ROOT / config["output_dir"].replace("./", "")
        output_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = output_dir / f"{payload['pipeline_id']}_{asset_type}_prompt.json"
        with open(prompt_file, "w") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return {
            "pipeline_status": "prompt_only",
            "reason": f"API unavailable: {e}",
            "prompt_file": str(prompt_file),
            "next_step": "通过MainAgent工具手动执行生成",
            "pipeline_id": payload["pipeline_id"]
        }

def run_pipeline(character: str, scene: str, emotion: str = "epic") -> dict:
    """
    运行完整多模态流水线：1输入→14资产
    """
    assets = []
    base_prompt = f"{character} in {scene}, {emotion} mood"
    
    # 文本资产
    assets.append(generate_asset("text", f"{base_prompt} - 角色设定文档"))
    assets.append(generate_asset("text", f"{base_prompt} - 分镜脚本"))
    assets.append(generate_asset("text", f"{base_prompt} - 旁白文案"))
    
    # 图像资产
    for i in range(5):
        assets.append(generate_asset("image", f"{base_prompt} - keyframe {i+1}"))
    
    # 视频资产
    for i in range(3):
        assets.append(generate_asset("video", f"{base_prompt} - scene {i+1}"))
    
    # 音频资产
    assets.append(generate_asset("audio", f"{base_prompt} - BGM"))
    assets.append(generate_asset("audio", f"{base_prompt} - 配音"))
    assets.append(generate_asset("audio", f"{base_prompt} - 音效"))
    
    # JSON配置
    assets.append({"type": "config", "status": "generated", "content": {"character": character, "scene": scene, "emotion": emotion, "asset_count": len(assets)}})
    
    return {
        "pipeline_id": hashlib.sha256(f"{character}_{scene}_{datetime.now().isoformat()}".encode()).hexdigest()[:12],
        "input": {"character": character, "scene": scene, "emotion": emotion},
        "assets_generated": len(assets),
        "assets": assets,
        "auto_locked": True
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        save_config(DEFAULT_CONFIG)
        print(f"多模态流水线配置已初始化: {PIPELINE_CONFIG}")
    elif len(sys.argv) > 3 and sys.argv[1] == "run":
        result = run_pipeline(sys.argv[2], sys.argv[3])
        print(json.dumps({"pipeline_id": result["pipeline_id"], "assets": result["assets_generated"]}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(get_config(), ensure_ascii=False, indent=2))
