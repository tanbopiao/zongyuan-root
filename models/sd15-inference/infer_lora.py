#!/usr/bin/env python3
# LoRA推理脚本 - 用训练好的LoRA生成昆仑洞天神女
# 用法: python infer_lora.py --lora_path ./lora_output/004_jiutian_xuannv

import argparse, torch
from diffusers import StableDiffusionPipeline, EulerAncestralDiscreteScheduler

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lora_path", required=True)
    parser.add_argument("--model_path", default="/home/user/Doubao/models/sd15")
    parser.add_argument("--prompt", default="kunlun dongtian style goddess, Chinese fantasy, cinematic, 9:16")
    parser.add_argument("--output", default="output.png")
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--scale", type=float, default=7.5)
    args = parser.parse_args()

    print(f"加载基础模型: {args.model_path}")
    pipe = StableDiffusionPipeline.from_pretrained(
        args.model_path, torch_dtype=torch.float16
    ).to("cuda")
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)

    print(f"加载LoRA: {args.lora_path}")
    pipe.load_lora_weights(args.lora_path)

    print(f"生成: {args.prompt}")
    image = pipe(
        args.prompt,
        num_inference_steps=args.steps,
        guidance_scale=args.scale,
        height=768, width=512
    ).images[0]
    image.save(args.output)
    print(f"✅ 保存: {args.output}")

if __name__ == "__main__":
    main()
