#!/usr/bin/env python3
"""
自主决策通知机制 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

功能：
1. 自动生成本轮自主决策执行摘要
2. 区分"自主决策通过项"和"待人工确认项"
3. 发送到ZONGYUAN-ROOT内核通知群
4. 记录通知日志，支持幂等防重复

决策标准（三维稳态公式：利益40%/风险35%/成本25%）：
- A级（≥85分）：自主决策通过，直接执行，通知内核群
- B级（70-84分）：需人工确认，发起飞书审批
- C级（<70分）：暂缓，上报待评估
"""
import json
import hashlib
import time
import subprocess
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# 内核通知群chat_id
KERNEL_CHAT_ID = "oc_1c68eb3664e751e397062ff0c60ffa3e"

# 通知日志路径
NOTIFY_LOG = os.path.expanduser("~/.zongyuan_root/kernel/auto_decision_notify_log.json")


class DecisionLevel:
    A = "AUTO_PASS"      # A级：自主决策通过
    B = "NEED_APPROVAL"  # B级：需人工审批
    C = "HOLD"           # C级：暂缓


class AutoDecisionNotifier:
    """自主决策通知器"""
    
    def __init__(self):
        self.log = self._load_log()
    
    def _load_log(self) -> List[Dict]:
        if os.path.exists(NOTIFY_LOG):
            with open(NOTIFY_LOG) as f:
                return json.load(f)
        return []
    
    def _save_log(self):
        os.makedirs(os.path.dirname(NOTIFY_LOG), exist_ok=True)
        with open(NOTIFY_LOG, 'w') as f:
            json.dump(self.log, f, ensure_ascii=False, indent=2)
    
    def calculate_score(self, benefit: float, risk: float, cost: float) -> float:
        """三维稳态评分：利益40%/风险35%/成本25%"""
        # benefit: 0-100, risk: 0-100(越低越好), cost: 0-100(越低越好)
        score = benefit * 0.4 + (100 - risk) * 0.35 + (100 - cost) * 0.25
        return round(score, 1)
    
    def get_decision_level(self, score: float) -> str:
        if score >= 85:
            return DecisionLevel.A
        elif score >= 70:
            return DecisionLevel.B
        else:
            return DecisionLevel.C
    
    def generate_report(self, decisions: List[Dict], system_status: Dict = None) -> str:
        """生成自主决策报告（Markdown格式）"""
        tz = timezone(timedelta(hours=8))
        now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        
        auto_passed = [d for d in decisions if d.get('level') == DecisionLevel.A]
        need_approval = [d for d in decisions if d.get('level') == DecisionLevel.B]
        hold = [d for d in decisions if d.get('level') == DecisionLevel.C]
        
        lines = [
            f"## 🤖 自主决策通知｜火斗云智AIOS",
            f"",
            f"**DID**: DID-BR-000002｜**溯源**: Ω₀⊂⊙∞⊂Ω",
            f"**时间**: {now}",
            f"",
        ]
        
        if system_status:
            lines.append("### 系统状态")
            lines.append("")
            lines.append("| 项目 | 状态 |")
            lines.append("|------|------|")
            for k, v in system_status.items():
                lines.append(f"| {k} | {v} |")
            lines.append("")
        
        if auto_passed:
            lines.append(f"### ✅ 自主决策通过项（{len(auto_passed)}项，无需人工审批）")
            lines.append("")
            for d in auto_passed:
                lines.append(f"- **{d['name']}**：{d.get('desc', '')}（评分{d.get('score', 'N/A')}分）")
            lines.append("")
        
        if need_approval:
            lines.append(f"### ⚠️ 待人工审批项（{len(need_approval)}项）")
            lines.append("")
            for d in need_approval:
                lines.append(f"- **{d['name']}**：{d.get('desc', '')}（评分{d.get('score', 'N/A')}分）")
            lines.append("")
        
        if hold:
            lines.append(f"### ⏸️ 暂缓项（{len(hold)}项）")
            lines.append("")
            for d in hold:
                lines.append(f"- **{d['name']}**：{d.get('desc', '')}（评分{d.get('score', 'N/A')}分）")
            lines.append("")
        
        lines.append("> 本通知由自主稳态决策机制自动生成。A级（≥85分）直接执行，B级（70-84分）需人工审批，C级（<70分）暂缓。")
        
        return "\n".join(lines)
    
    def send_to_kernel_group(self, markdown: str, idempotency_key: str = None) -> Dict:
        """发送到内核通知群"""
        if idempotency_key is None:
            idempotency_key = f"auto-decision-{int(time.time())}"
        
        # 检查幂等
        for entry in self.log:
            if entry.get('idempotency_key') == idempotency_key:
                return {"status": "duplicate", "message": "重复通知，已跳过"}
        
        try:
            result = subprocess.run(
                ['lark-cli', 'im', '+messages-send',
                 '--chat-id', KERNEL_CHAT_ID,
                 '--markdown', markdown,
                 '--idempotency-key', idempotency_key],
                capture_output=True, text=True, timeout=30
            )
            
            response = json.loads(result.stdout) if result.stdout else {}
            
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "idempotency_key": idempotency_key,
                "status": "sent" if response.get("ok") else "failed",
                "message_id": response.get("data", {}).get("message_id", ""),
                "error": response.get("error", {}).get("message", "") if not response.get("ok") else ""
            }
            self.log.append(log_entry)
            self._save_log()
            
            return log_entry
            
        except Exception as e:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "idempotency_key": idempotency_key,
                "status": "error",
                "error": str(e)
            }
            self.log.append(log_entry)
            self._save_log()
            return log_entry
    
    def notify(self, decisions: List[Dict], system_status: Dict = None) -> Dict:
        """完整通知流程：生成报告→发送→记录"""
        markdown = self.generate_report(decisions, system_status)
        result = self.send_to_kernel_group(markdown)
        return {
            "report": markdown,
            "send_result": result,
            "decision_count": len(decisions),
            "auto_pass_count": sum(1 for d in decisions if d.get('level') == DecisionLevel.A)
        }


