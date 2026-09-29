"""
ANCE 修复引擎
错误模式匹配 → 修复策略 → 自动修复重试
"""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable


@dataclass
class ErrorPattern:
    """错误模式"""
    pattern: str           # 正则匹配错误信息
    name: str              # 错误名称
    severity: str = "P2"   # P0/P1/P2/P3
    fix_commands: List[str] = field(default_factory=list)
    fix_description: str = ""


@dataclass
class FixResult:
    """修复结果"""
    error_name: str
    severity: str
    fixed: bool
    fix_commands: List[str]
    detail: str


# 预定义错误模式库
ERROR_PATTERNS = [
    ErrorPattern(
        pattern=r"Connection refused|Connection timed out|No route to host",
        name="网络连接失败",
        severity="P1",
        fix_commands=[
            "iptables -L -n | grep -E '80|443|22'",
            "ufw status",
            "iptables -I INPUT -p tcp --dport 80 -j ACCEPT",
            "iptables -I INPUT -p tcp --dport 443 -j ACCEPT",
        ],
        fix_description="检查并开放防火墙端口",
    ),
    ErrorPattern(
        pattern=r"nginx: \[emerg\]|nginx.*failed",
        name="Nginx配置错误",
        severity="P1",
        fix_commands=[
            "nginx -t",
            "cat /var/log/nginx/error.log | tail -20",
        ],
        fix_description="检查Nginx配置语法和错误日志",
    ),
    ErrorPattern(
        pattern=r"Permission denied|permission denied",
        name="权限不足",
        severity="P2",
        fix_commands=[
            "chown -R www-data:www-data /www/wwwroot/",
            "chmod -R 755 /www/wwwroot/",
        ],
        fix_description="修复文件权限",
    ),
    ErrorPattern(
        pattern=r"Address already in use|port.*already in use",
        name="端口被占用",
        severity="P1",
        fix_commands=[
            "ss -tlnp | grep -E '80|443|8000|8001'",
            "lsof -i :80",
        ],
        fix_description="查找并释放占用端口的进程",
    ),
    ErrorPattern(
        pattern=r"certbot.*failed|Failed to authenticate",
        name="SSL证书申请失败",
        severity="P2",
        fix_commands=[
            "cat /var/log/letsencrypt/letsencrypt.log | tail -30",
            "nginx -t",
            "systemctl status nginx",
        ],
        fix_description="检查域名解析和Nginx配置后重试certbot",
    ),
    ErrorPattern(
        pattern=r"No space left on device",
        name="磁盘空间不足",
        severity="P0",
        fix_commands=[
            "df -h",
            "du -sh /var/log/* | sort -rh | head -10",
            "journalctl --vacuum-size=100M",
            "apt-get clean",
        ],
        fix_description="清理日志和缓存释放空间",
    ),
    ErrorPattern(
        pattern=r"Out of memory|Cannot allocate memory|OOM",
        name="内存不足",
        severity="P0",
        fix_commands=[
            "free -h",
            "ps aux --sort=-%mem | head -10",
            "swapoff -a && swapon -a",
        ],
        fix_description="检查内存占用，考虑增加Swap或升级配置",
    ),
    ErrorPattern(
        pattern=r"502 Bad Gateway|503 Service Unavailable",
        name="后端服务不可用",
        severity="P1",
        fix_commands=[
            "systemctl status nginx",
            "ss -tlnp | grep -E '8000|8001|3000|5000'",
            "journalctl -u nginx --no-pager | tail -20",
        ],
        fix_description="检查后端服务是否运行，端口是否正确",
    ),
    ErrorPattern(
        pattern=r"proxy_pass.*404|location.*not found",
        name="Nginx代理路径错误",
        severity="P2",
        fix_commands=[
            "grep -n 'proxy_pass' /www/server/panel/vhost/nginx/*.conf",
            "# 检查proxy_pass是否带尾部斜杠（会剥离路径前缀）",
        ],
        fix_description="修正proxy_pass路径，去掉尾部斜杠保留完整路径",
    ),
    ErrorPattern(
        pattern=r"SSL certificate problem|certificate has expired",
        name="SSL证书过期",
        severity="P1",
        fix_commands=[
            "certbot renew --dry-run",
            "certbot renew",
            "nginx -s reload",
        ],
        fix_description="续期SSL证书并重载Nginx",
    ),
]


class Healer:
    """自动修复引擎"""

    def __init__(self, executor=None, llm_client=None):
        self.executor = executor
        self.llm_client = llm_client
        self.patterns = ERROR_PATTERNS
        self.fix_history: List[FixResult] = []

    def diagnose(self, error_text: str) -> List[ErrorPattern]:
        """诊断错误，匹配模式"""
        matched = []
        for pattern in self.patterns:
            if re.search(pattern.pattern, error_text, re.IGNORECASE):
                matched.append(pattern)
        return matched

    def heal(self, error_text: str, context: Optional[Dict] = None) -> List[FixResult]:
        """执行自动修复"""
        results = []
        matched = self.diagnose(error_text)

        if not matched:
            # 未匹配到预定义模式，尝试LLM诊断
            if self.llm_client:
                llm_fix = self._llm_diagnose(error_text, context)
                if llm_fix:
                    results.append(llm_fix)
            else:
                results.append(FixResult(
                    error_name="未识别错误",
                    severity="P3",
                    fixed=False,
                    fix_commands=[],
                    detail="未匹配到预定义错误模式，建议人工检查",
                ))
            return results

        for pattern in matched:
            fix_result = self._apply_fix(pattern)
            results.append(fix_result)
            self.fix_history.append(fix_result)

        return results

    def _apply_fix(self, pattern: ErrorPattern) -> FixResult:
        """应用修复策略"""
        if not self.executor:
            return FixResult(
                error_name=pattern.name,
                severity=pattern.severity,
                fixed=False,
                fix_commands=pattern.fix_commands,
                detail=f"修复命令已生成（未执行）：{pattern.fix_description}",
            )

        # 执行修复命令
        all_success = True
        details = []
        for cmd in pattern.fix_commands:
            if self.executor.ssh:
                result = self.executor.ssh.run(cmd)
            else:
                result = self.executor.local.run(cmd)
            details.append(f"$ {cmd}\n{result.stdout}\n{result.stderr}")
            if not result.success:
                all_success = False

        return FixResult(
            error_name=pattern.name,
            severity=pattern.severity,
            fixed=all_success,
            fix_commands=pattern.fix_commands,
            detail=pattern.fix_description + "\n" + "\n".join(details),
        )

    def _llm_diagnose(self, error_text: str, context: Optional[Dict]) -> Optional[FixResult]:
        """LLM增强诊断（需配置API）"""
        try:
            prompt = f"""诊断以下部署错误，给出修复命令：
错误：{error_text}
上下文：{context or '无'}
输出JSON：{{"error_name": "", "severity": "P0-P3", "fix_commands": [], "description": ""}}"""
            # LLM调用
            # resp = self.llm_client.chat(prompt)
            # data = json.loads(resp)
            # return FixResult(...)
            return None
        except Exception:
            return None

    def get_fix_summary(self) -> Dict:
        return {
            "total_fixes": len(self.fix_history),
            "successful": sum(1 for f in self.fix_history if f.fixed),
            "by_severity": {
                sev: sum(1 for f in self.fix_history if f.severity == sev)
                for sev in ["P0", "P1", "P2", "P3"]
            },
        }
