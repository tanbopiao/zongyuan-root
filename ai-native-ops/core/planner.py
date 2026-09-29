"""
ANCE 规划器
DeploymentPlan → 执行步骤DAG
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class StepType(Enum):
    CREATE_RESOURCE = "create_resource"
    CONFIGURE_OS = "configure_os"
    INSTALL_SOFTWARE = "install_software"
    CONFIGURE_SERVICE = "configure_service"
    SETUP_DOMAIN = "setup_domain"
    SETUP_SSL = "setup_ssl"
    CONFIGURE_FIREWALL = "configure_firewall"
    VERIFY = "verify"
    DESTROY = "destroy"


@dataclass
class ExecutionStep:
    """执行步骤"""
    step_id: str
    step_type: StepType
    description: str
    depends_on: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    iac_artifact: Optional[str] = None  # terraform/ansible文件路径
    retry_count: int = 2
    timeout: int = 300
    status: str = "pending"  # pending/running/success/failed/skipped


@dataclass
class ExecutionDAG:
    """执行有向无环图"""
    steps: List[ExecutionStep] = field(default_factory=list)

    def get_ready_steps(self) -> List[ExecutionStep]:
        """获取所有可执行步骤（依赖已完成）"""
        done_ids = {s.step_id for s in self.steps if s.status == "success"}
        ready = []
        for s in self.steps:
            if s.status == "pending" and all(d in done_ids for d in s.depends_on):
                ready.append(s)
        return ready

    def is_complete(self) -> bool:
        return all(s.status in ("success", "skipped") for s in self.steps)

    def has_failed(self) -> bool:
        return any(s.status == "failed" for s in self.steps)


class Planner:
    """部署规划器"""

    def __init__(self):
        self.step_counter = 0

    def plan(self, deployment_plan) -> ExecutionDAG:
        """将部署计划转为执行DAG"""
        dag = ExecutionDAG()
        self.step_counter = 0

        if deployment_plan.action == "destroy":
            return self._plan_destroy(deployment_plan, dag)

        # 1. 创建云资源
        if deployment_plan.resources:
            step = self._make_step(
                StepType.CREATE_RESOURCE,
                "创建云服务器实例",
                commands=self._gen_create_commands(deployment_plan),
                iac_artifact="terraform/main.tf",
            )
            dag.steps.append(step)
            create_id = step.step_id
        else:
            create_id = None

        # 2. 系统配置
        step = self._make_step(
            StepType.CONFIGURE_OS,
            "系统初始化配置（更新/时区/用户）",
            commands=self._gen_os_config_commands(),
            iac_artifact="ansible/01-os-setup.yml",
            depends_on=[create_id] if create_id else [],
        )
        dag.steps.append(step)
        os_id = step.step_id

        # 3. 软件安装
        if deployment_plan.software_stack:
            step = self._make_step(
                StepType.INSTALL_SOFTWARE,
                f"安装软件栈：{', '.join(deployment_plan.software_stack)}",
                commands=self._gen_install_commands(deployment_plan.software_stack),
                iac_artifact="ansible/02-install-software.yml",
                depends_on=[os_id],
            )
            dag.steps.append(step)
            install_id = step.step_id
        else:
            install_id = os_id

        # 4. 服务配置
        config_deps = [install_id]
        if "nginx" in deployment_plan.software_stack:
            step = self._make_step(
                StepType.CONFIGURE_SERVICE,
                "配置Nginx反向代理",
                commands=["nginx -t", "systemctl reload nginx"],
                iac_artifact="templates/nginx.conf",
                depends_on=list(config_deps),
            )
            dag.steps.append(step)
            config_deps = config_deps + [step.step_id]

        # 5. 域名配置
        if deployment_plan.domain:
            step = self._make_step(
                StepType.SETUP_DOMAIN,
                f"配置域名解析：{deployment_plan.domain}",
                commands=[f"# DNS配置：{deployment_plan.domain} → 服务器IP"],
                depends_on=config_deps,
            )
            dag.steps.append(step)
            domain_id = step.step_id
        else:
            domain_id = config_deps[-1] if config_deps else os_id

        # 6. SSL配置
        if deployment_plan.ssl_enabled and deployment_plan.domain:
            step = self._make_step(
                StepType.SETUP_SSL,
                f"配置HTTPS证书（Let's Encrypt）：{deployment_plan.domain}",
                commands=[
                    f"certbot --nginx -d {deployment_plan.domain} --non-interactive --agree-tos -m admin@{deployment_plan.domain}",
                    "nginx -t && systemctl reload nginx",
                ],
                depends_on=[domain_id],
            )
            dag.steps.append(step)
            ssl_id = step.step_id
        else:
            ssl_id = domain_id

        # 7. 防火墙
        step = self._make_step(
            StepType.CONFIGURE_FIREWALL,
            "配置防火墙规则（开放80/443/SSH）",
            commands=[
                "ufw allow 80/tcp",
                "ufw allow 443/tcp",
                "ufw allow 22/tcp",
                "ufw --force enable",
            ],
            depends_on=[ssl_id],
        )
        dag.steps.append(step)
        fw_id = step.step_id

        # 8. 验证
        step = self._make_step(
            StepType.VERIFY,
            "部署验证（端口/HTTP/HTTPS/服务状态）",
            commands=[],
            depends_on=[fw_id],
        )
        dag.steps.append(step)

        return dag

    def _plan_destroy(self, plan, dag: ExecutionDAG) -> ExecutionDAG:
        step = self._make_step(
            StepType.DESTROY,
            "销毁云资源",
            commands=["terraform destroy -auto-approve"],
            iac_artifact="terraform/main.tf",
        )
        dag.steps.append(step)
        return dag

    def _make_step(self, step_type: StepType, desc: str, **kwargs) -> ExecutionStep:
        self.step_counter += 1
        return ExecutionStep(
            step_id=f"step-{self.step_counter:03d}",
            step_type=step_type,
            description=desc,
            **kwargs,
        )

    def _gen_create_commands(self, plan) -> List[str]:
        if not plan.resources:
            return []
        r = plan.resources[0]
        return [
            f"# 创建{r['cpu']}核{r['memory_gb']}GB服务器",
            f"terraform apply -auto-approve -var='cpu={r['cpu']}' -var='memory={r['memory_gb']}'",
        ]

    def _gen_os_config_commands(self) -> List[str]:
        return [
            "apt-get update -qq",
            "timedatectl set-timezone Asia/Shanghai",
            "apt-get install -y curl wget git unzip",
        ]

    def _gen_install_commands(self, software: List[str]) -> List[str]:
        cmds = []
        pkg_map = {
            "nginx": "nginx",
            "docker": "docker.io docker-compose",
            "mysql": "mysql-server",
            "redis": "redis-server",
            "nodejs": "nodejs npm",
            "python": "python3 python3-pip python3-venv",
            "certbot": "certbot python3-certbot-nginx",
            "ufw": "ufw",
            "postgresql": "postgresql",
            "mongodb": "mongodb",
        }
        pkgs = [pkg_map[s] for s in software if s in pkg_map]
        if pkgs:
            cmds.append(f"apt-get install -y {' '.join(pkgs)}")
        if "docker" in software:
            cmds.append("systemctl enable --now docker")
        return cmds


def plan_deployment(deployment_plan) -> ExecutionDAG:
    planner = Planner()
    return planner.plan(deployment_plan)
