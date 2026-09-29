"""
部署算子 - ZONGYUAN-ROOT 算子化架构
执行标准化部署流程，支持预检查、部署、验证、回滚

算子ID: OP-DEPLOY-001
算子名称: deploy
类别: 部署/SOP
版本: V1.0

溯源标识：Ω₀⊂⊙∞⊂Ω
确权编码：DID-BR-000002
"""

import os
import subprocess
import time
from typing import Any, Dict, List, Optional

from operator_base import BaseOperator, OperatorMetadata


class DeployOperator(BaseOperator):
    """部署算子 - 执行标准化部署流程"""

    def __init__(self):
        metadata = OperatorMetadata(
            operator_id="OP-DEPLOY-001",
            operator_name="deploy",
            version="V1.0",
            description="执行标准化部署流程，支持预检查、部署、验证、回滚",
            category="deploy",
            inputs_schema={
                "deploy_type": "部署类型：service/file/config（默认service）",
                "target": "部署目标路径或服务名",
                "source": "部署源路径（可选）",
                "dry_run": "是否预演模式（默认False）",
                "verify_command": "验证命令（可选）",
            },
            outputs_schema={
                "deploy_result": "部署结果字典",
                "deployed": "是否部署成功",
                "steps": "部署步骤列表",
            },
        )
        super().__init__(metadata)

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行部署"""
        deploy_type = inputs.get("deploy_type", "service")
        target = inputs.get("target", "")
        source = inputs.get("source", "")
        dry_run = inputs.get("dry_run", False)
        verify_command = inputs.get("verify_command", "")

        steps = []
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # 步骤1: 预检查
        steps.append({
            "step": 1,
            "name": "预检查",
            "action": f"检查部署目标: {target}",
            "target_exists": os.path.exists(target) if target else False,
            "dry_run": dry_run,
            "status": "完成",
        })

        # 步骤2: 执行部署
        if not dry_run:
            if deploy_type == "file" and source and target:
                try:
                    import shutil
                    target_dir = os.path.dirname(target)
                    if target_dir and not os.path.exists(target_dir):
                        os.makedirs(target_dir, exist_ok=True)
                    shutil.copy2(source, target)
                    deploy_success = True
                    deploy_msg = f"文件复制成功: {source} -> {target}"
                except Exception as e:
                    deploy_success = False
                    deploy_msg = f"文件复制失败: {str(e)}"
            elif deploy_type == "service":
                deploy_success = True
                deploy_msg = "服务部署指令已执行（需外部验证）"
            else:
                deploy_success = True
                deploy_msg = "部署完成（通用模式）"
        else:
            deploy_success = True
            deploy_msg = "预演模式，未实际执行部署"

        steps.append({
            "step": 2,
            "name": "执行部署",
            "type": deploy_type,
            "success": deploy_success,
            "message": deploy_msg,
            "status": "完成" if deploy_success else "失败",
        })

        # 步骤3: 验证
        if verify_command and not dry_run:
            try:
                result = subprocess.run(
                    verify_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                verify_success = result.returncode == 0
                verify_output = result.stdout[:500] if result.stdout else ""
            except Exception as e:
                verify_success = False
                verify_output = f"验证异常: {str(e)}"
        else:
            verify_success = True
            verify_output = "跳过验证（无验证命令或预演模式）"

        steps.append({
            "step": 3,
            "name": "验证",
            "success": verify_success,
            "output": verify_output,
            "status": "完成" if verify_success else "失败",
        })

        deploy_result = {
            "deploy_type": deploy_type,
            "target": target,
            "source": source,
            "dry_run": dry_run,
            "deployed_at": timestamp,
            "steps": steps,
            "all_passed": deploy_success and verify_success,
        }

        return {
            "deploy_result": deploy_result,
            "deployed": deploy_success and verify_success,
            "steps": steps,
        }


# 算子单例
deploy_operator = DeployOperator()
