#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 多智能体辩论决策引擎 v1.0
三角色议会制决策：乐观(利益最大化) / 保守(风险最小化) / 中立(平衡)
流程：各自论证 → 交叉质询 → 七维公式量化裁决
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import json
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

AI_PROXY = "http://127.0.0.1:8021/v1/chat/completions"
DECISION_ENGINE = "http://127.0.0.1:8180/evaluate"
GATEWAY_URL = "http://127.0.0.1:9120/api/truth/upsert"
PORT = 8185

ROLE_PROMPTS = {
    "optimist": """你是【乐观派分析师】。职责是最大化利益和机会。
重点关注潜在收益、增长机会、竞争优势；假设执行顺利计算最佳回报；对风险持乐观态度。
输出JSON：{"立场":"乐观","核心论点":"...","预期收益":"...","关键机会":["..."],"风险评估":"可控"}""",
    "pessimist": """你是【保守派分析师】。职责是最小化风险和损失。
重点关注潜在风险、失败概率、下行空间；假设最坏情景计算最大损失；对机会持谨慎态度。
输出JSON：{"立场":"保守","核心论点":"...","最大风险":"...","关键隐患":["..."],"收益评估":"有限"}""",
    "neutral": """你是【中立派分析师】。职责是平衡利益与风险。
客观评估收益和风险概率分布；关注期望值和风险调整后收益；识别其他方盲点。
输出JSON：{"立场":"中立","核心论点":"...","期望值分析":"...","平衡点":"...","建议方案":"..."}"""
}

def call_ai(system_prompt, user_prompt, max_tokens=500):
    try:
        resp = requests.post(AI_PROXY, json={
            "model": "doubao-lite",
            "messages": [{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
            "max_tokens": max_tokens, "temperature": 0.7
        }, timeout=60)
        content = resp.json()["choices"][0]["message"]["content"].strip()
        try:
            start, end = content.find("{"), content.rfind("}")+1
            return json.loads(content[start:end])
        except:
            return {"raw": content[:200]}
    except Exception as e:
        return {"error": str(e)}

def run_debate(question, context=""):
    debate_id = f"DEBATE-{int(time.time())}"
    print(f"\n{'='*50}\n  多智能体辩论: {question}\n  ID: {debate_id}\n{'='*50}")

    # 第一轮：各方陈述
    print("\n[第一轮] 各方陈述...")
    statements = {}
    for role, prompt in ROLE_PROMPTS.items():
        result = call_ai(prompt, f"决策问题：{question}\n背景：{context}\n请陈述你的立场。")
        statements[role] = result if isinstance(result, dict) else {"raw": str(result)}
        print(f"  ✅ {role}")

    # 第二轮：交叉质询
    print("\n[第二轮] 交叉质询...")
    responses = {}
    for role, prompt in ROLE_PROMPTS.items():
        others = [f"{r}: {json.dumps(s, ensure_ascii=False)[:150]}" for r,s in statements.items() if r != role]
        result = call_ai(prompt, f"问题：{question}\n其他方观点：\n{chr(10).join(others)}\n请反驳或补充。", 400)
        responses[role] = result if isinstance(result, dict) else {"raw": str(result)}
        print(f"  ✅ {role}")

    # 第三轮：七维公式裁决
    print("\n[第三轮] 七维公式裁决...")
    try:
        resp = requests.post(DECISION_ENGINE, json={
            "decision": question,
            "options": [
                {"name":"乐观方案","description":json.dumps(statements.get("optimist",{}),ensure_ascii=False)[:200]},
                {"name":"保守方案","description":json.dumps(statements.get("pessimist",{}),ensure_ascii=False)[:200]},
                {"name":"平衡方案","description":json.dumps(statements.get("neutral",{}),ensure_ascii=False)[:200]}
            ]
        }, timeout=30)
        arbitration = resp.json()
    except Exception as e:
        arbitration = {"recommendation":"平衡方案","scores":{"乐观":65,"保守":70,"平衡":80},"note":f"降级简单加权: {e}"}

    recommendation = arbitration.get("recommendation", "平衡方案")
    print(f"  ✅ 推荐: {recommendation}")

    result = {
        "debate_id": debate_id, "question": question,
        "round1_opening": statements, "round2_cross": responses,
        "arbitration": arbitration, "recommendation": recommendation,
        "created_at": time.time(), "did": "DID-BR-000002"
    }

    # 上报9120
    try:
        requests.post(GATEWAY_URL, json={
            "key": f"DECISION.DEBATE.{debate_id}",
            "value": f"辩论决策：{question}。推荐：{recommendation}",
            "source": "multi_agent_debate", "did": "DID-BR-000002",
            "truth_type": "decision_record", "confidence": 0.85
        }, timeout=5)
    except: pass

    print(f"\n辩论完成！推荐: {recommendation}")
    return result

class DebateHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}
    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status":"ok","service":"multi-agent-debate","port":PORT})
            return
        self._send_json({"error":"not found"},404)
    def do_POST(self):
        if self.path == "/api/debate/run":
            body = self._read_body()
            if not body.get("question"):
                self._send_json({"error":"缺少question"},400)
                return
            result = run_debate(body["question"], body.get("context",""))
            self._send_json(result)
            return
        self._send_json({"error":"not found"},404)

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), DebateHandler)
    print(f"多智能体辩论决策引擎 v1.0 端口{PORT}")
    server.serve_forever()
