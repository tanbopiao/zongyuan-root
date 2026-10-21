#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FM-Core 边缘 Agent — OpenAI 兼容对话服务（默认端口 8000）。

启动顺序（严格）：先起内核 8100，再起本服务。
    python -m fm_core.api.http_server      # 终端1
    python -m fm_agent.edge_agent          # 终端2

链路：检索 FM-Core 记忆 → 按种子真值生成回答 → 事实抽取 →（内存水位内）回写提案。
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import diskcache as dc
import psutil
import requests
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from llama_cpp import Llama

ROOT = Path(__file__).resolve().parents[1]      # fm_project/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fm_adapters import (FaissFlatRetriever, LlamaCppExtractor,      # noqa: E402
                         LlamaCppGenAdapter, OnnxBgeAdapter)

PORT = int(os.environ.get("FM_AGENT_PORT", "8000"))
HOST = os.environ.get("FM_AGENT_HOST", "127.0.0.1")

app = FastAPI(title="FM-Core Edge Agent｜4G边缘对话节点", version="1.0.0")


def _p(rel: str) -> str:
    """把配置里的相对路径解析为绝对路径（相对 fm_project 根）。"""
    p = Path(rel)
    return str(p if p.is_absolute() else (ROOT / p))


with open(ROOT / "fm_agent" / "agent_config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

for key in ("gguf_path",):
    if not Path(_p(cfg["llm"][key])).exists():
        raise SystemExit(
            f"[fm_agent] 模型文件缺失: {_p(cfg['llm'][key])}\n"
            "           先执行 ./fetch_models.sh 下载模型资产。")
if not Path(_p(cfg["embedding"]["onnx_path"])).exists():
    raise SystemExit(
        f"[fm_agent] embedding 模型缺失: {_p(cfg['embedding']['onnx_path'])}\n"
        "           先执行 ./fetch_models.sh 下载模型资产。")

# ---------- 初始化缓存 & 适配器 ----------
cache = dc.Cache(_p(cfg["cache_dir"]))
llm = Llama(
    model_path=_p(cfg["llm"]["gguf_path"]),
    n_ctx=cfg["llm"]["n_ctx"],
    n_threads=cfg["llm"]["n_threads"],
    n_gpu_layers=cfg["llm"]["n_gpu_layers"],
    verbose=False,
)
emb_adapter = OnnxBgeAdapter(_p(cfg["embedding"]["onnx_path"]),
                             _p(cfg["embedding"]["vocab_path"]), cache)
FAISS_PATH = _p(cfg["faiss_path"])
retriever = FaissFlatRetriever(dim=emb_adapter.dim or 384)   # 维度由模型自描述，不硬编码
try:
    if not retriever.load(FAISS_PATH):
        print(f"[fm_agent] 无既有索引，空索引起步: {FAISS_PATH}")
except Exception as e:                      # 索引损坏/维度不符 → 重建（本地缓存可再生）
    retriever = FaissFlatRetriever(dim=emb_adapter.dim or 384)
    print(f"[fm_agent] 检索索引重建（原索引不可用: {e}）")
gen_adapter = LlamaCppGenAdapter(llm)
ext_adapter = LlamaCppExtractor(llm)
FM_API = cfg["fm_core_api"].rstrip("/")


def ram_used_gb() -> float:
    return psutil.virtual_memory().used / 1024 / 1024 / 1024


class ChatReq(BaseModel):
    messages: list
    temperature: float = 0.15
    max_tokens: int = 128
    model: str = "fm-edge"


def _fetch_atoms(topk: int = 3) -> list:
    try:
        r = requests.get(f"{FM_API}/fm/retrieve", params={"topk": topk}, timeout=30)
    except requests.RequestException as e:
        raise HTTPException(status_code=503,
                            detail=f"FM-Core 内核不可达（{FM_API}）: {e}")
    if r.status_code != 200:
        raise HTTPException(status_code=503, detail=f"FM-Core 内核返回 {r.status_code}")
    return r.json() or []


@app.get("/health")
def health():
    kernel_ok, kernel_state = False, None
    try:
        kernel_ok = requests.get(f"{FM_API}/health", timeout=5).ok
    except requests.RequestException as e:
        kernel_state = str(e)
    return {"status": "ok", "service": "fm-edge-agent", "port": PORT,
            "fm_core_api": FM_API, "kernel_reachable": kernel_ok,
            "kernel_error": kernel_state, "faiss_size": retriever.size,
            "ram_used_gb": round(ram_used_gb(), 2),
            "high_watermark_gb": cfg["high_watermark_gb"]}


@app.post("/v1/chat/completions")
def chat(req: ChatReq):
    if not req.messages:
        raise HTTPException(400, "empty messages")
    user_q = req.messages[-1].get("content") or ""
    if not user_q.strip():
        raise HTTPException(400, "empty question")

    # 1. 从 FM-Core 内核检索记忆
    atoms = _fetch_atoms(topk=3)
    ctx_block = "\n".join(f"- [{a['status']}] {a['content']}" for a in atoms) or "（暂无记忆）"

    # 2. LLM 生成回答（answer() 自动套用 GGUF 对话模板，避免原始续写退化）
    ans = gen_adapter.answer(ctx_block, user_q, req.max_tokens, req.temperature)

    # 3. 事实抽取
    fact = ext_adapter.extract_fact(ans)
    ram = ram_used_gb()
    audit_hash = None
    stored = False

    # 4. 内存水位判定，高水位不再写入提案
    if ram < cfg["high_watermark_gb"] and fact != "[NO_STORE]":
        payload = {"content": fact, "source": "edge-agent-01",
                   "source_type": "llm_extract", "tags": ["edge-auto"]}
        try:
            resp = requests.post(f"{FM_API}/fm/propose", json=payload, timeout=30)
            resp.raise_for_status()
            audit_hash = resp.json().get("mid")
            vec = emb_adapter.encode(fact)
            retriever.add(fact, vec)
            retriever.save(FAISS_PATH)
            stored = True
        except requests.RequestException as e:
            audit_hash = None
            print(f"[fm_agent] 提案回写失败（不影响本次回答）: {e}")

    return {
        "id": f"chatcmpl-fm-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [{"index": 0,
                     "message": {"role": "assistant", "content": ans},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None},
        # —— 本服务自有字段（OpenAI 兼容之上的扩展）——
        "local_fact_extract": fact,
        "audit_mid": audit_hash,
        "fact_stored": stored,
        "memory_used": [a["mid"] for a in atoms],
        "ram_used_gb": round(ram, 2),
    }


def main():
    uvicorn.run("fm_agent.edge_agent:app", host=HOST, port=PORT, workers=1)


if __name__ == "__main__":
    main()
