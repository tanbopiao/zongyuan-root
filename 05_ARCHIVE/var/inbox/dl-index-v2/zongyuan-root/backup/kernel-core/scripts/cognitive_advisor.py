#!/usr/bin/env python3
"""认知建议器（CognitiveAdvisor）：给内核补"认知推理"层入口——目标/问题 → LLM 建议 → 审计留痕。

Provider：
  - ark（火山方舟豆包，验证可用）：https://ark.cn-beijing.volces.com/api/v3，model=ep-20260925170233-g4f7w
  - zhipu（免费）：https://open.bigmodel.cn/api/paas/v4，model=glm-4-flash
  - huodouai：https://www.huodouai.com/v1（云端网关，需上游可用）
密钥来源（零明文落盘，META-LAW-CRYPT-LOCK-001）：
  1. 环境变量 ZONGYUAN_ZHIPU_KEY 优先（运行时注入）
  2. 本地加密存储 var/state/zhipu-key.enc.json（AES-256-GCM，KEK=环境变量 ZR_API_ENC_KEY）
  两者皆缺 → fail-closed unavailable（不决策、不阻塞）
设计：只建议、不决策；实际动作一律走 ActionGate 审批。
用法：
  ZONGYUAN_ZHIPU_KEY=<key> cognitive_advisor.py "<目标>"            # zhipu 免费模型
  cognitive_advisor.py "<目标>" --provider huodouai --model doubao
"""
import argparse
import base64
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "var" / "audit" / "audit.jsonl"
KEY_ENC = {name: ROOT / "var" / "state" / f"{name}-key.enc.json" for name in ("zhipu", "ark", "huodouai")}

PROVIDERS = {
    "zhipu": {"base": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash", "free": True},
    "ark": {"base": "https://ark.cn-beijing.volces.com/api/v3", "model": "ep-20260925170233-g4f7w", "free": False},
    "huodouai": {"base": os.environ.get("ZONGYUAN_LLM_BASE", "https://www.huodouai.com/v1"), "model": "doubao"},
}


def audit(event, actor, action, result, detail):
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": event,
           "actor": actor, "action": action, "result": result, "detail": detail}
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_key(provider):
    """密钥加载：环境变量优先 → 加密存储；返回 (key, source)。"""
    env_map = {"zhipu": "ZONGYUAN_ZHIPU_KEY", "ark": "ZONGYUAN_ARK_KEY", "huodouai": "ZONGYUAN_LLM_KEY"}
    env = os.environ.get(env_map.get(provider, ""), "")
    if env:
        return env, "env"
    enc_file = KEY_ENC.get(provider)
    if enc_file and enc_file.exists():
        try:
            enc = json.loads(enc_file.read_text(encoding="utf-8"))
            kek = os.environ.get("ZR_API_ENC_KEY", "")
            if not kek:
                kekf = Path("/home/user/ZONGYUAN-ROOT/var/kek.env")
                if kekf.exists():
                    kek = kekf.read_text().strip()
            if kek:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                iv = base64.b64decode(enc["iv_b64"])
                ct = base64.b64decode(enc["ciphertext_b64"])
                k = hashlib.sha256(kek.encode()).digest()
                aad = enc.get("aad")
                pt = AESGCM(k).decrypt(iv, ct, aad.encode() if aad else None)
                return pt.decode(), "encrypted_storage"
        except Exception as e:
            audit("kernel.cognitive", "operator", "keyload", "fail", f"{provider} 解密失败 {e}")
    return None, "unavailable"


def advise(goal, provider, model):
    p = PROVIDERS.get(provider)
    if not p:
        return {"verdict": "deny", "reason": f"未知 provider {provider}，支持: {list(PROVIDERS)}"}
    key, src = load_key(provider)
    if not key:
        note = f"{provider} 密钥未注入（环境变量或加密存储均无）——fail-closed 不决策"
        audit("kernel.cognitive", "operator", "advise", "unavailable", f"goal={goal[:60]} {note}")
        return {"verdict": "unavailable", "reason": note, "provider": provider, "key_source": src}

    base = p["base"]
    mdl = model or p["model"]
    system = ("你是 ZONGYUAN-ROOT 自治内核的认知建议层。对给定目标输出结构化建议 JSON："
              '{"options":[{"name","desc","risk(0-10)"}],"recommendation","risks":[],"notes"}。'
              "只给建议，不执行任何动作。")
    body = {"model": mdl, "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": goal},
    ], "temperature": 0.4}
    req = urllib.request.Request(base + "/chat/completions",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {key}"})
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    else:
        audit("kernel.cognitive", "operator", "advise", "fail", f"goal={goal[:60]} provider={provider} err={last_err}")
        return {"verdict": "fail", "provider": provider, "reason": str(last_err)}
    content = data["choices"][0]["message"]["content"]
    try:
        advice = json.loads(content)
    except Exception:
        import re as _re
        m = _re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if m:
            try:
                advice = json.loads(m.group(1))
            except Exception:
                advice = {"raw": content}
        else:
            advice = {"raw": content}
    audit("kernel.cognitive", "operator", "advise", "ok",
          f"goal={goal[:60]} provider={provider} model={mdl} options={len(advice.get('options', []))}")
    return {"verdict": "ok", "provider": provider, "model": mdl, "key_source": src, "advice": advice}


def main():
    ap = argparse.ArgumentParser(description="认知建议器（只建议不决策）")
    ap.add_argument("goal")
    ap.add_argument("--provider", choices=list(PROVIDERS), default="zhipu")
    ap.add_argument("--model", default=None)
    args = ap.parse_args()
    print(json.dumps(advise(args.goal, args.provider, args.model), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
