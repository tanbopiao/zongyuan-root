#!/usr/bin/env python3
"""
L3飞书审批真实连接器
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
将自治引擎L3级操作自动提交飞书审批，审批通过后自动执行
"""
import json
import subprocess
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

class FeishuApprovalConnector:
    """飞书审批连接器 - L3人工审批真实对接"""
    
    APPROVAL_CODE = "CAC2F6DD-B206-4F27-96FF-E99BD13464F7"  # AIOS阶段验收
    USER_ID = "e87749ef"  # 当前用户user_id
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.pending_approvals = self._load_pending()
        
    def _load_config(self, path: str = None) -> dict:
        default = {
            "approval_code": self.APPROVAL_CODE,
            "default_approver": self.USER_ID,
            "auto_approve_l3": False,  # L3不自动批准
            "timeout_hours": 24,
            "approval_templates": {
                "deploy": {"stage": "部署审批", "conclusion": "通过"},
                "config_change": {"stage": "配置变更审批", "conclusion": "通过"},
                "architecture": {"stage": "架构变更审批", "conclusion": "通过"},
                "security": {"stage": "安全策略审批", "conclusion": "通过"},
            }
        }
        if path and os.path.exists(path):
            with open(path) as f:
                default.update(json.load(f))
        return default
    
    def _load_pending(self) -> List[dict]:
        path = os.path.join(os.path.dirname(__file__), '..', 'l3_pending', 'pending_approvals.json')
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return []
    
    def _save_pending(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'l3_pending', 'pending_approvals.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.pending_approvals, f, ensure_ascii=False, indent=2)
    
    def _run_lark_cli(self, cmd: List[str]) -> dict:
        """执行lark-cli命令"""
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout if result.stdout else result.stderr
        try:
            return json.loads(output)
        except:
            return {"ok": False, "error": output[:500]}
    
    def submit_approval(self, operation_type: str, title: str, content: str, 
                       result_link: str = "", risk_score: float = 0.0) -> dict:
        """
        提交L3级审批
        Args:
            operation_type: deploy/config_change/architecture/security
            title: 审批标题
            content: 审批内容（验收项）
            result_link: 成果链接
            risk_score: 风险评分0-1
        Returns:
            {success, instance_code, instance_link, status}
        """
        now = datetime.now(timezone(timedelta(hours=8)))
        start = now.strftime('%Y-%m-%dT%H:%M:%S+08:00')
        end = (now + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S+08:00')
        
        template = self.config["approval_templates"].get(operation_type, 
                   {"stage": title, "conclusion": "通过"})
        
        form = [
            {"id": "widget16457732057390001", "type": "input", "value": f"{template['stage']} - {title}"},
            {"id": "widget16462072487340001", "type": "textarea", "value": content},
            {"id": "widget17890639416310001", "type": "input", "value": result_link},
            {"id": "widget17890619119210001", "type": "textarea", 
             "value": f"风险评分: {risk_score:.1%}\n操作类型: {operation_type}\n由自治引擎L3分级自动提交审批"},
            {"id": "widget17890619390370001", "type": "radioV2", "value": "mtvtab1a-nr5c4s2q49-0"},
            {"id": "widget16462073040250001", "type": "contact", "value": [self.USER_ID]},
            {"id": "widget16457732647360001", "type": "dateInterval", 
             "value": {"start": start, "end": end, "interval": 1.0}},
            {"id": "widget16457743012420001", "type": "contact", "value": [self.USER_ID]},
        ]
        
        payload = {
            "approval_code": self.config["approval_code"],
            "form": json.dumps(form, ensure_ascii=False)
        }
        
        cmd = ["lark-cli", "approval", "instances", "create",
               "--data", json.dumps(payload, ensure_ascii=False),
               "--as", "user", "--yes"]
        
        result = self._run_lark_cli(cmd)
        
        if result.get("ok"):
            data = result["data"]
            approval_record = {
                "instance_code": data.get("instance_code"),
                "instance_link": data.get("instance_link"),
                "title": title,
                "operation_type": operation_type,
                "risk_score": risk_score,
                "submitted_at": now.isoformat(),
                "status": "PENDING",
                "auto_execute_on_approve": True
            }
            self.pending_approvals.append(approval_record)
            self._save_pending()
            return {"success": True, **approval_record}
        else:
            return {"success": False, "error": result.get("error", str(result))}
    
    def check_approval_status(self, instance_code: str) -> dict:
        """查询审批状态"""
        cmd = ["lark-cli", "approval", "instances", "get",
               "--params", json.dumps({"instance_code": instance_code}),
               "--as", "user"]
        result = self._run_lark_cli(cmd)
        if result.get("ok"):
            data = result["data"]
            return {
                "status": data.get("status"),
                "current_nodes": data.get("current_nodes", []),
                "tasks": data.get("tasks", [])
            }
        return {"status": "ERROR", "error": str(result)}
    
    def approve_approval(self, instance_code: str, task_id: str, comment: str = "") -> dict:
        """同意审批（仅用于测试或自动批准场景）"""
        cmd = ["lark-cli", "approval", "tasks", "approve",
               "--data", json.dumps({
                   "instance_code": instance_code,
                   "task_id": task_id,
                   "comment": comment or "自治引擎自动批准"
               }),
               "--as", "user", "--yes"]
        return self._run_lark_cli(cmd)
    
    def sync_pending_approvals(self) -> dict:
        """同步所有待处理审批状态，返回已通过可执行的列表"""
        approved = []
        for record in self.pending_approvals:
            if record["status"] != "PENDING":
                continue
            status = self.check_approval_status(record["instance_code"])
            if status["status"] == "APPROVED":
                record["status"] = "APPROVED"
                record["approved_at"] = datetime.now(timezone.utc).isoformat()
                approved.append(record)
            elif status["status"] == "REJECTED":
                record["status"] = "REJECTED"
        self._save_pending()
        return {"approved": approved, "total_pending": len([r for r in self.pending_approvals if r["status"] == "PENDING"])}
    
    def get_pending_list(self) -> List[dict]:
        """获取待审批列表"""
        return [r for r in self.pending_approvals if r["status"] == "PENDING"]


# 测试
if __name__ == "__main__":
    connector = FeishuApprovalConnector()
    
    # 测试提交审批
    print("=== 测试L3飞书审批连接器 ===")
    result = connector.submit_approval(
        operation_type="deploy",
        title="自治引擎进化部署测试",
        content="测试L3审批连接器：飞书审批真实对接完成",
        result_link="https://aka.doubaocdn.com/s/Qt7GjTL3Yq",
        risk_score=0.72
    )
    print(f"提交结果: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
    
    # 查询待审批
    pending = connector.get_pending_list()
    print(f"\n待审批数: {len(pending)}")
    for p in pending:
        print(f"  - {p['title']} | {p['instance_code']} | {p['status']}")
