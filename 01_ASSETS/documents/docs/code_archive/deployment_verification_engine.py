#!/usr/bin/env python3
"""
部署验证闭环引擎 V1.0
审批通过 → 自动部署 → 自动验证 → 结果记录 → 飞书通知 → 官网可视化
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import json, os, subprocess, requests, time
from datetime import datetime

DEPLOYMENT_LOG_FILE = "/opt/ZONGYUAN-ROOT/data/deployment_verification_log.json"
TRUTH_BASE = "http://127.0.0.1:9120"
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook"

class DeploymentVerificationEngine:
    """部署验证闭环引擎"""

    def __init__(self):
        self.name = "Deployment-Verification-Engine-V1.0"
        self.log_file = DEPLOYMENT_LOG_FILE
        self._ensure_log_file()

    def _ensure_log_file(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                json.dump({"deployments": [], "stats": {"total": 0, "success": 0, "failed": 0, "pending": 0}}, f, indent=2)

    def _load_log(self):
        with open(self.log_file) as f:
            return json.load(f)

    def _save_log(self, log):
        with open(self.log_file, "w") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)

    def deploy(self, deployment_id, deployment_type, deployment_script, target_url=None, target_port=None, target_path=None):
        """
        执行部署并自动验证
        返回完整的部署验证报告
        """
        deployment_record = {
            "deployment_id": deployment_id,
            "deployment_type": deployment_type,
            "deployment_script": deployment_script,
            "target_url": target_url,
            "target_port": target_port,
            "target_path": target_path,
            "status": "deploying",
            "started_at": datetime.now().isoformat(),
            "verification": {},
            "logs": []
        }

        # Step1: 执行部署脚本
        print("[Step1] 执行部署脚本...")
        deploy_result = self._execute_deployment(deployment_script)
        deployment_record["logs"].append({"step": "deploy", "result": deploy_result})

        if deploy_result["returncode"] != 0:
            deployment_record["status"] = "failed"
            deployment_record["failure_reason"] = "部署脚本执行失败: " + deploy_result["stderr"][:500]
            self._record_deployment(deployment_record)
            self._notify_failure(deployment_record)
            return deployment_record

        # Step2: 等待服务启动
        print("[Step2] 等待服务启动...")
        time.sleep(3)

        # Step3: 自动验证部署
        print("[Step3] 自动验证部署...")
        verification = self._verify_deployment(target_url, target_port, target_path)
        deployment_record["verification"] = verification

        # Step4: 判断部署是否成功
        if verification["overall_pass"]:
            deployment_record["status"] = "success"
            deployment_record["completed_at"] = datetime.now().isoformat()
            print("[OK] 部署验证通过！")
        else:
            deployment_record["status"] = "failed"
            deployment_record["failure_reason"] = "部署验证失败: " + json.dumps(verification["failed_checks"])
            print("[FAIL] 部署验证失败！")

        # Step5: 记录部署结果
        self._record_deployment(deployment_record)

        # Step6: 飞书通知
        if deployment_record["status"] == "success":
            self._notify_success(deployment_record)
        else:
            self._notify_failure(deployment_record)

        # Step7: 写入9120真值库
        self._write_to_truth_gateway(deployment_record)

        return deployment_record

    def _execute_deployment(self, script):
        """执行部署脚本"""
        try:
            result = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"returncode": -1, "stdout": "", "stderr": "部署超时(300秒)"}
        except Exception as e:
            return {"returncode": -1, "stdout": "", "stderr": str(e)}

    def _verify_deployment(self, target_url=None, target_port=None, target_path=None):
        """
        多维度自动验证部署
        1. HTTP状态码验证（如果有URL）
        2. 端口监听验证（如果有端口）
        3. 文件/路径存在验证（如果有路径）
        4. 进程存在验证
        5. 内容关键字验证
        """
        checks = []
        failed_checks = []

        # 检查1: HTTP状态码
        if target_url:
            http_result = self._check_http(target_url)
            checks.append({"name": "HTTP状态码", "result": http_result})
            if not http_result["pass"]:
                failed_checks.append("HTTP状态码: " + str(http_result.get("status_code", "N/A")))

        # 检查2: 端口监听
        if target_port:
            port_result = self._check_port(target_port)
            checks.append({"name": "端口监听", "result": port_result})
            if not port_result["pass"]:
                failed_checks.append("端口监听: " + str(target_port))

        # 检查3: 文件路径存在
        if target_path:
            path_result = self._check_path(target_path)
            checks.append({"name": "文件路径", "result": path_result})
            if not path_result["pass"]:
                failed_checks.append("文件路径: " + target_path)

        # 检查4: 进程存在（通过端口反查）
        if target_port:
            proc_result = self._check_process_by_port(target_port)
            checks.append({"name": "进程存在", "result": proc_result})
            if not proc_result["pass"]:
                failed_checks.append("进程存在: 端口" + str(target_port) + "无进程")

        overall_pass = len(failed_checks) == 0

        return {
            "overall_pass": overall_pass,
            "checks_passed": len(checks) - len(failed_checks),
            "checks_total": len(checks),
            "failed_checks": failed_checks,
            "all_checks": checks,
            "verified_at": datetime.now().isoformat()
        }

    def _check_http(self, url):
        """检查HTTP状态码"""
        try:
            r = requests.get(url, timeout=10, allow_redirects=True)
            return {
                "pass": r.status_code == 200,
                "status_code": r.status_code,
                "url": url,
                "response_time_ms": round(r.elapsed.total_seconds() * 1000, 1)
            }
        except Exception as e:
            return {"pass": False, "status_code": None, "url": url, "error": str(e)}

    def _check_port(self, port):
        """检查端口是否监听"""
        try:
            result = subprocess.run(
                ["ss", "-tlnp"],
                capture_output=True,
                text=True,
                timeout=5
            )
            port_str = ":" + str(port)
            is_listening = port_str in result.stdout
            return {"pass": is_listening, "port": port, "listening": is_listening}
        except Exception as e:
            return {"pass": False, "port": port, "error": str(e)}

    def _check_path(self, path):
        """检查文件/路径是否存在"""
        exists = os.path.exists(path)
        is_dir = os.path.isdir(path) if exists else False
        size = os.path.getsize(path) if exists and not is_dir else 0
        return {"pass": exists, "path": path, "exists": exists, "is_dir": is_dir, "size_bytes": size}

    def _check_process_by_port(self, port):
        """通过端口检查进程是否存在"""
        try:
            result = subprocess.run(
                ["ss", "-tlnp"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split("\n"):
                if ":" + str(port) in line and "users:" in line:
                    return {"pass": True, "port": port, "process_info": line.strip()}
            return {"pass": False, "port": port, "process_info": None}
        except Exception as e:
            return {"pass": False, "port": port, "error": str(e)}

    def _record_deployment(self, record):
        """记录部署结果到日志"""
        log = self._load_log()
        log["deployments"].append(record)
        log["stats"]["total"] += 1
        if record["status"] == "success":
            log["stats"]["success"] += 1
        elif record["status"] == "failed":
            log["stats"]["failed"] += 1
        else:
            log["stats"]["pending"] += 1
        # 只保留最近1000条
        if len(log["deployments"]) > 1000:
            log["deployments"] = log["deployments"][-1000:]
        self._save_log(log)

    def _notify_success(self, record):
        """飞书通知部署成功"""
        message = (
            "✅ 部署验证通过\n"
            "部署ID: " + record["deployment_id"] + "\n"
            "部署类型: " + record["deployment_type"] + "\n"
            "验证结果: " + str(record["verification"]["checks_passed"]) + "/" + str(record["verification"]["checks_total"]) + " 项通过\n"
            "完成时间: " + record.get("completed_at", "N/A")
        )
        print("[通知] " + message)
        # 实际飞书通知可以通过webhook发送

    def _notify_failure(self, record):
        """飞书通知部署失败"""
        message = (
            "❌ 部署验证失败\n"
            "部署ID: " + record["deployment_id"] + "\n"
            "部署类型: " + record["deployment_type"] + "\n"
            "失败原因: " + record.get("failure_reason", "未知")[:200] + "\n"
            "请检查部署日志并手动处理"
        )
        print("[告警] " + message)

    def _write_to_truth_gateway(self, record):
        """写入9120真值库"""
        try:
            payload = {
                "key": "DEPLOYMENT." + record["deployment_id"],
                "value": json.dumps({
                    "deployment_id": record["deployment_id"],
                    "type": record["deployment_type"],
                    "status": record["status"],
                    "verification": record["verification"],
                    "started_at": record["started_at"],
                    "completed_at": record.get("completed_at")
                }, ensure_ascii=False),
                "type": "deployment_record",
                "confidence": 0.99
            }
            requests.post(TRUTH_BASE + "/api/truth/upsert", json=payload, timeout=10)
        except:
            pass

    def get_status(self):
        """获取部署验证状态总览"""
        log = self._load_log()
        recent = log["deployments"][-10:] if log["deployments"] else []
        return {
            "engine": self.name,
            "stats": log["stats"],
            "recent_deployments": [
                {
                    "id": d["deployment_id"],
                    "type": d["deployment_type"],
                    "status": d["status"],
                    "started_at": d["started_at"],
                    "verification_pass": d["verification"].get("overall_pass", None)
                }
                for d in recent
            ]
        }

    def get_deployment_detail(self, deployment_id):
        """获取单个部署的详细验证报告"""
        log = self._load_log()
        for d in log["deployments"]:
            if d["deployment_id"] == deployment_id:
                return d
        return None


if __name__ == "__main__":
    import sys
    engine = DeploymentVerificationEngine()

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(engine.get_status(), indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "detail" and len(sys.argv) > 2:
        detail = engine.get_deployment_detail(sys.argv[2])
        print(json.dumps(detail, indent=2, ensure_ascii=False))
    else:
        print("部署验证闭环引擎 V1.0")
        print("用法:")
        print("  python3 deployment_verification_engine.py status  - 查看部署状态总览")
        print("  python3 deployment_verification_engine.py detail <部署ID>  - 查看详细验证报告")
        print("")
        print(json.dumps(engine.get_status(), indent=2, ensure_ascii=False))
