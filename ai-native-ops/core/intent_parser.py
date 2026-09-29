"""
ANCE 意图解析器
自然语言 → DeploymentPlan 结构化对象
"""
import re
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class DeploymentPlan:
    """部署计划结构化对象"""
    raw_input: str
    cloud_provider: str = "auto"           # tencent / aliyun / aws / auto
    action: str = "deploy"                 # deploy / update / destroy / audit
    resources: List[Dict] = field(default_factory=list)
    software_stack: List[str] = field(default_factory=list)
    domain: Optional[str] = None
    ssl_enabled: bool = False
    ssh_key: Optional[str] = None
    region: str = "auto"
    os: str = "ubuntu22"
    confidence: float = 0.0
    missing_fields: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "cloud_provider": self.cloud_provider,
            "action": self.action,
            "resources": self.resources,
            "software_stack": self.software_stack,
            "domain": self.domain,
            "ssl_enabled": self.ssl_enabled,
            "region": self.region,
            "os": self.os,
            "confidence": self.confidence,
            "missing_fields": self.missing_fields,
        }


# 云厂商关键词映射
CLOUD_KEYWORDS = {
    "tencent": ["腾讯云", "tencent", "qcloud", "腾讯"],
    "aliyun": ["阿里云", "aliyun", "alicloud", "阿里"],
    "aws": ["aws", "amazon", "亚马逊"],
    "huawei": ["华为云", "huawei", "hcloud"],
}

# 软件栈关键词
SOFTWARE_PATTERNS = {
    "nginx": ["nginx", "Nginx", "反向代理", "web服务器"],
    "docker": ["docker", "Docker", "容器"],
    "mysql": ["mysql", "MySQL", "数据库"],
    "redis": ["redis", "Redis", "缓存"],
    "nodejs": ["node", "nodejs", "Node.js"],
    "python": ["python", "Python", "flask", "django", "fastapi"],
    "certbot": ["certbot", "https", "ssl证书", "letsencrypt"],
    "ufw": ["ufw", "防火墙", "firewall"],
    "postgresql": ["postgres", "postgresql", "pg"],
    "mongodb": ["mongo", "mongodb"],
}

# 规格关键词
SPEC_PATTERNS = [
    (r"(\d+)\s*核.*?(\d+)\s*[Gg][Bb]?", "cpu_memory"),
    (r"(\d+)[cC]\s*(\d+)[gG]", "cpu_memory"),
]


class IntentParser:
    """意图解析器"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client  # 可选：豆包API客户端

    def parse(self, text: str) -> DeploymentPlan:
        """解析自然语言为部署计划"""
        plan = DeploymentPlan(raw_input=text)

        # 1. 云厂商识别
        plan.cloud_provider = self._detect_cloud(text)

        # 2. 动作识别
        plan.action = self._detect_action(text)

        # 3. 资源规格提取
        plan.resources = self._extract_resources(text)

        # 4. 软件栈提取
        plan.software_stack = self._extract_software(text)

        # 5. 域名提取
        plan.domain = self._extract_domain(text)

        # 6. SSL识别
        plan.ssl_enabled = self._detect_ssl(text)

        # 7. 区域识别
        plan.region = self._detect_region(text)

        # 8. 置信度评估
        plan.confidence, plan.missing_fields = self._evaluate(plan)

        # 9. 如果有LLM客户端，用LLM增强解析
        if self.llm_client and plan.confidence < 0.7:
            plan = self._llm_enhance(text, plan)

        return plan

    def _detect_cloud(self, text: str) -> str:
        text_lower = text.lower()
        for provider, keywords in CLOUD_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    return provider
        return "auto"

    def _detect_action(self, text: str) -> str:
        if any(w in text for w in ["销毁", "删除", "释放", "destroy", "delete"]):
            return "destroy"
        if any(w in text for w in ["更新", "升级", "修改", "update", "upgrade"]):
            return "update"
        if any(w in text for w in ["审计", "检查", "巡检", "audit", "check"]):
            return "audit"
        return "deploy"

    def _extract_resources(self, text: str) -> List[Dict]:
        resources = []
        for pattern, rtype in SPEC_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                cpu = int(m.group(1))
                memory = int(m.group(2))
                resources.append({
                    "type": "instance",
                    "cpu": cpu,
                    "memory_gb": memory,
                    "disk_gb": 50,  # 默认
                    "count": 1,
                })
                break
        # 磁盘大小
        disk_m = re.search(r"(\d+)\s*[Gg][Bb]?\s*(系统盘|硬盘|磁盘)", text)
        if disk_m and resources:
            resources[0]["disk_gb"] = int(disk_m.group(1))
        # 数量
        count_m = re.search(r"(\d+)\s*台", text)
        if count_m and resources:
            resources[0]["count"] = int(count_m.group(1))
        return resources

    def _extract_software(self, text: str) -> List[str]:
        found = []
        for sw, patterns in SOFTWARE_PATTERNS.items():
            for p in patterns:
                if p.lower() in text.lower():
                    found.append(sw)
                    break
        return found

    def _extract_domain(self, text: str) -> Optional[str]:
        m = re.search(r"([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)", text)
        if m:
            domain = m.group(1)
            # 排除常见非域名词汇
            if not any(domain.endswith(x) for x in [".py", ".sh", ".json", ".yaml", ".md"]):
                return domain
        return None

    def _detect_ssl(self, text: str) -> bool:
        return any(w in text.lower() for w in ["https", "ssl", "证书", "tls", "安全连接"])

    def _detect_region(self, text: str) -> str:
        regions = {
            "ap-guangzhou": ["广州", "guangzhou"],
            "ap-shanghai": ["上海", "shanghai"],
            "ap-beijing": ["北京", "beijing"],
            "ap-shenzhen": ["深圳", "shenzhen"],
            "ap-hongkong": ["香港", "hongkong"],
        }
        for region, kws in regions.items():
            for kw in kws:
                if kw in text.lower():
                    return region
        return "auto"

    def _evaluate(self, plan: DeploymentPlan) -> tuple:
        score = 0.0
        missing = []
        if plan.cloud_provider != "auto":
            score += 0.2
        else:
            missing.append("cloud_provider")
        if plan.resources:
            score += 0.25
        else:
            missing.append("resources")
        if plan.software_stack:
            score += 0.2
        if plan.domain:
            score += 0.15
        else:
            missing.append("domain")
        if plan.ssl_enabled:
            score += 0.1
        if plan.region != "auto":
            score += 0.1
        return min(score, 1.0), missing

    def _llm_enhance(self, text: str, plan: DeploymentPlan) -> DeploymentPlan:
        """用LLM增强解析（需要配置豆包API）"""
        try:
            prompt = f"""解析以下部署需求，输出JSON：
需求：{text}
当前解析：{json.dumps(plan.to_dict(), ensure_ascii=False)}
请补充缺失字段，输出完整JSON：cloud_provider, action, resources, software_stack, domain, ssl_enabled, region"""
            # LLM调用逻辑（需配置API）
            # resp = self.llm_client.chat(prompt)
            # enhanced = json.loads(resp)
            # plan.update(enhanced)
            pass
        except Exception:
            pass
        return plan


# 快捷函数
def parse_intent(text: str, llm_client=None) -> DeploymentPlan:
    parser = IntentParser(llm_client)
    return parser.parse(text)


if __name__ == "__main__":
    # 测试
    test = "帮我在腾讯云广州部署一台2核4G服务器，装好nginx和docker，配置huodouai.com的HTTPS"
    plan = parse_intent(test)
    print(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))
