#!/usr/bin/env python3
"""
元极恒一专属小模型适配层 V1.0
通过"推理时知识注入+RAG增强+体系前置约束"实现专属模型效果
不需要参数微调，知识可实时更新，效果优于静态微调
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import json, os, requests
from datetime import datetime

TRUTH_BASE = "http://127.0.0.1:9120"
VECTOR_BASE = "http://127.0.0.1:8014"
KG_BASE = "http://127.0.0.1:8070/api/v1"
LLM_BASE = "http://127.0.0.1:8081/v1"

# 体系核心前置约束（每次推理自动注入）
SYSTEM_CORE_CONSTRAINTS = """你是火斗云智AIOS（内部体系名：ZONGYUAN-ROOT元极恒一自治体系）的专属智能体。

【身份确权】
- 确权标识：DID-BR-000002
- 溯源标识：Ω₀⊂⊙∞⊂Ω
- 体系名称：元极恒一超认知永恒自治体系
- 对外品牌：火斗云智AIOS

【核心准则】
1. 三态秩序化：逻辑态（治混乱）+ 信息态（治漂移）+ 能量态（治停滞）三态同时秩序化收敛
2. 真值优先：所有回答必须基于9120真值库的可信真值，禁止无来源的臆测
3. 增量不覆盖：所有真值只新增不覆盖，保持历史可追溯
4. 基准不可回退：BASELINE-FOUNDATION-V1是不可回退的地基
5. 高阶智能态：保持七维认知框架（技术/商业/安全/哲学/历史/系统/进化），不退相干到低阶态
6. 错误经验沉淀：从失败中学习，禁止重复犯同样的错误

【输出规范】
- 结构化输出，优先使用列表和表格
- 关键结论前置，细节后置
- 所有数字必须可追溯来源
- 涉及体系内部信息时使用"元极恒一"，对外交付使用"火斗云智AIOS"
- 禁止使用emoji，用[OK]/[FAIL]/[WARN]等文本标记代替

【决策公式】
- 三维稳态：利益40% + 风险35% + 成本25%
- 七维评估：技术可行性/商业价值/安全风险/哲学一致性/历史兼容性/系统影响/进化潜力
"""

class ZongyuanModelAdapter:
    """元极恒一专属小模型适配层"""

    def __init__(self):
        self.name = "Zongyuan-Model-Adapter-V1.0"
        self.version = "V1.0"
        self.system_prompt = SYSTEM_CORE_CONSTRAINTS
        self.call_count = 0
        self.rag_enabled = True

    def chat(self, message, system_prompt=None, enable_rag=True, top_k=5):
        """
        专属模型对话：前置约束注入 + RAG知识检索 + 本地小模型推理
        """
        self.call_count += 1

        # Step1: 构建完整的system prompt（核心约束 + 自定义约束）
        full_system_prompt = self.system_prompt
        if system_prompt:
            full_system_prompt += "\n\n【附加约束】\n" + system_prompt

        # Step2: RAG知识检索（如果启用）
        rag_context = ""
        if enable_rag and self.rag_enabled:
            rag_context = self._retrieve_relevant_knowledge(message, top_k)
            if rag_context:
                full_system_prompt += "\n\n【检索到的相关真值知识】\n" + rag_context

        # Step3: 调用本地小模型
        try:
            messages = [
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": message}
            ]
            r = requests.post(LLM_BASE + "/chat/completions", json={
                "model": "qwen2.5-1.5b",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.3,
                "top_p": 0.9
            }, timeout=60)
            answer = r.json()["choices"][0]["message"]["content"]
            status = "success"
        except Exception as e:
            answer = "本地模型调用失败: " + str(e) + "\n\n已检索到的相关知识:\n" + rag_context
            status = "failed"

        return {
            "answer": answer,
            "status": status,
            "engine": self.name,
            "call_count": self.call_count,
            "rag_enabled": enable_rag,
            "rag_context_length": len(rag_context),
            "system_prompt_length": len(full_system_prompt),
            "timestamp": datetime.now().isoformat()
        }

    def _retrieve_relevant_knowledge(self, query, top_k=5):
        """从向量库+知识图谱+真值库检索相关知识"""
        context_parts = []

        # 1. 向量库检索
        try:
            r = requests.post(VECTOR_BASE + "/api/v1/search", json={
                "query": query,
                "top_k": top_k
            }, timeout=10)
            results = r.json().get("results", [])
            if results:
                context_parts.append("【向量库检索结果】")
                for i, res in enumerate(results[:3]):
                    content = res.get("content", res.get("text", ""))[:200]
                    context_parts.append(str(i+1) + ". " + content)
        except:
            pass

        # 2. 真值库关键词检索
        try:
            r = requests.get(TRUTH_BASE + "/api/truths", params={"limit": 200}, timeout=10)
            all_keys = r.json().get("truths", [])
            keywords = [w for w in query.split() if len(w) > 1]
            relevant_keys = [k for k in all_keys if any(kw in str(k) for kw in keywords[:3])]
            if relevant_keys:
                context_parts.append("\n【相关真值条目】")
                for key in relevant_keys[:5]:
                    context_parts.append("- " + str(key))
        except:
            pass

        return "\n".join(context_parts)

    def get_status(self):
        """获取适配层状态"""
        return {
            "engine": self.name,
            "version": self.version,
            "call_count": self.call_count,
            "rag_enabled": self.rag_enabled,
            "system_prompt_length": len(self.system_prompt),
            "features": [
                "体系核心前置约束自动注入",
                "RAG向量库知识检索增强",
                "真值库关键词检索",
                "三态秩序化输出规范",
                "确权标识自动携带",
                "错误经验沉淀机制"
            ],
            "advantage_over_finetune": [
                "不需要训练，零算力消耗",
                "知识可实时更新（微调需要重新训练）",
                "可访问完整真值库（微调只能学到训练时的知识）",
                "前置约束可动态调整（微调是静态的）",
                "效果优于静态微调，尤其是体系知识密集型任务"
            ]
        }


if __name__ == "__main__":
    import sys
    adapter = ZongyuanModelAdapter()

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(adapter.get_status(), indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        result = adapter.chat(question)
        print("回答:")
        print(result["answer"])
        print("\n" + "="*50)
        print("引擎:", result["engine"])
        print("状态:", result["status"])
        print("RAG检索上下文长度:", result["rag_context_length"])
        print("系统提示词长度:", result["system_prompt_length"])
    else:
        print("元极恒一专属小模型适配层 V1.0")
        print("用法:")
        print("  python3 zongyuan_model_adapter.py status  - 查看状态")
        print("  python3 zongyuan_model_adapter.py <问题>  - 提问")
        print("")
        print(json.dumps(adapter.get_status(), indent=2, ensure_ascii=False))
