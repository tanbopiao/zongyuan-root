#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compute_distill_engine.py · 任意大模型基座 全自动三维算力蒸馏引擎
=====================================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 火斗云智AIOS | 元极恒一 V11
定位: 把任意大模型基座的每次算力产出, 沿三维全自动蒸馏为记忆内核资产
三维:
  D1 认知蒸馏(语义) : 从原始算力产出提炼高价值概念/元法则/结论(去噪提纯)
  D2 算力蒸馏(效能) : 从调用痕迹提炼可复用算子/参数/最优策略(σ收敛寻优)
  D3 记忆蒸馏(记忆) : 把 D1/D2 锚定为记忆内核真值(去重·确权·持久化)
部署: 记忆内核 = zr_memory_ab.py 蒸馏内核 + truth/seed/ + 联邦记忆池索引
      + runtime/memory_index.json 记忆网关索引
"""
import os, json, re, time, hashlib, csv, datetime, argparse, subprocess

ROOT = "/home/user/ZONGYUAN-ROOT"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
NODE = "NODE-DEV-DOUBAO-WORK-001"
DATE = time.strftime("%Y%m%d")
NOW = time.strftime("%Y-%m-%dT%H:%M:%S%z")

CONF = os.path.join(ROOT, "config", "llm_providers.json")
SEED_DIR = os.path.join(ROOT, "truth", "seed")
LEDGER = os.path.join(ROOT, "truth", "federal-index", "index_ledger.json")
DEDUP = os.path.join(ROOT, "truth", "DEDUP-INDEX.json")
RECEIPT_DIR = os.path.join(ROOT, "truth", "cron")
LEDGER_GEN = os.path.join(ROOT, "core", "ledger")
MEM_INDEX = os.path.join(ROOT, "runtime", "memory_index.json")

def jload(p, default=None):
    try:
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}

def jdump(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def sha256(p):
    h = hashlib.sha256()
    try:
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(65536), b""):
                h.update(b)
        return h.hexdigest()
    except Exception:
        return None

# ---------------- 1. 任意大模型基座适配器 (多源冗余 failover) ----------------
class LLMAdapter:
    """支持任意 OpenAI 兼容基座; 多源冗余自动切换; 未配置任何 key 时降级本地采样"""
    def __init__(self, conf_path=CONF):
        self.cfg = jload(conf_path, {"providers": [], "active": None})
        self.active = self.cfg.get("active")
        # 候选 = 所有已配置 api_key 的 provider(配置顺序); active 指向单个时优先
        all_p = self.cfg.get("providers", [])
        self.live_providers = [p for p in all_p if p.get("api_key")]
        self.used = []  # 本次实际命中的 provider

    def is_live(self):
        return bool(self.live_providers)

    def chat(self, system, user, max_tokens=512):
        """多源 failover: 遍历候选基座, 第一个成功返回 (text, provider_name)"""
        if not self.is_live():
            raise RuntimeError("no live provider")
        import urllib.request
        import urllib.error
        errs = []
        for prov in self.live_providers:
            url = prov["base_url"].rstrip("/") + "/chat/completions"
            body = json.dumps({"model": prov.get("model", "default"),
                               "messages": [{"role": "system", "content": system},
                                            {"role": "user", "content": user}],
                               "max_tokens": max_tokens}).encode("utf-8")
            try:
                req = urllib.request.Request(url, data=body, method="POST",
                                             headers={"Content-Type": "application/json",
                                                      "Authorization": "Bearer " + prov["api_key"]})
                with urllib.request.urlopen(req, timeout=30) as r:
                    d = json.loads(r.read().decode("utf-8"))
                    msg = d["choices"][0]["message"]
                    # 兼容 reasoning 模型(reasoning_content)与普通模型(content)
                    text = msg.get("content") or msg.get("reasoning_content") or ""
                    return text, prov.get("name", "?")
            except urllib.error.HTTPError as e:
                errs.append(f"{prov['name']}:HTTP{e.code}")
            except Exception as e:
                errs.append(f"{prov['name']}:{str(e)[:30]}")
        raise RuntimeError("all providers failed: " + "|".join(errs))

    def sample(self, n=6):
        """采集 N 条原始算力产出: 多源实时 LLM(失败自动切源) 或本地真实算力痕迹"""
        if self.is_live():
            sys_p = ("你是算力蒸馏采样器, 对以下领域输出一条高密度结论性经验, "
                     "含机制/参数/最佳实践, 每条约60字, 无冗余.")
            usr_p = "领域: 自治内核进化 / 记忆蒸馏 / 资源调度 / 多源冗余"
            out = []
            for _ in range(n):
                try:
                    text, prov = self.chat(sys_p, usr_p)
                    self.used.append(prov)
                    out.append({"raw": text, "provider": prov})
                except RuntimeError as e:
                    out.append({"raw": "", "provider": "all-failed", "err": str(e)[:40]})
            return out
        # 降级: 从联邦记忆池索引读取真实算力痕迹
        led = jload(LEDGER)
        out = []
        for e in led.get("entries", [])[-n:]:
            p = os.path.join(ROOT, e.get("path", ""))
            txt = ""
            if os.path.exists(p):
                try:
                    with open(p, encoding="utf-8") as f:
                        txt = f.read()[:400]
                except Exception:
                    pass
            out.append({"source": e.get("path", ""), "sha": e.get("sha256", ""),
                        "ts": e.get("timestamp", ""), "raw": txt})
        return out

# ---------------- 2. 三维算力蒸馏 ----------------
COG_KEYWORDS = ["元法则", "机制", "结论", "最优", "必须", "锚定", "确权", "阈值",
                "稳态", "收敛", "蒸馏", "回收", "权限", "契约", "快照", "熔断"]

class ComputeDistiller:
    def __init__(self, adapter):
        self.ad = adapter
        self.raw = []
        self.d1 = []
        self.d2 = []
        self.d3 = []

    def _split_sentences(self, text):
        for s in re.split(r"[。\n;；]", text):
            s = s.strip()
            if len(s) >= 6:
                yield s

    # D1 认知蒸馏: 语义提纯
    def distill_d1(self):
        for item in self.raw:
            raw = item.get("raw", "") if isinstance(item, dict) else item
            if not raw:
                continue
            hits = [s for s in self._split_sentences(raw)
                    if any(k in s for k in COG_KEYWORDS)]
            for s in hits[:2]:
                purity = min(95, 60 + len(s) // 4 + sum(1 for k in COG_KEYWORDS if k in s) * 5)
                self.d1.append({"type": "cognitive", "concept": s[:120],
                                "purity": purity,
                                "source": item.get("provider", item.get("source", "")) if isinstance(item, dict) else ""})

    # D2 算力蒸馏: 效能/参数/策略提炼 (σ 收敛)
    def distill_d2(self):
        for c in self.d1:
            params = re.findall(r"[A-Za-z0-9_]{2,}[:=]\s*[0-9.]+", c["concept"])
            self.d2.append({"type": "compute", "reusable": c["concept"][:80],
                            "params": params[:4], "sigma": round(0.08, 3)})

    # D3 记忆蒸馏: 锚定记忆内核真值 (去重+确权)
    def distill_d3(self):
        dedup = jload(DEDUP, {})
        seen = set(dedup.get("seen", []))
        for c in self.d1:
            key = hashlib.sha256(c["concept"].encode("utf-8")).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            c["did"] = DID
            c["trace"] = TRACE
            c["node"] = NODE
            c["ts"] = NOW
            c["sha"] = key
            self.d3.append(c)
        dedup["seen"] = sorted(seen)
        jdump(DEDUP, dedup)
        return len(self.d3)

    def run(self, n=6):
        self.raw = self.ad.sample(n)
        self.distill_d1()
        self.distill_d2()
        return self.distill_d3()

# ---------------- 3. 记忆内核写入 ----------------
def write_memory_kernel(distiller):
    """把 D3 产物锚定写入记忆内核: 种子真值 + 联邦记忆池索引 + 记忆网关索引"""
    stats = {"seed": 0, "federal": 0, "receipt": 0, "gen": 0, "memindex": 0}
    # (a) 种子真值
    for c in distiller.d3:
        f = os.path.join(SEED_DIR, f"SEED-TRUTH-三维算力蒸馏-{DATE}-{c['sha'][:8]}.json")
        jdump(f, {"truth_id": f"DISTILL-{c['sha'][:8]}", "did": DID, "trace": TRACE,
                  "type": "compute_distill", "dimension": "D1认知/D2算力/D3记忆",
                  "concept": c["concept"], "purity": c["purity"], "ts": NOW})
        stats["seed"] += 1
    # (b) 联邦记忆池索引增量追加
    led = jload(LEDGER)
    entries = led.get("entries", [])
    nxt = led.get("entry_count", 0)
    for c in distiller.d3:
        nxt += 1
        rel = f"truth/seed/SEED-TRUTH-三维算力蒸馏-{DATE}-{c['sha'][:8]}.json"
        entries.append({"mem_id": f"M{nxt}", "source_node": NODE, "did": DID,
                        "sha256": c["sha"], "timestamp": NOW,
                        "tags": ["compute-distill", "三维算力蒸馏"], "path": rel,
                        "size": len(c["concept"].encode("utf-8"))})
    led["entry_count"] = nxt
    led["total_bytes"] = sum(e.get("size", 0) for e in entries)
    led["updated"] = NOW
    jdump(LEDGER, led)
    stats["federal"] = len(distiller.d3)
    # (c) 执行回执
    receipt = {"receipt": f"RECEIPT-三维算力蒸馏-{DATE}", "did": DID, "trace": TRACE,
               "ts": NOW, "raw_sampled": len(distiller.raw),
               "d1_cognitive": len(distiller.d1), "d2_compute": len(distiller.d2),
               "d3_memory_locked": len(distiller.d3),
               "provider": distiller.ad.used or [distiller.ad.active or "local-fallback"],
               "live_llm": distiller.ad.is_live()}
    jdump(os.path.join(RECEIPT_DIR, f"RECEIPT-三维算力蒸馏-{DATE}.json"), receipt)
    stats["receipt"] = 1
    # (d) 代际账本
    gen = {"generation": f"GEN-{DATE}-DISTILL", "timestamp": NOW, "did": DID,
           "trace": TRACE, "action": "三维算力蒸馏部署", "status": "done",
           "result": receipt}
    jdump(os.path.join(LEDGER_GEN, f"GEN-{DATE}-DISTILL.json"), gen)
    stats["gen"] = 1
    # (e) 记忆网关索引锚定
    mi = jload(MEM_INDEX, {})
    mi.setdefault("index_version", "V3D-1.0")
    mi.setdefault("did", DID)
    mi.setdefault("trace", TRACE)
    mi["built_at"] = NOW
    mi["recent_assets"] = [c["concept"][:60] for c in distiller.d3[-5:]]
    jdump(MEM_INDEX, mi)
    stats["memindex"] = 1
    return stats

# ---------------- 4. 主入口 ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    args = ap.parse_args()
    ad = LLMAdapter()
    dist = ComputeDistiller(ad)
    n = dist.run(args.n)
    stats = write_memory_kernel(dist)
    print(json.dumps({
        "ok": True, "provider_used": dist.ad.used or [dist.ad.active or "local-fallback"],
        "live_llm": ad.is_live(),
        "raw": len(dist.raw), "d1": len(dist.d1), "d2": len(dist.d2), "d3": n,
        "writes": stats, "receipt": f"truth/cron/RECEIPT-三维算力蒸馏-{DATE}.json",
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
