# GPU推理服务 - 模型常驻显存
from fastapi import FastAPI
from pydantic import BaseModel
import torch
from diffusers import StableDiffusionPipeline
import time
import uvicorn

app = FastAPI()

# 全局模型，启动时加载，常驻显存
pipe = None

class GenerateRequest(BaseModel):
    prompt: str
    steps: int = 20
    width: int = 432
    height: int = 768

@app.on_event("startup")
def load_model():
    global pipe
    print("加载Wan2.1模型到显存...")
    start = time.time()
    pipe = StableDiffusionPipeline.from_pretrained(
        "/mnt/workspace/models/models/models/Wan-AI--Wan2.1-T2V-14B-Diffusers/snapshots/master",
        torch_dtype=torch.float16
    ).to("cuda")
    print(f"✅ 模型加载完成，耗时{time.time()-start:.1f}秒，常驻显存中")

@app.get("/health")
def health():
    return {"status": "ok", "vram": torch.cuda.memory_allocated()/1024**3 if torch.cuda.is_available() else 0}

@app.post("/generate")
def generate(req: GenerateRequest):
    print(f"生成: {req.prompt[:30]}...")
    start = time.time()
    image = pipe(
        prompt=req.prompt,
        num_inference_steps=req.steps,
        width=req.width,
        height=req.height
    ).images[0]
    path = f"/mnt/workspace/output_{int(time.time())}.png"
    image.save(path)
    print(f"✅ 生成完成，耗时{time.time()-start:.1f}秒，保存到{path}")
    return {"path": path, "time": time.time()-start}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7888)
