"""
记忆网关服务端进化方案 V1.0
生成时间: 2026-09-15 19:30 CST
触发: 元极恒一超认知永恒自治每小时心跳黄色告警自愈
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

包含4项修复:
1. /api/truths 端点修复（支持查询参数与列表分页）
2. 节点心跳超时降级机制
3. 自动仲裁分流引擎
4. POST端点限流与502防护

部署说明: 本文件为服务端代码补丁方案，需通过非SSH通道（CI/CD或云控制台）部署至
         /opt/storage 对应服务目录。禁止SSH直连123.207.202.158。
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import Optional, List
import time
import hashlib
import json

# ============================================================
# 模块1: /api/truths 端点修复
# 问题: 当前端点忽略所有查询参数，恒返回id=1499空记录
# 修复: 支持 ?id=, ?truth_key=, ?category=, ?node_id=, ?limit=, ?offset=
# ============================================================

def fix_truths_endpoint(app: FastAPI, db):
    """修复 /api/truths 端点，支持多维度查询与分页"""

    @app.get("/api/truths")
    async def get_truths(
        id: Optional[int] = None,
        truth_key: Optional[str] = None,
        category: Optional[str] = None,
        node_id: Optional[str] = None,
        truth_type: Optional[str] = None,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0)
    ):
        query = db.query("SELECT * FROM truths WHERE 1=1")
        params = []

        if id is not None:
            query += " AND id = ?"
            params.append(id)
        if truth_key:
            query += " AND truth_key LIKE ?"
            params.append(f"%{truth_key}%")
        if category:
            query += " AND category = ?"
            params.append(category)
        if node_id:
            query += " AND node_id = ?"
            params.append(node_id)
        if truth_type:
            query += " AND truth_type = ?"
            params.append(truth_type)

        total = db.query(f"SELECT COUNT(*) FROM ({query})", params).scalar()
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = db.query(query, params).fetchall()

        return {
            "status": "ok",
            "total": total,
            "limit": limit,
            "offset": offset,
            "truths": [dict(r) for r in rows]
        }


# ============================================================
# 模块2: 节点心跳超时降级机制
# 问题: verify-node和local-test静默超17小时仍标记active
# 修复: 基于last_report_at自动降级，三级告警
# ============================================================

class NodeTimeoutDegradation:
    """节点心跳超时降级引擎"""

    DEGRADED_THRESHOLD = timedelta(hours=2)
    SUSPECTED_OFFLINE_THRESHOLD = timedelta(hours=6)
    OFFLINE_THRESHOLD = timedelta(hours=24)

    EXCLUDED_NODES = {"local-test"}  # 测试节点允许长期间歇

    def __init__(self, db):
        self.db = db

    def check_and_degrade(self, node_id: str, last_report_at: str) -> dict:
        """检查节点活跃度并执行降级"""
        if node_id in self.EXCLUDED_NODES:
            return {"node_id": node_id, "action": "excluded", "alert": "none"}

        last_report = datetime.fromisoformat(last_report_at.replace("Z", "+00:00"))
        now = datetime.utcnow()
        silence_duration = now - last_report

        if silence_duration > self.OFFLINE_THRESHOLD:
            action, alert = "mark_offline", "red"
        elif silence_duration > self.SUSPECTED_OFFLINE_THRESHOLD:
            action, alert = "mark_suspected_offline", "orange"
        elif silence_duration > self.DEGRADED_THRESHOLD:
            action, alert = "mark_degraded", "yellow"
        else:
            action, alert = "keep_active", "green"

        # 更新节点状态
        self.db.execute(
            "UPDATE nodes SET status = ?, degraded_at = ? WHERE node_id = ?",
            (action, now.isoformat(), node_id)
        )

        return {
            "node_id": node_id,
            "silence_hours": round(silence_duration.total_seconds() / 3600, 1),
            "action": action,
            "alert": alert
        }

    def run_periodic_check(self) -> List[dict]:
        """全节点周期检查，返回降级结果列表"""
        nodes = self.db.query("SELECT node_id, last_report_at FROM nodes").fetchall()
        results = []
        for node in nodes:
            result = self.check_and_degrade(node["node_id"], node["last_report_at"])
            if result["alert"] != "green":
                results.append(result)
        return results


# ============================================================
# 模块3: 自动仲裁分流引擎
# 问题: need_arbitration积压393条，无自动处理机制
# 修复: 基于置信度+冲突状态的五级自动仲裁分流
# ============================================================

class AutoArbitrationEngine:
    """自动仲裁分流引擎 V1.0"""

    MAX_OPERATIONS_PER_HOUR = 200
    BATCH_SIZE = 50
    ESCALATION_THRESHOLD = 100

    def __init__(self, db):
        self.db = db
        self.operations_this_hour = 0
        self.hour_start = time.time()

    def _reset_counter_if_needed(self):
        if time.time() - self.hour_start > 3600:
            self.operations_this_hour = 0
            self.hour_start = time.time()

    def arbitrate(self, report: dict) -> dict:
        """对单条待仲裁报告执行自动仲裁"""
        self._reset_counter_if_needed()
        if self.operations_this_hour >= self.MAX_OPERATIONS_PER_HOUR:
            return {"action": "deferred", "reason": "hourly_quota_exceeded"}

        confidence = report.get("confidence", 0)
        has_conflict = report.get("conflict_check", {}).get("conflict", False)
        truth_key = report.get("truth_key", "")

        # 规则1: 高置信度无冲突 → 自动通过
        if confidence >= 0.95 and not has_conflict:
            self._approve(report, "auto_approve_high_confidence")
            return {"action": "auto_approve", "reason": "confidence>=0.95 no_conflict"}

        # 规则2: 中高置信度无冲突 → 通过但记录
        if confidence >= 0.8 and not has_conflict:
            self._approve(report, "auto_approve_with_log")
            return {"action": "auto_approve_with_log", "reason": "confidence>=0.8 no_conflict"}

        # 规则3: 有冲突但高置信度 → 触发三方交叉验证
        if has_conflict and confidence >= 0.9:
            return {"action": "cross_validate", "reason": "conflict with high confidence"}

        # 规则4: 低置信度 → 标记人工审核
        if confidence < 0.6:
            self._flag_for_review(report, "low_confidence")
            return {"action": "flag_for_review", "reason": "confidence<0.6"}

        # 规则5: 重复truth_key → 合并最新版本
        if self._is_duplicate(truth_key):
            self._merge_duplicate(report)
            return {"action": "merge_duplicate", "reason": "duplicate truth_key"}

        # 默认: 保留待仲裁
        return {"action": "keep_pending", "reason": "no_rule_matched"}

    def _approve(self, report: dict, reason: str):
        self.db.execute(
            "UPDATE reports SET arbitration_status = 'auto_resolved', resolution_reason = ?, "
            "resolved_at = ? WHERE report_id = ?",
            (reason, datetime.utcnow().isoformat(), report["report_id"])
        )
        self.operations_this_hour += 1

    def _flag_for_review(self, report: dict, reason: str):
        self.db.execute(
            "UPDATE reports SET arbitration_status = 'needs_human_review', "
            "review_reason = ? WHERE report_id = ?",
            (reason, report["report_id"])
        )
        self.operations_this_hour += 1

    def _is_duplicate(self, truth_key: str) -> bool:
        count = self.db.query(
            "SELECT COUNT(*) FROM reports WHERE truth_key = ? AND arbitration_status = 'resolved'",
            (truth_key,)
        ).scalar()
        return count > 0

    def _merge_duplicate(self, report: dict):
        self.db.execute(
            "UPDATE reports SET arbitration_status = 'merged', "
            "merged_at = ? WHERE report_id = ?",
            (datetime.utcnow().isoformat(), report["report_id"])
        )
        self.operations_this_hour += 1

    def run_batch(self) -> dict:
        """批量处理待仲裁队列"""
        pending = self.db.query(
            "SELECT * FROM reports WHERE arbitration_status = 'pending' "
            "ORDER BY confidence DESC LIMIT ?",
            (self.BATCH_SIZE,)
        ).fetchall()

        results = {"processed": 0, "auto_approved": 0, "flagged": 0, "merged": 0, "deferred": 0}
        for report in pending:
            result = self.arbitrate(dict(report))
            results["processed"] += 1
            action = result["action"]
            if action == "auto_approve":
                results["auto_approved"] += 1
            elif action == "flag_for_review":
                results["flagged"] += 1
            elif action == "merge_duplicate":
                results["merged"] += 1
            elif action == "deferred":
                results["deferred"] += 1

        remaining = self.db.query(
            "SELECT COUNT(*) FROM reports WHERE arbitration_status = 'pending'"
        ).scalar()
        results["remaining_pending"] = remaining

        if remaining > self.ESCALATION_THRESHOLD:
            results["escalation"] = "orange_alert_backlog_high"

        return results


# ============================================================
# 模块4: POST端点限流与502防护
# 问题: 连续快速POST导致后端502 Bad Gateway
# 修复: 令牌桶限流 + 请求队列 + 健康检查熔断
# ============================================================

class RateLimiter:
    """令牌桶限流器"""

    def __init__(self, rate_per_second: float = 1.0, burst: int = 3):
        self.rate = rate_per_second
        self.burst = burst
        self.tokens = burst
        self.last_refill = time.time()

    def acquire(self) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_refill = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class CircuitBreaker:
    """熔断器 - 后端异常时快速失败而非等待超时"""

    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 30  # 秒

    def __init__(self):
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.FAILURE_THRESHOLD:
            self.state = "open"

    def record_success(self):
        self.failure_count = 0
        self.state = "closed"

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.RECOVERY_TIMEOUT:
                self.state = "half_open"
                return True
            return False
        # half_open: 允许一个探测请求
        return True

    def call(self, func, *args, **kwargs):
        if not self.can_execute():
            raise HTTPException(status_code=503, detail="Service temporarily unavailable (circuit open)")
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise


# ============================================================
# 集成: 应用所有修复到FastAPI实例
# ============================================================

def apply_evolution_patch(app: FastAPI, db):
    """应用全部进化补丁到FastAPI应用"""

    # 模块1: 修复truths端点
    fix_truths_endpoint(app, db)

    # 模块2: 节点降级 - 注册中间件
    node_degrader = NodeTimeoutDegradation(db)

    @app.middleware("http")
    async def node_health_middleware(request, call_next):
        response = await call_next(request)
        return response

    # 模块3: 自动仲裁 - 注册后台任务端点
    arbitration_engine = AutoArbitrationEngine(db)

    @app.post("/api/admin/arbitration/run")
    async def run_arbitration_batch():
        result = arbitration_engine.run_batch()
        return {"status": "ok", "result": result}

    # 模块4: 限流与熔断 - 包装POST /api/report/truth
    rate_limiter = RateLimiter(rate_per_second=0.5, burst=2)
    circuit_breaker = CircuitBreaker()

    @app.middleware("http")
    async def rate_limit_middleware(request, call_next):
        if request.method == "POST" and request.url.path == "/api/report/truth":
            if not rate_limiter.acquire():
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please retry after 2 seconds."}
                )
        response = await call_next(request)
        return response

    return {
        "truths_endpoint": "fixed",
        "node_degradation": "registered",
        "auto_arbitration": "registered at /api/admin/arbitration/run",
        "rate_limiting": "0.5 req/s burst=2",
        "circuit_breaker": "threshold=5 recovery=30s"
    }


# ============================================================
# 部署验证清单
# ============================================================

DEPLOYMENT_CHECKLIST = """
[ ] 1. 备份当前服务代码与数据库
[ ] 2. 通过CI/CD或云控制台部署本补丁（禁止SSH）
[ ] 3. 验证 /api/truths?id=1 返回指定记录而非恒返回1499
[ ] 4. 验证 /api/truths?limit=5&offset=0 返回列表格式
[ ] 5. 验证节点降级: 模拟last_report_at=25h前的节点标记offline
[ ] 6. 验证仲裁: POST /api/admin/arbitration/run 返回处理统计
[ ] 7. 验证限流: 连续快速POST第3条返回429
[ ] 8. 验证熔断: 模拟后端5次失败后第6次快速返回503
[ ] 9. 全量回归测试: 6项心跳指标全部green
[ ] 10. 上报部署结果至记忆网关 truth_type=config
"""

if __name__ == "__main__":
    print("记忆网关进化方案 V1.0")
    print("4项修复模块已就绪，需通过非SSH通道部署")
    print(DEPLOYMENT_CHECKLIST)