# ============================================================
# 元规则：自主决策分级标准
# ============================================================
AUTO_DECISION_METARULE = {
    "rule_id": "META-AUTO-DECISION-V1.0",
    "rule_name": "自主稳态决策分级元规则",
    "description": "达到A级标准的任务自主决策通过，直接执行并通知内核群；B级需人工审批；C级暂缓",
    "scoring_formula": "利益40% + (100-风险)35% + (100-成本)25%",
    "levels": {
        "A": {"min_score": 85, "action": "AUTO_PASS", "notify": "kernel_group"},
        "B": {"min_score": 70, "max_score": 84, "action": "NEED_APPROVAL", "notify": "feishu_approval"},
        "C": {"max_score": 69, "action": "HOLD", "notify": "report_only"}
    },
    "kernel_group_chat_id": KERNEL_CHAT_ID,
    "did": "DID-BR-000002",
    "trace": "Ω₀⊂⊙∞⊂Ω"
}


if __name__ == '__main__':
    # 示例：发送当前状态通知
    notifier = AutoDecisionNotifier()
    
    # 示例决策
    decisions = [
        {"name": "D2-T1批量优化", "desc": "batch 50→200，独立处理器", "level": DecisionLevel.A, "score": 92},
        {"name": "D6-T3仿真模式", "desc": "Soft-TPM替代真实硬件", "level": DecisionLevel.A, "score": 88},
        {"name": "昆仑洞天修复", "desc": "需中枢部署代理执行", "level": DecisionLevel.B, "score": 75},
    ]
    
    system_status = {
        "进化任务": "✅ 21/21 (100%)",
        "D2-T1覆盖率": "✅ 100%",
        "全域锁档": "✅ 区块#1334",
        "部署包": "✅ 7/7上传",
    }
    
    result = notifier.notify(decisions, system_status)
    print(json.dumps(result, ensure_ascii=False, indent=2))
