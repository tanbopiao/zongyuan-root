#!/usr/bin/env python3
"""
EMMS自动化评估工具 V1.0 (基础版)
Engineering Maturity Measurement Standard - Auto Assessor

功能：
1. 代码扫描：分析代码结构、测试覆盖率、文档完整性
2. 部署探测：检查Dockerfile、docker-compose、部署文档
3. 安全检查：API key暴露、认证机制、依赖漏洞提示
4. 接口分析：API设计规范性、文档完整性
5. EMMS评级：八维度评分+综合等级+改进建议

用法：
  python3 emms-auto-assessor.py --path /path/to/project
  python3 emms-auto-assessor.py --path /path/to/project --output report.json
  python3 emms-auto-assessor.py --path /path/to/project --format html

确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import os
import re
import json
import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict


class EMMSAssessor:
    """EMMS自动化评估器"""

    # EMMS等级定义
    LEVELS = {
        (0, 2.0): ("E1", "概念级", "仅有概念或想法，无实际代码"),
        (2.0, 3.5): ("E2", "原型级", "有基础原型代码，功能不完整，不可部署"),
        (3.5, 5.5): ("E3", "演示级", "可演示核心功能，部署复杂，稳定性差，不适合生产"),
        (5.5, 7.0): ("E4", "试用级", "可部署试用，基本稳定，有简单运维，适合小范围试用"),
        (7.0, 8.0): ("E5", "生产级", "可生产部署，稳定可靠，运维完善，安全达标"),
        (8.0, 9.0): ("E6", "规模化级", "支持大规模部署，高可用，自动化运维，多租户"),
        (9.0, 9.5): ("E7", "平台级", "平台化架构，生态完善，标准化程度高，行业标杆"),
        (9.5, 10.1): ("E8", "工业化级", "工业化标准，全自动化，零运维，行业基础设施"),
    }

    # 维度权重
    DIMENSION_WEIGHTS = {
        "code_completeness": 0.15,
        "deployability": 0.15,
        "stability": 0.15,
        "operability": 0.10,
        "api_standardization": 0.15,
        "data_persistence": 0.10,
        "security": 0.10,
        "scalability": 0.10,
    }

    DIMENSION_NAMES = {
        "code_completeness": "代码实现完整度",
        "deployability": "部署可用性",
        "stability": "系统稳定性",
        "operability": "可运维性",
        "api_standardization": "接口标准化",
        "data_persistence": "数据持久化",
        "security": "安全性",
        "scalability": "可扩展性",
    }

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.results = {}
        self.evidence = defaultdict(list)
        self.warnings = []

    def assess(self):
        """执行完整评估"""
        if not self.project_path.exists():
            raise FileNotFoundError(f"项目路径不存在: {self.project_path}")

        print(f"[EMMS] 开始评估: {self.project_path}")
        print(f"[EMMS] 评估时间: {datetime.now().isoformat()}")
        print()

        # 八大维度评估
        self.results["code_completeness"] = self._assess_code_completeness()
        self.results["deployability"] = self._assess_deployability()
        self.results["stability"] = self._assess_stability()
        self.results["operability"] = self._assess_operability()
        self.results["api_standardization"] = self._assess_api_standardization()
        self.results["data_persistence"] = self._assess_data_persistence()
        self.results["security"] = self._assess_security()
        self.results["scalability"] = self._assess_scalability()

        # 计算综合评分
        total_score = sum(
            self.results[dim]["score"] * self.DIMENSION_WEIGHTS[dim]
            for dim in self.DIMENSION_WEIGHTS
        )
        self.results["total_score"] = round(total_score, 2)

        # 确定等级
        self.results["level"] = self._get_level(total_score)

        # 生成改进建议
        self.results["recommendations"] = self._generate_recommendations()

        # 元数据
        self.results["metadata"] = {
            "project_path": str(self.project_path),
            "assess_time": datetime.now().isoformat(),
            "emms_version": "1.0",
            "assessor": "EMMS-Auto-Assessor-V1.0",
            "project_hash": self._calculate_project_hash(),
            "did": "DID-BR-000002",
            "trace_mark": "Ω₀⊂⊙∞⊂Ω",
        }

        print()
        print(f"[EMMS] 评估完成")
        print(f"[EMMS] 综合评分: {self.results['total_score']}/10")
        print(f"[EMMS] EMMS等级: {self.results['level']['code']} {self.results['level']['name']}")
        print(f"[EMMS] 警告数: {len(self.warnings)}")

        return self.results

    def _assess_code_completeness(self):
        """评估代码实现完整度"""
        score = 0
        details = []

        # 1. 代码文件数量和结构
        code_files = list(self.project_path.rglob("*.py")) + \
                     list(self.project_path.rglob("*.js")) + \
                     list(self.project_path.rglob("*.ts")) + \
                     list(self.project_path.rglob("*.go")) + \
                     list(self.project_path.rglob("*.java"))
        code_count = len(code_files)

        if code_count > 100:
            score += 2
            details.append(f"代码文件丰富({code_count}个)")
        elif code_count > 20:
            score += 1.5
            details.append(f"代码文件适中({code_count}个)")
        elif code_count > 5:
            score += 1
            details.append(f"代码文件较少({code_count}个)")
        else:
            details.append(f"代码文件极少({code_count}个)")
        self.evidence["code_completeness"].append(f"代码文件数: {code_count}")

        # 2. 测试文件
        test_files = list(self.project_path.rglob("test_*.py")) + \
                      list(self.project_path.rglob("*_test.py")) + \
                      list(self.project_path.rglob("*.test.js")) + \
                      list(self.project_path.rglob("*.spec.js"))
        test_count = len(test_files)

        if test_count > 20:
            score += 2
            details.append("测试覆盖完善")
        elif test_count > 5:
            score += 1.5
            details.append("有一定测试覆盖")
        elif test_count > 0:
            score += 1
            details.append("有基础测试")
        else:
            details.append("无测试文件")
        self.evidence["code_completeness"].append(f"测试文件数: {test_count}")

        # 3. 文档完整性
        doc_files = list(self.project_path.rglob("README*")) + \
                    list(self.project_path.rglob("docs")) + \
                    list(self.project_path.rglob("*.md"))
        has_readme = any("README" in f.name for f in self.project_path.glob("*"))
        has_docs_dir = (self.project_path / "docs").exists()

        if has_readme and has_docs_dir:
            score += 2
            details.append("文档完善(README+docs目录)")
        elif has_readme:
            score += 1.5
            details.append("有README文档")
        elif doc_files:
            score += 1
            details.append("有部分文档")
        else:
            details.append("无文档")
        self.evidence["code_completeness"].append(f"文档文件数: {len(doc_files)}")

        # 4. 代码结构(模块化)
        has_src = (self.project_path / "src").exists()
        has_lib = (self.project_path / "lib").exists()
        has_packages = any(d.is_dir() and not d.name.startswith('.') for d in self.project_path.iterdir())

        if has_src or has_lib:
            score += 2
            details.append("代码结构清晰(模块化)")
        elif has_packages:
            score += 1.5
            details.append("有基本代码组织")
        else:
            score += 0.5
            details.append("代码结构混乱")

        # 5. CI/CD配置
        has_ci = (self.project_path / ".github" / "workflows").exists() or \
                 (self.project_path / ".gitlab-ci.yml").exists() or \
                 (self.project_path / "Jenkinsfile").exists()

        if has_ci:
            score += 2
            details.append("有CI/CD配置")
        else:
            details.append("无CI/CD配置")

        score = min(score, 10)
        return {"score": score, "details": details, "evidence": self.evidence["code_completeness"]}

    def _assess_deployability(self):
        """评估部署可用性"""
        score = 0
        details = []

        # 1. Docker支持
        has_dockerfile = (self.project_path / "Dockerfile").exists()
        has_docker_compose = (self.project_path / "docker-compose.yml").exists() or \
                              (self.project_path / "docker-compose.yaml").exists()

        if has_dockerfile and has_docker_compose:
            score += 3
            details.append("Dockerfile+docker-compose完整")
        elif has_dockerfile:
            score += 2
            details.append("有Dockerfile")
        else:
            details.append("无Docker支持")
        self.evidence["deployability"].append(f"Dockerfile: {has_dockerfile}, docker-compose: {has_docker_compose}")

        # 2. 依赖管理
        has_requirements = (self.project_path / "requirements.txt").exists()
        has_pyproject = (self.project_path / "pyproject.toml").exists()
        has_package_json = (self.project_path / "package.json").exists()
        has_go_mod = (self.project_path / "go.mod").exists()

        if any([has_requirements, has_pyproject, has_package_json, has_go_mod]):
            score += 2
            details.append("有依赖管理文件")
        else:
            details.append("无依赖管理")
        self.evidence["deployability"].append(f"依赖管理: requirements={has_requirements}, pyproject={has_pyproject}, package.json={has_package_json}")

        # 3. 环境配置
        has_env_example = (self.project_path / ".env.example").exists() or \
                           (self.project_path / ".env.template").exists()
        has_config = (self.project_path / "config").exists() or \
                     any(self.project_path.glob("config.*"))

        if has_env_example and has_config:
            score += 2
            details.append("环境配置完善(.env.example+config)")
        elif has_env_example or has_config:
            score += 1.5
            details.append("有基本环境配置")
        else:
            details.append("无环境配置模板")

        # 4. 部署文档
        deploy_docs = []
        for pattern in ["*deploy*", "*installation*", "*setup*", "*quickstart*"]:
            deploy_docs.extend(list(self.project_path.rglob(pattern)))

        if deploy_docs:
            score += 2
            details.append(f"有部署文档({len(deploy_docs)}个)")
        else:
            details.append("无专门部署文档")

        # 5. 一键部署脚本
        has_install_script = (self.project_path / "install.sh").exists() or \
                              (self.project_path / "setup.sh").exists() or \
                              (self.project_path / "Makefile").exists()

        if has_install_script:
            score += 1
            details.append("有一键部署脚本")

        score = min(score, 10)
        return {"score": score, "details": details, "evidence": self.evidence["deployability"]}

    def _assess_stability(self):
        """评估系统稳定性"""
        score = 0
        details = []

        # 1. 错误处理
        error_patterns = ["try:", "except", "catch", "throw", "raise", "error handling"]
        error_count = 0
        for code_file in list(self.project_path.rglob("*.py"))[:50] + list(self.project_path.rglob("*.js"))[:50]:
            try:
                content = code_file.read_text(errors="ignore")
                error_count += sum(1 for p in error_patterns if p in content)
            except:
                pass

        if error_count > 50:
            score += 2
            details.append("错误处理完善")
        elif error_count > 10:
            score += 1.5
            details.append("有一定错误处理")
        elif error_count > 0:
            score += 1
            details.append("有基础错误处理")
        else:
            details.append("无错误处理")
        self.evidence["stability"].append(f"错误处理模式数: {error_count}")

        # 2. 重试机制
        retry_patterns = ["retry", "backoff", "重试"]
        has_retry = False
        for code_file in list(self.project_path.rglob("*.py"))[:30] + list(self.project_path.rglob("*.js"))[:30]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in retry_patterns):
                    has_retry = True
                    break
            except:
                pass

        if has_retry:
            score += 2
            details.append("有重试/退避机制")
        else:
            details.append("无重试机制")

        # 3. 健康检查
        health_patterns = ["health", "healthcheck", "ping", "ready"]
        has_health = False
        for code_file in list(self.project_path.rglob("*.py"))[:30] + list(self.project_path.rglob("*.js"))[:30]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in health_patterns):
                    has_health = True
                    break
            except:
                pass

        if has_health:
            score += 2
            details.append("有健康检查端点")
        else:
            details.append("无健康检查")

        # 4. 配置验证
        config_validation = ["pydantic", "schema", "validate", "校验"]
        has_validation = False
        for code_file in list(self.project_path.rglob("*.py"))[:30]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in config_validation):
                    has_validation = True
                    break
            except:
                pass

        if has_validation:
            score += 2
            details.append("有配置/输入验证")
        else:
            details.append("无配置验证")

        # 5. 优雅关闭
        shutdown_patterns = ["signal", "atexit", "shutdown", "graceful"]
        has_shutdown = False
        for code_file in list(self.project_path.rglob("*.py"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in shutdown_patterns):
                    has_shutdown = True
                    break
            except:
                pass

        if has_shutdown:
            score += 2
            details.append("有优雅关闭机制")
        else:
            details.append("无优雅关闭")

        score = min(score, 10)
        return {"score": score, "details": details, "evidence": self.evidence["stability"]}

    def _assess_operability(self):
        """评估可运维性"""
        score = 0
        details = []

        # 1. 日志系统
        log_patterns = ["logging", "logger", "winston", "log4j", "zap", "日志"]
        has_logging = False
        for code_file in list(self.project_path.rglob("*.py"))[:20] + list(self.project_path.rglob("*.js"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in log_patterns):
                    has_logging = True
                    break
            except:
                pass

        if has_logging:
            score += 3
            details.append("有日志系统")
        else:
            details.append("无结构化日志")
        self.evidence["operability"].append(f"日志系统: {has_logging}")

        # 2. 监控指标
        metrics_patterns = ["prometheus", "metrics", "monitor", "statsd", "监控"]
        has_metrics = False
        for code_file in list(self.project_path.rglob("*.py"))[:20] + list(self.project_path.rglob("*.js"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in metrics_patterns):
                    has_metrics = True
                    break
            except:
                pass

        if has_metrics:
            score += 3
            details.append("有监控指标")
        else:
            details.append("无监控指标")

        # 3. 告警机制
        alert_patterns = ["alert", "webhook", "notification", "告警", "通知"]
        has_alert = False
        for code_file in list(self.project_path.rglob("*.py"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in alert_patterns):
                    has_alert = True
                    break
            except:
                pass

        if has_alert:
            score += 2
            details.append("有告警/通知机制")
        else:
            details.append("无告警机制")

        # 4. 管理后台
        admin_patterns = ["admin", "dashboard", "管理后台", "控制台"]
        has_admin = False
        for code_file in list(self.project_path.rglob("*.py"))[:30] + list(self.project_path.rglob("*.html"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in admin_patterns):
                    has_admin = True
                    break
            except:
                pass

        if has_admin:
            score += 2
            details.append("有管理后台/仪表盘")
        else:
            details.append("无管理后台")

        score = min(score, 10)
        return {"score": score, "details": details, "evidence": self.evidence["operability"]}

    def _assess_api_standardization(self):
        """评估接口标准化"""
        score = 0
        details = []

        # 1. API文档
        api_docs = list(self.project_path.rglob("openapi*")) + \
                   list(self.project_path.rglob("swagger*")) + \
                   list(self.project_path.rglob("*api*.md")) + \
                   list(self.project_path.rglob("*API*"))
        has_api_doc = len(api_docs) > 0

        if has_api_doc:
            score += 3
            details.append(f"有API文档({len(api_docs)}个)")
        else:
            details.append("无API文档")
        self.evidence["api_standardization"].append(f"API文档数: {len(api_docs)}")

        # 2. RESTful设计
        rest_patterns = ["@app.route", "@router", "express", "fastapi", "flask", "gin", "REST"]
        has_rest = False
        for code_file in list(self.project_path.rglob("*.py"))[:30] + list(self.project_path.rglob("*.js"))[:30]:
            try:
                content = code_file.read_text(errors="ignore")
                if any(p in content for p in rest_patterns):
                    has_rest = True
                    break
            except:
                pass

        if has_rest:
            score += 2
            details.append("有RESTful API框架")
        else:
            details.append("无标准API框架")

        # 3. SDK支持
        sdk_dirs = ["sdk", "client", "clients"]
        has_sdk = any((self.project_path / d).exists() for d in sdk_dirs)
        if has_sdk:
            score += 2
            details.append("有官方SDK")
        else:
            details.append("无官方SDK")

        # 4. 版本管理
        version_patterns = ["/v1/", "/v2/", "api_version", "versioning"]
        has_version = False
        for code_file in list(self.project_path.rglob("*.py"))[:20]:
            try:
                content = code_file.read_text(errors="ignore")
                if any(p in content for p in version_patterns):
                    has_version = True
                    break
            except:
                pass

        if has_version:
            score += 2
            details.append("有API版本管理")
        else:
            details.append("无API版本管理")

        # 5. 错误码规范
        error_code_patterns = ["error_code", "status_code", "HTTPException", "ApiError"]
        has_error_code = False
        for code_file in list(self.project_path.rglob("*.py"))[:20]:
            try:
                content = code_file.read_text(errors="ignore")
                if any(p in content for p in error_code_patterns):
                    has_error_code = True
                    break
            except:
                pass

        if has_error_code:
            score += 1
            details.append("有错误码规范")

        score = min(score, 10)
        return {"score": score, "details": details, "evidence": self.evidence["api_standardization"]}

    def _assess_data_persistence(self):
        """评估数据持久化"""
        score = 0
        details = []

        # 1. 数据库支持
        db_patterns = ["postgres", "mysql", "mongodb", "redis", "sqlite", "数据库"]
        has_db = False
        for code_file in list(self.project_path.rglob("*.py"))[:30] + list(self.project_path.rglob("*.js"))[:30]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in db_patterns):
                    has_db = True
                    break
            except:
                pass

        # 检查docker-compose中的数据库
        if not has_db and (self.project_path / "docker-compose.yml").exists():
            try:
                content = (self.project_path / "docker-compose.yml").read_text().lower()
                if any(p in content for p in ["postgres", "mysql", "mongo", "redis"]):
                    has_db = True
            except:
                pass

        if has_db:
            score += 4
            details.append("有数据库支持")
        else:
            details.append("无数据库支持")
        self.evidence["data_persistence"].append(f"数据库: {has_db}")

        # 2. ORM/数据层
        orm_patterns = ["sqlalchemy", "django.db", "prisma", "typeorm", "mongoose", "gorm"]
        has_orm = False
        for code_file in list(self.project_path.rglob("*.py"))[:20] + list(self.project_path.rglob("*.js"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in orm_patterns):
                    has_orm = True
                    break
            except:
                pass

        if has_orm:
            score += 2
            details.append("有ORM/数据访问层")
        else:
            details.append("无ORM")

        # 3. 数据迁移
        migration_patterns = ["alembic", "migrate", "migration", "flyway"]
        has_migration = False
        for code_file in list(self.project_path.rglob("*.py"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in migration_patterns):
                    has_migration = True
                    break
            except:
                pass
        # 检查迁移目录
        if (self.project_path / "migrations").exists():
            has_migration = True

        if has_migration:
            score += 2
            details.append("有数据迁移机制")
        else:
            details.append("无数据迁移")

        # 4. 备份方案
        backup_patterns = ["backup", "dump", "备份"]
        has_backup = False
        for code_file in list(self.project_path.rglob("*.sh"))[:10] + list(self.project_path.rglob("*.md"))[:10]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in backup_patterns):
                    has_backup = True
                    break
            except:
                pass

        if has_backup:
            score += 2
            details.append("有数据备份方案")
        else:
            details.append("无备份方案")

        score = min(score, 10)
        return {"score": score, "details": details, "evidence": self.evidence["data_persistence"]}

    def _assess_security(self):
        """评估安全性"""
        score = 0
        details = []

        # 1. 认证授权
        auth_patterns = ["jwt", "oauth", "auth", "login", "token", "认证", "授权"]
        has_auth = False
        for code_file in list(self.project_path.rglob("*.py"))[:30] + list(self.project_path.rglob("*.js"))[:30]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in auth_patterns):
                    has_auth = True
                    break
            except:
                pass

        if has_auth:
            score += 3
            details.append("有认证授权机制")
        else:
            details.append("无认证授权")
        self.evidence["security"].append(f"认证授权: {has_auth}")

        # 2. API key安全检查(检测硬编码)
        api_key_patterns = [
            r'sk-[a-zA-Z0-9]{20,}',
            r'api[_-]?key\s*=\s*["\'][a-zA-Z0-9]{10,}["\']',
            r'secret\s*=\s*["\'][a-zA-Z0-9]{10,}["\']',
            r'password\s*=\s*["\'][^"\']{6,}["\']',
        ]
        hardcoded_keys = []
        for code_file in list(self.project_path.rglob("*.py"))[:30] + list(self.project_path.rglob("*.js"))[:30] + list(self.project_path.rglob("*.env*")):
            try:
                content = code_file.read_text(errors="ignore")
                for pattern in api_key_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        hardcoded_keys.append((str(code_file), len(matches)))
            except:
                pass

        if hardcoded_keys:
            score += 0
            details.append(f"⚠️ 检测到{len(hardcoded_keys)}处疑似硬编码密钥")
            self.warnings.append(f"检测到硬编码密钥: {hardcoded_keys[:3]}")
        else:
            score += 2
            details.append("无硬编码密钥")
        self.evidence["security"].append(f"硬编码密钥: {len(hardcoded_keys)}处")

        # 3. HTTPS/TLS
        tls_patterns = ["https", "ssl", "tls", "certificate"]
        has_tls = False
        for code_file in list(self.project_path.rglob("*.py"))[:20] + list(self.project_path.rglob("*.js"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in tls_patterns):
                    has_tls = True
                    break
            except:
                pass

        if has_tls:
            score += 2
            details.append("有HTTPS/TLS支持")
        else:
            details.append("无TLS配置")

        # 4. 安全审计日志
        audit_patterns = ["audit", "security_log", "安全审计"]
        has_audit = False
        for code_file in list(self.project_path.rglob("*.py"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in audit_patterns):
                    has_audit = True
                    break
            except:
                pass

        if has_audit:
            score += 2
            details.append("有安全审计日志")
        else:
            details.append("无安全审计")

        # 5. 输入校验/防注入
        injection_patterns = ["sanitize", "escape", "parameterized", "prepared statement", "xss", "sql injection"]
        has_injection_protection = False
        for code_file in list(self.project_path.rglob("*.py"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in injection_patterns):
                    has_injection_protection = True
                    break
            except:
                pass

        if has_injection_protection:
            score += 1
            details.append("有输入校验/防注入")

        score = min(score, 10)
        return {"score": score, "details": details, "evidence": self.evidence["security"]}

    def _assess_scalability(self):
        """评估可扩展性"""
        score = 0
        details = []

        # 1. 插件机制
        plugin_patterns = ["plugin", "extension", "hook", "插件", "扩展"]
        has_plugin = False
        for code_file in list(self.project_path.rglob("*.py"))[:30] + list(self.project_path.rglob("*.js"))[:30]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in plugin_patterns):
                    has_plugin = True
                    break
            except:
                pass

        # 检查插件目录
        if (self.project_path / "plugins").exists() or (self.project_path / "extensions").exists():
            has_plugin = True

        if has_plugin:
            score += 3
            details.append("有插件/扩展机制")
        else:
            details.append("无插件机制")
        self.evidence["scalability"].append(f"插件机制: {has_plugin}")

        # 2. 微服务/模块化架构
        microservice_patterns = ["microservice", "service", "grpc", "rpc", "消息队列", "kafka", "rabbitmq"]
        has_microservice = False
        for code_file in list(self.project_path.rglob("*.py"))[:20] + list(self.project_path.rglob("*.js"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in microservice_patterns):
                    has_microservice = True
                    break
            except:
                pass

        if has_microservice:
            score += 2
            details.append("有微服务/模块化架构")
        else:
            details.append("单体架构")

        # 3. 配置中心
        config_center_patterns = ["config_center", "nacos", "consul", "etcd", "配置中心"]
        has_config_center = False
        for code_file in list(self.project_path.rglob("*.py"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in config_center_patterns):
                    has_config_center = True
                    break
            except:
                pass

        if has_config_center:
            score += 2
            details.append("有配置中心")
        else:
            details.append("无配置中心")

        # 4. 水平扩展支持
        horizontal_patterns = ["load_balancer", "replica", "cluster", "k8s", "kubernetes", "水平扩展"]
        has_horizontal = False
        for code_file in list(self.project_path.rglob("*.yml"))[:10] + list(self.project_path.rglob("*.yaml"))[:10]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in horizontal_patterns):
                    has_horizontal = True
                    break
            except:
                pass

        if has_horizontal:
            score += 2
            details.append("有水平扩展/K8s支持")
        else:
            details.append("无水平扩展配置")

        # 5. 多租户
        multi_tenant_patterns = ["tenant", "multi_tenant", "多租户", "workspace"]
        has_multi_tenant = False
        for code_file in list(self.project_path.rglob("*.py"))[:20]:
            try:
                content = code_file.read_text(errors="ignore").lower()
                if any(p in content for p in multi_tenant_patterns):
                    has_multi_tenant = True
                    break
            except:
                pass

        if has_multi_tenant:
            score += 1
            details.append("有多租户支持")

        score = min(score, 10)
        return {"score": score, "details": details, "evidence": self.evidence["scalability"]}

    def _get_level(self, score):
        """根据评分获取EMMS等级"""
        for (min_s, max_s), (code, name, desc) in self.LEVELS.items():
            if min_s <= score < max_s:
                return {"code": code, "name": name, "description": desc, "score": score}
        return {"code": "E8", "name": "工业化级", "description": "工业化标准", "score": score}

    def _generate_recommendations(self):
        """生成改进建议"""
        recommendations = []
        for dim, weight in self.DIMENSION_WEIGHTS.items():
            score = self.results[dim]["score"]
            if score < 5:
                dim_name = self.DIMENSION_NAMES[dim]
                recommendations.append({
                    "dimension": dim,
                    "dimension_name": dim_name,
                    "current_score": score,
                    "target_score": 6,
                    "priority": "高" if score < 4 else "中",
                    "suggestion": f"提升{dim_name}至6分以上，重点改进: {'; '.join(self.results[dim]['details'][-2:])}"
                })
        return recommendations

    def _calculate_project_hash(self):
        """计算项目哈希(用于锁档确权)"""
        hasher = hashlib.sha256()
        for file_path in sorted(self.project_path.rglob("*")):
            if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                try:
                    hasher.update(str(file_path.relative_to(self.project_path)).encode())
                    hasher.update(file_path.read_bytes()[:1024])
                except:
                    pass
        return hasher.hexdigest().upper()

    def to_json(self, indent=2):
        """输出JSON格式报告"""
        return json.dumps(self.results, ensure_ascii=False, indent=indent)

    def to_text(self):
        """输出文本格式报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("EMMS自动化评估报告 V1.0")
        lines.append("=" * 60)
        lines.append(f"项目路径: {self.project_path}")
        lines.append(f"评估时间: {self.results['metadata']['assess_time']}")
        lines.append(f"项目哈希: {self.results['metadata']['project_hash'][:16]}...")
        lines.append(f"确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
        lines.append("")

        level = self.results["level"]
        lines.append(f"【综合评分】 {self.results['total_score']}/10")
        lines.append(f"【EMMS等级】 {level['code']} {level['name']}")
        lines.append(f"【等级说明】 {level['description']}")
        lines.append("")

        lines.append("-" * 60)
        lines.append("八大维度评分详情")
        lines.append("-" * 60)
        for dim, weight in self.DIMENSION_WEIGHTS.items():
            result = self.results[dim]
            dim_name = self.DIMENSION_NAMES[dim]
            lines.append("")
            lines.append(f"【{dim_name}】 {result['score']}/10 (权重{int(weight*100)}%)")
            for detail in result["details"]:
                lines.append(f"  - {detail}")

        if self.results["recommendations"]:
            lines.append("")
            lines.append("-" * 60)
            lines.append("改进建议(优先级排序)")
            lines.append("-" * 60)
            for rec in sorted(self.results["recommendations"], key=lambda x: x["priority"]):
                lines.append("")
                lines.append(f"[{rec['priority']}优先级] {rec['dimension_name']}: {rec['current_score']}→{rec['target_score']}")
                lines.append(f"  建议: {rec['suggestion']}")

        if self.warnings:
            lines.append("")
            lines.append("-" * 60)
            lines.append(f"安全警告 ({len(self.warnings)}项)")
            lines.append("-" * 60)
            for w in self.warnings:
                lines.append(f"  ⚠️  {w}")

        lines.append("")
        lines.append("=" * 60)
        lines.append("报告生成: EMMS-Auto-Assessor-V1.0")
        lines.append("确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
        lines.append("=" * 60)

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="EMMS自动化评估工具 V1.0")
    parser.add_argument("--path", required=True, help="项目路径")
    parser.add_argument("--output", help="输出文件路径(JSON格式)")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    args = parser.parse_args()

    assessor = EMMSAssessor(args.path)
    results = assessor.assess()

    if args.format == "json":
        output = assessor.to_json()
    else:
        output = assessor.to_text()

    print()
    print(output)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print()
        print(f"[EMMS] 报告已保存: {args.output}")


if __name__ == "__main__":
    main()
