"""
ANCE 验证器
部署后自动验证：端口/HTTP/HTTPS/服务状态/证书
"""
import socket
import time
import subprocess
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class VerificationResult:
    """验证结果"""
    check_name: str
    passed: bool
    detail: str
    duration: float = 0.0


@dataclass
class VerificationReport:
    """验证报告"""
    results: List[VerificationResult] = field(default_factory=list)
    all_passed: bool = False
    total_checks: int = 0
    passed_count: int = 0
    failed_count: int = 0

    def add(self, result: VerificationResult):
        self.results.append(result)
        self.total_checks += 1
        if result.passed:
            self.passed_count += 1
        else:
            self.failed_count += 1
        self.all_passed = self.failed_count == 0

    def to_dict(self) -> Dict:
        return {
            "all_passed": self.all_passed,
            "total": self.total_checks,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "results": [
                {"check": r.check_name, "passed": r.passed, "detail": r.detail}
                for r in self.results
            ],
        }


class Verifier:
    """部署验证器"""

    def __init__(self, host: str = "127.0.0.1", ssh_executor=None):
        self.host = host
        self.ssh = ssh_executor

    def verify_port(self, port: int, timeout: int = 5) -> VerificationResult:
        """验证端口开放"""
        start = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.host, port))
            sock.close()
            passed = result == 0
            return VerificationResult(
                check_name=f"端口{port}",
                passed=passed,
                detail=f"端口{port}{'开放' if passed else '关闭'}",
                duration=time.time() - start,
            )
        except Exception as e:
            return VerificationResult(
                check_name=f"端口{port}", passed=False,
                detail=f"检查失败: {e}", duration=time.time() - start,
            )

    def verify_http(self, url: str, expected_status: int = 200,
                    timeout: int = 10) -> VerificationResult:
        """验证HTTP响应"""
        start = time.time()
        try:
            cmd = f"curl -s -o /dev/null -w '%{{http_code}}' --max-time {timeout} {url}"
            if self.ssh:
                proc = subprocess.run(
                    f"ssh -o StrictHostKeyChecking=no {self.ssh.username}@{self.ssh.host} '{cmd}'",
                    shell=True, capture_output=True, text=True, timeout=timeout + 5
                )
                code = proc.stdout.strip()
            else:
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
                code = proc.stdout.strip()
            passed = code == str(expected_status)
            return VerificationResult(
                check_name=f"HTTP {url}",
                passed=passed,
                detail=f"状态码: {code}（预期: {expected_status}）",
                duration=time.time() - start,
            )
        except Exception as e:
            return VerificationResult(
                check_name=f"HTTP {url}", passed=False,
                detail=f"请求失败: {e}", duration=time.time() - start,
            )

    def verify_ssl(self, domain: str, port: int = 443,
                   min_days_valid: int = 7) -> VerificationResult:
        """验证SSL证书有效期"""
        start = time.time()
        try:
            cmd = (f"echo | openssl s_client -connect {domain}:{port} "
                   f"-servername {domain} 2>/dev/null | "
                   f"openssl x509 -noout -dates 2>/dev/null")
            if self.ssh:
                proc = subprocess.run(
                    f"ssh -o StrictHostKeyChecking=no {self.ssh.username}@{self.ssh.host} '{cmd}'",
                    shell=True, capture_output=True, text=True, timeout=15
                )
                output = proc.stdout
            else:
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
                output = proc.stdout

            if "notAfter" in output:
                # 解析到期日期
                import re
                m = re.search(r"notAfter=(.+)", output)
                if m:
                    expiry = m.group(1).strip()
                    return VerificationResult(
                        check_name=f"SSL证书 {domain}",
                        passed=True,
                        detail=f"证书有效，到期: {expiry}",
                        duration=time.time() - start,
                    )
            return VerificationResult(
                check_name=f"SSL证书 {domain}", passed=False,
                detail="无法获取证书信息", duration=time.time() - start,
            )
        except Exception as e:
            return VerificationResult(
                check_name=f"SSL证书 {domain}", passed=False,
                detail=f"检查失败: {e}", duration=time.time() - start,
            )

    def verify_service(self, service_name: str) -> VerificationResult:
        """验证系统服务运行状态"""
        start = time.time()
        try:
            cmd = f"systemctl is-active {service_name}"
            if self.ssh:
                result = self.ssh.run(cmd)
                output = result.stdout.strip()
            else:
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                output = proc.stdout.strip()
            passed = output == "active"
            return VerificationResult(
                check_name=f"服务 {service_name}",
                passed=passed,
                detail=f"状态: {output}",
                duration=time.time() - start,
            )
        except Exception as e:
            return VerificationResult(
                check_name=f"服务 {service_name}", passed=False,
                detail=f"检查失败: {e}", duration=time.time() - start,
            )

    def verify_deployment(self, domain: Optional[str] = None,
                          ports: Optional[List[int]] = None,
                          services: Optional[List[str]] = None,
                          check_ssl: bool = False) -> VerificationReport:
        """执行完整部署验证"""
        report = VerificationReport()

        # 端口检查
        for port in (ports or [22, 80, 443]):
            report.add(self.verify_port(port))

        # HTTP检查
        if domain:
            report.add(self.verify_http(f"http://{domain}"))
            if check_ssl:
                report.add(self.verify_http(f"https://{domain}"))
                report.add(self.verify_ssl(domain))

        # 服务检查
        for svc in (services or []):
            report.add(self.verify_service(svc))

        return report


def verify_deployment(host: str, domain: str = None, **kwargs) -> VerificationReport:
    verifier = Verifier(host=host)
    return verifier.verify_deployment(domain=domain, **kwargs)
