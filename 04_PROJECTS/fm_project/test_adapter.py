#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""适配器联调测试（Embedding / 检索 / 事实抽取 / 生成）。

运行：python test_adapter.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import diskcache as dc
import yaml
from llama_cpp import Llama

from fm_adapters import (FaissFlatRetriever, LlamaCppExtractor,
                         LlamaCppGenAdapter, OnnxBgeAdapter)

OK = [0]
FAIL = [0]


def check(name, cond, extra=""):
    if cond:
        OK[0] += 1
        print(f"  [PASS] {name}{(' — ' + str(extra)) if extra else ''}")
    else:
        FAIL[0] += 1
        print(f"  [FAIL] {name}{(' — ' + str(extra)) if extra else ''}")


def p(rel: str) -> str:
    q = Path(rel)
    return str(q if q.is_absolute() else (ROOT / q))


def _uniq(text: str) -> float:
    t = (text or "").strip()
    return len(set(t)) / len(t) if t else 0.0


def _uniq_ok(text: str) -> bool:
    """病态重复的判据：未套对话模板时 MiniMind2 会输出「或或或/聚聚聚」。"""
    t = (text or "").strip()
    if len(t) < 4:
        return True
    return _uniq(t) >= 0.35


with open(ROOT / "fm_agent" / "agent_config.yaml", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

print("[1] Embedding 适配器（bge-small-zh ONNX，带磁盘缓存）")
cache = dc.Cache(p(cfg["cache_dir"]))
emb = OnnxBgeAdapter(p(cfg["embedding"]["onnx_path"]), p(cfg["embedding"]["vocab_path"]), cache)
vec1 = emb.encode("九天玄女执掌昆仑秩序")
check("vector dim == 模型自描述维度", len(vec1) == emb.dim, f"len={len(vec1)} dim={emb.dim}")
check("L2 归一化", abs(sum(x * x for x in vec1) - 1.0) < 1e-3, round(sum(x * x for x in vec1), 6))
vec2 = emb.encode("九天玄女执掌昆仑秩序")
check("缓存命中后向量一致", vec1 == vec2, f"cache_len={len(cache)}")

print("[2] FAISS Flat 检索适配器")
ret = FaissFlatRetriever(dim=emb.dim)
ret.add("九天玄女执掌昆仑秩序", vec1)
ret.add("东海龙王镇守归墟", emb.encode("东海龙王镇守归墟"))
hits = ret.search(vec1, topk=2)
check("命中自相似 top1", hits and hits[0][0] == "九天玄女执掌昆仑秩序", hits[:1])
check("返回 2 条", len(hits) == 2, len(hits))
idx_path = p(cfg["faiss_path"])
Path(idx_path).parent.mkdir(parents=True, exist_ok=True)
ret.save(idx_path)
ret2 = FaissFlatRetriever(dim=emb.dim)
ret2.load(idx_path)
check("索引存取往返", len(ret2.text_store) == 2 and ret2.size == 2, ret2.size)

print("[3] 事实抽取适配器（llama.cpp，走对话模板）")
llm = Llama(model_path=p(cfg["llm"]["gguf_path"]), n_ctx=cfg["llm"]["n_ctx"],
            n_threads=cfg["llm"]["n_threads"], n_gpu_layers=cfg["llm"]["n_gpu_layers"],
            verbose=False)
check("GGUF 带对话模板", bool((llm.metadata or {}).get("tokenizer.chat_template")), "")
ext = LlamaCppExtractor(llm)
fact = ext.extract_fact("昆仑霞光漫过玉阙，九天玄女端坐云台执掌秩序。")
check("抽取非空", bool(fact), repr(fact[:80]))
check("抽取无病态重复", _uniq_ok(fact), f"uniq={_uniq(fact):.2f}")

print("[4] 生成适配器（种子真值约束生成，走对话模板）")
gen = LlamaCppGenAdapter(llm)
out = gen.answer("- 九天玄女执掌昆仑秩序", "昆仑是谁在执掌？", 64, 0.1)
check("生成非空", bool(out), repr(out[:80]))
check("生成无病态重复", _uniq_ok(out), f"uniq={_uniq(out):.2f}")
prompt = gen.build_prompt("- 九天玄女执掌昆仑秩序", "昆仑是谁在执掌？")
check("prompt 模板含真值约束", "禁止编造" in prompt, "")

print(f"\n===> PASS {OK[0]} / FAIL {FAIL[0]}")
sys.exit(1 if FAIL[0] else 0)
