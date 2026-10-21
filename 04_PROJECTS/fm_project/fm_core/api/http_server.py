#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FM-Core 内核 API（默认端口 8100）。

启动：python -m fm_core.api.http_server   （须在 fm_project 根目录执行，先于边缘 Agent）

端点：
  POST /fm/seed/add   种子真值写入（不可变更基线）
  POST /fm/propose    提案写入（待共识）
  GET  /fm/retrieve?topk=3   检索记忆原子（种子→归档→提案，按分数降序）
  POST /fm/vote       共识投票（≥2 票且比例达标才裁决归档/软遗忘）
  GET  /fm/atoms      原子列表（可按 status 过滤）
  GET  /fm/audit      审计账本（哈希链，含完整性校验）
  GET  /health        内核健康
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]   # fm_project/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fm_core.kernel import AXIOM, KERNEL_NAME, KERNEL_VERSION, MemoryKernel  # noqa: E402

DB_PATH = os.environ.get("FM_CORE_DB", str(ROOT / "fm_data" / "fm_core.db"))
PORT = int(os.environ.get("FM_CORE_PORT", "8100"))
HOST = os.environ.get("FM_CORE_HOST", "127.0.0.1")

kernel = MemoryKernel(DB_PATH)
app = FastAPI(title="FM-Core Kernel｜元极恒一 Lv11 基线",
              version=KERNEL_VERSION, description="联邦记忆智能体内核 Phase1")


# ---------- 请求体 ----------
class SeedReq(BaseModel):
    content: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)


class ProposeReq(BaseModel):
    content: str = Field(..., min_length=1)
    source: Optional[str] = None
    source_type: str = "llm_extract"
    tags: List[str] = Field(default_factory=list)


class VoteReq(BaseModel):
    mid: str
    agree: bool
    voter: str = "anonymous"


# ---------- 路由 ----------
@app.get("/health")
def health():
    return kernel.health()


@app.post("/fm/seed/add")
def seed_add(req: SeedReq):
    return kernel.add_seed(req.content, req.tags)


@app.post("/fm/propose")
def propose(req: ProposeReq):
    return kernel.propose(req.content, req.source, req.source_type, req.tags)


@app.get("/fm/retrieve")
def retrieve(topk: int = Query(3, ge=1, le=100)):
    return kernel.retrieve(topk)


@app.post("/fm/vote")
def vote(req: VoteReq):
    res = kernel.vote(req.mid, req.agree, req.voter)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res)
    return res


@app.get("/fm/atoms")
def atoms(status: Optional[str] = None, limit: int = Query(50, ge=1, le=500)):
    rows = kernel.list_atoms(status, limit)
    return {"count": len(rows), "atoms": rows}


@app.get("/fm/audit")
def audit(limit: int = Query(50, ge=1, le=500), verify: bool = False):
    out = {"count": 0, "entries": kernel.audit_log(limit)}
    out["count"] = len(out["entries"])
    if verify:
        out["chain"] = kernel.verify_chain()
    return out


@app.get("/")
def index():
    return {"kernel": KERNEL_NAME, "version": KERNEL_VERSION, "axiom": AXIOM,
            "port": PORT, "docs": "/docs", "endpoints": [
                "/fm/seed/add", "/fm/propose", "/fm/retrieve",
                "/fm/vote", "/fm/atoms", "/fm/audit", "/health"]}


def main():
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, workers=1, log_level="info")


if __name__ == "__main__":
    main()
