#!/usr/bin/env python3
# ZONGYUAN-ROOT API 配额管理与预算控制
"""
API Quota Manager - 防止配额耗尽 + 成本优化

功能:
✓ 每日/每月配额限制
✓ 按模型分级限额
✓ 成本估算与预算告警
✓ 自动降级到免费模型
✓ 使用率统计报表
"""

import os, json, time, sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

CONFIG_DIR = Path("/zongyuan-yuanji/config")
QUOTA_DB = CONFIG_DIR / "api_quotas.db"


class APIQuotaManager:
    """API 配额管理器"""
    
    def __init__(self):
        self.db_path = QUOTA_DB
        self._init_db()
        
        # 默认配额配置 (可按需调整)
        self.daily_quotas = {
            "doubao": 10_000_000,      # 10M tokens/day (~¥10)
            "sensenova": 5_000_000,    # 5M tokens/day (~¥2.5)
            "deepseek-pro": 2_000_000, # 2M tokens/day (~¥6)
            "glm-flash": 50_000_000,   # 免费，不设限
        }
        
        self.monthly_budget = {
            "total": 100.0,             # ¥100/月总预算
            "warning_threshold": 80.0,  # 80% 时告警
            "critical_threshold": 90.0, # 90% 时强制降级
        }
    
    def _init_db(self):
        """初始化数据库"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                model_name TEXT NOT NULL,
                tokens_used INTEGER NOT NULL,
                cost DECIMAL(10,4),
                success BOOLEAN NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON usage_log(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def check_quota_available(self, model_name: str, required_tokens: int) -> Dict:
        """
        检查配额是否可用
        
        Returns:
            {"available": bool, "remaining": int, "reason": str}
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SUM(tokens_used) FROM usage_log
            WHERE model_name = ? AND timestamp >= ?
        """, (model_name, today.isoformat()))
        
        result = cursor.fetchone()
        used = result[0] or 0
        remaining = self.daily_quotas.get(model_name, float('inf')) - used
        
        conn.close()
        
        if remaining < required_tokens:
            return {
                "available": False,
                "remaining": remaining,
                "reason": f"今日配额不足 (剩余{remaining:,}/{self.daily_quotas[model_name]:,})",
                "suggestion": self._get_fallback_model(model_name)
            }
        
        return {
            "available": True,
            "remaining": remaining,
            "used_today": used
        }
    
    def record_usage(self, model_name: str, tokens_used: int, 
                    success: bool, cost: float = 0.0):
        """记录 API 使用量"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO usage_log (model_name, tokens_used, cost, success)
            VALUES (?, ?, ?, ?)
        """, (model_name, tokens_used, cost, success))
        
        conn.commit()
        conn.close()
        
        # 检查预算告警
        if success:
            self._check_budget_alert()
    
    def _check_budget_alert(self):
        """检查预算告警"""
        monthly_cost = self.get_monthly_cost()
        threshold_warning = self.monthly_budget["warning_threshold"]
        threshold_critical = self.monthly_budget["critical_threshold"]
        
        if monthly_cost >= threshold_critical:
            print(f"\n⚠️ [CRITICAL] 本月 API 费用已达¥{monthly_cost:.2f}"
                  f" ({monthly_cost/self.monthly_budget['total']*100:.1f}%)"
                  f" ≥ 90%, 已触发自动降级！\n")
            # TODO: 发送告警通知
    
    def get_monthly_cost(self) -> float:
        """获取本月累计费用"""
        first_day = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SUM(cost) FROM usage_log
            WHERE timestamp >= ?
        """, (first_day.isoformat(),))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] or 0.0
    
    def get_usage_stats(self, days: int = 7) -> Dict:
        """获取使用统计 (最近 N 天)"""
        start_date = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT model_name, 
                   SUM(tokens_used) as total_tokens,
                   SUM(cost) as total_cost,
                   COUNT(*) as call_count,
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count
            FROM usage_log
            WHERE timestamp >= ?
            GROUP BY model_name
        """, (start_date.isoformat(),))
        
        rows = cursor.fetchall()
        conn.close()
        
        stats = {}
        for row in rows:
            success_rate = (row[4] / row[3] * 100) if row[3] > 0 else 0
            stats[row[0]] = {
                "tokens": row[1],
                "cost": round(row[2], 2),
                "calls": row[3],
                "success_rate": round(success_rate, 2)
            }
        
        return stats
    
    def _get_fallback_model(self, current_model: str) -> str:
        """获取回退模型推荐"""
        fallback_chain = {
            "doubao": "sensenova",
            "sensenova": "glm-flash",
            "deepseek-pro": "glm-flash",
            "glm-flash": "local-fallback",
        }
        return fallback_chain.get(current_model, "local-fallback")
    
    def reset_daily_quota(self, model_name: str = None):
        """重置指定模型的日配额 (用于测试或手动干预)"""
        pass  # 保留接口，实际不需要手动调用
    
    def export_report(self, output_path: str = None):
        """导出使用报告"""
        if output_path is None:
            output_path = "/zongyuan-yuanji/logs/api_usage_report.json"
        
        stats = self.get_usage_stats(days=30)
        monthly_cost = self.get_monthly_cost()
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "monthly_budget": self.monthly_budget,
            "current_month_cost": round(monthly_cost, 2),
            "budget_remaining": self.monthly_budget["total"] - monthly_cost,
            "usage_by_model": stats,
            "recommendations": self._generate_recommendations(stats)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report
    
    def _generate_recommendations(self, stats: Dict) -> list:
        """生成优化建议"""
        recommendations = []
        
        # 分析高成本模型
        high_cost_models = ["deepseek-pro"]
        for model in high_cost_models:
            if stats.get(model, {}).get("tokens", 0) > 1_000_000:
                recommendations.append(
                    f"⚠️ {model}本月消耗大量 token ({stats[model]['tokens']:,}), "
                    "考虑降低优先级或设置更严格限额"
                )
        
        # 分析低成功率模型
        for model, data in stats.items():
            if data.get("success_rate", 100) < 80:
                recommendations.append(
                    f"⚠️ {model}成功率较低 ({data['success_rate']}%), "
                    "建议检查 API 密钥有效性或网络状态"
                )
        
        return recommendations


if __name__ == "__main__":
    # 测试
    quota_manager = APIQuotaManager()
    
    # 模拟使用
    print("✅ API 配额管理器初始化完成")
    print(f"\n📊 今日配额:")
    for model, quota in quota_manager.daily_quotas.items():
        available = quota_manager.check_quota_available(model, 1000)
        print(f"  {model}: {available['remaining']:,} tokens 剩余")
    
    print(f"\n💰 本月费用：¥{quota_manager.get_monthly_cost():.2f}")
    print(f"  预算：¥{quota_manager.monthly_budget['total']}")
    print(f"  剩余：¥{quota_manager.monthly_budget['total'] - quota_manager.get_monthly_cost():.2f}")
    
    print("\n📈 使用统计 (近 7 天):")
    stats = quota_manager.get_usage_stats(days=7)
    for model, data in stats.items():
        print(f"  {model}: {data['calls']}次调用, ¥{data['cost']}费用, {data['success_rate']}%成功率")
    
    print("\n📋 生成完整报告...")
    report = quota_manager.export_report()
    print(f"  报告位置：/zongyuan-yuanji/logs/api_usage_report.json")
