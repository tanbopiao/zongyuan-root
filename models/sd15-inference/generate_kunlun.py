#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑洞天 LoRA 推理流水线
训练完 → 生成图片 → 加水印 → 自动归档 → 上报中枢
"""
import argparse, os, json, time, hashlib, urllib.request
from pathlib import Path

# ============ 配置 ============
BASE_MODEL = "/home/user/Doubao/models/sd15"
ASSETS_ROOT = "/home/user/ZONGYUAN-ROOT/kunlun-assets"
GATEWAY = "https://www.huodouai.com/api/report/truth"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
NODE = "NODE-DEV-DOUBAO-WORK-001"

def generate(lora_path, prompt, output_name, steps=30, scale=7.5):
    """用LoRA生成一张图"""
    import torch
    from diffusers import StableDiffusionPipeline, EulerAncestralDiscreteScheduler
    
    today = time.strftime("%Y-%m-%d")
    out_dir = Path(ASSETS_ROOT) / today / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{output_name}.png"
    
    print(f"加载基础模型: {BASE_MODEL}")
    pipe = StableDiffusionPipeline.from_pretrained(
        BASE_MODEL, torch_dtype=torch.float16
    ).to("cuda")
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    
    print(f"加载LoRA: {lora_path}")
    pipe.load_lora_weights(lora_path)
    
    print(f"生成: {prompt[:60]}...")
    image = pipe(
        prompt,
        num_inference_steps=steps,
        guidance_scale=scale,
        height=768, width=512
    ).images[0]
    
    # 加水印
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(image)
    draw.text((image.width - 200, image.height - 30), ANCHOR, fill=(255,255,255,128))
    
    image.save(str(out_path))
    print(f"✅ 保存: {out_path}")
    return str(out_path)

def auto_archive(image_path, role, prompt):
    """自动归档：SHA256+manifest+上报中枢"""
    p = Path(image_path)
    data = p.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    
    today = time.strftime("%Y-%m-%d")
    manifest_dir = Path(ASSETS_ROOT) / today
    manifest_file = manifest_dir / "manifest.json"
    
    # 读或建manifest
    if manifest_file.exists():
        manifest = json.load(open(manifest_file))
    else:
        manifest = {"date": today, "items": []}
    
    entry = {
        "file": p.name,
        "role": role,
        "prompt": prompt,
        "sha256": sha,
        "size_bytes": len(data),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "anchor": ANCHOR,
        "did": DID
    }
    manifest["items"].append(entry)
    json.dump(manifest, open(manifest_file, "w"), ensure_ascii=False, indent=2)
    
    # 上报中枢
    truth_key = f"ZONGYUAN.KUNLUN.GENERATED.{today.replace('-','').upper()}"
    truth_value = f"角色={role} | 文件={p.name} | sha256={sha[:16]}... | prompt={prompt[:50]} | {ANCHOR}"
    
    body = json.dumps({
        "truth_key": truth_key,
        "truth_value": truth_value,
        "source_node": NODE,
        "confidence": 1.0,
        "truth_type": "creative"
    }).encode()
    
    try:
        req = urllib.request.Request(GATEWAY, data=body, headers={"Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        print(f"✅ 中枢已上报: {result.get('truth_count')}条")
    except Exception as e:
        print(f"⚠️ 中枢上报失败: {e}")
    
    return sha

def main():
    parser = argparse.ArgumentParser(description="昆仑洞天LoRA推理流水线")
    parser.add_argument("--lora", required=True, help="LoRA权重路径")
    parser.add_argument("--prompt", required=True, help="生成提示词")
    parser.add_argument("--role", required=True, help="角色名")
    parser.add_argument("--name", required=True, help="输出文件名")
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--scale", type=float, default=7.5)
    args = parser.parse_args()
    
    print("=" * 60)
    print("  昆仑洞天 LoRA 推理流水线")
    print("=" * 60)
    
    # 1. 生成
    img_path = generate(args.lora, args.prompt, args.name, args.steps, args.scale)
    
    # 2. 归档
    print("\n--- 自动归档 ---")
    sha = auto_archive(img_path, args.role, args.prompt)
    print(f"  SHA256: {sha[:32]}...")
    
    print("\n" + "=" * 60)
    print("  ✅ 流水线完成")
    print(f"  图片: {img_path}")
    print(f"  角色: {args.role}")
    print(f"  锚定: {ANCHOR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
