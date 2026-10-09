#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT MR-010 双轮算力调度器
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001

功能：
  1. 双轮算力路由：简单任务→本地小模型，复杂任务→外部API
  2. 六类定时任务：
     - 真值语义分类（每15分钟）
     - 冲突语义检测（每30分钟）
     - 日志摘要提炼（每小时）
     - 异常模式检测（每小时）
     - 自状态反思（每2小时）
     - 真值去重合并（每天）
  3. 结果自动写入9120真值池
  4. 错误降级：本地失败→跳过，不阻塞
  5. 完整审计日志
  6. 状态持久化
"""

import os
import sys
import time
import json
import logging
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# ============================================================
# 配置
# ============================================================
CONFIG = {
    # 本地小模型（Qwen2.5-0.5B）
    "local_llm": {
        "url": "http://127.0.0.1:8081/v1/chat/completions",
        "model": "qwen2.5-0.5b",
        "timeout": 30,
        "max_tokens": 200,
    },
    # 外部API（ai-proxy，支持doubao/hunyuan/kimi等）
    "external_api": {
        "url": "http://127.0.0.1:8021/v1/chat/completions",
        "model": "doubao",
        "timeout": 60,
        "max_tokens": 500,
    },
    # 9120记忆网关
    "gateway": {
        "url": "http://127.0.0.1:9120",
        "db_path": "/opt/ZONGYUAN-ROOT/data/memory_gateway.db",
    },
    # 任务调度间隔（秒）
    "intervals": {
        "truth_classification": 900,      # 15分钟
        "conflict_detection": 1800,        # 30分钟
        "log_summary": 3600,                # 1小时
        "anomaly_detection": 3600,          # 1小时
        "self_reflection": 7200,            # 2小时
        "truth_dedup": 86400,               # 24小时
    },
    # 路径
    "state_file": "/opt/ZONGYUAN-ROOT/ops/mr010_scheduler/state.json",
    "audit_log": "/opt/ZONGYUAN-ROOT/ops/mr010_scheduler/audit.jsonl",
    "log_file": "/opt/ZONGYUAN-ROOT/ops/mr010_scheduler/scheduler.log",
    # 节点ID
    "node_id": "mr010-dual-compute-scheduler",
}

# ============================================================
# 日志
# ============================================================
def setup_logging():
    os.makedirs(os.path.dirname(CONFIG["log_file"]), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(CONFIG["log_file"]),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("mr010")

logger = setup_logging()

# ============================================================
# 状态管理
# ============================================================
class StateManager:
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.state = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_run": {},        # {task_name: timestamp}
            "task_counts": {},     # {task_name: count}
            "success_count": 0,
            "error_count": 0,
            "local_llm_calls": 0,
            "external_api_calls": 0,
            "truths_written": 0,
            "started_at": datetime.now().isoformat(),
        }

    def save(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def should_run(self, task_name: str, interval: int) -> bool:
        last = self.state["last_run"].get(task_name, 0)
        return (time.time() - last) >= interval

    def mark_run(self, task_name: str):
        self.state["last_run"][task_name] = time.time()
        self.state["task_counts"][task_name] = self.state["task_counts"].get(task_name, 0) + 1

    def increment(self, field: str):
        self.state[field] = self.state.get(field, 0) + 1


# ============================================================
# 审计日志
# ============================================================
class AuditLogger:
    def __init__(self, audit_file: str):
        self.audit_file = audit_file
        os.makedirs(os.path.dirname(audit_file), exist_ok=True)

    def log(self, action: str, detail: Dict):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "detail": detail,
        }
        with open(self.audit_file, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ============================================================
# LLM调用器（双轮路由）
# ============================================================
class LLMClient:
    def __init__(self):
        self.local_config = CONFIG["local_llm"]
        self.external_config = CONFIG["external_api"]

    def _call_api(self, config: Dict, messages: List[Dict], max_tokens: int = None) -> Optional[str]:
        """调用OpenAI兼容API"""
        try:
            payload = {
                "model": config["model"],
                "messages": messages,
                "max_tokens": max_tokens or config["max_tokens"],
                "temperature": 0.3,
            }
            resp = requests.post(
                config["url"],
                json=payload,
                timeout=config["timeout"],
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"API调用失败 ({config['model']}): {e}")
            return None

    def call_local(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> Optional[str]:
        """调用本地小模型"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        result = self._call_api(self.local_config, messages, max_tokens)
        if result:
            logger.info(f"本地LLM调用成功: {result[:50]}...")
        return result

    def call_external(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> Optional[str]:
        """调用外部API"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        result = self._call_api(self.external_config, messages, max_tokens)
        if result:
            logger.info(f"外部API调用成功: {result[:50]}...")
        return result

    def call_with_fallback(self, system_prompt: str, user_prompt: str, complexity: str = "simple", max_tokens: int = None) -> Optional[str]:
        """
        双轮路由：
        - simple: 优先本地，失败→外部
        - complex: 优先外部，失败→本地
        """
        if complexity == "simple":
            result = self.call_local(system_prompt, user_prompt, max_tokens)
            if result:
                return result
            logger.warning("本地LLM失败，降级到外部API")
            return self.call_external(system_prompt, user_prompt, max_tokens)
        else:
            result = self.call_external(system_prompt, user_prompt, max_tokens)
            if result:
                return result
            logger.warning("外部API失败，降级到本地LLM")
            return self.call_local(system_prompt, user_prompt, max_tokens)


# ============================================================
# 9120真值写入器
# ============================================================
class TruthWriter:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def write(self, key: str, value: Any, category: str = "", node_id: str = None) -> bool:
        """写入真值到9120（直接SQLite，比HTTP更可靠）"""
        try:
            value_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            truth_hash = hashlib.sha256(value_str.encode()).hexdigest()
            now = time.time()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查是否已存在
            cursor.execute("SELECT id, version FROM truths WHERE truth_key = ?", (key,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    "UPDATE truths SET truth_value=?, truth_hash=?, category=?, node_id=?, updated_at=?, version=? WHERE id=?",
                    (value_str, truth_hash, category, node_id or CONFIG["node_id"], now, existing[1] + 1, existing[0]),
                )
                action = "updated"
            else:
                cursor.execute(
                    "INSERT INTO truths (truth_key, truth_value, truth_hash, category, node_id, created_at, updated_at, version) VALUES (?,?,?,?,?,?,?,1)",
                    (key, value_str, truth_hash, category, node_id or CONFIG["node_id"], now, now),
                )
                action = "inserted"

            conn.commit()
            conn.close()
            logger.info(f"真值写入成功 [{action}]: {key}")
            return True
        except Exception as e:
            logger.error(f"真值写入失败 {key}: {e}")
            return False

    def get_recent_truths(self, limit: int = 20) -> List[Dict]:
        """获取最近的真值（用于分类/检测任务）"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT truth_key, truth_value, category, node_id, updated_at FROM truths ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            logger.error(f"获取真值失败: {e}")
            return []


import hashlib  # 放在顶部更好，但这里补全

# ============================================================
# 六类定时任务实现
# ============================================================
class TaskExecutor:
    def __init__(self, llm: LLMClient, writer: TruthWriter, audit: AuditLogger, state: StateManager):
        self.llm = llm
        self.writer = writer
        self.audit = audit
        self.state = state

    def task_truth_classification(self):
        """任务1：真值语义分类（每15分钟）"""
        logger.info("=== 执行任务：真值语义分类 ===")
        truths = self.writer.get_recent_truths(15)
        if not truths:
            logger.info("无新真值，跳过分类")
            return

        # 构建分类prompt
        truth_list = "\n".join([f"- {t['truth_key']}: {t['truth_value'][:80]}" for t in truths[:10]])
        system_prompt = "你是一个真值分类器。对输入的真值列表进行语义分类，只输出JSON格式：[{\"key\":\"...\", \"category\":\"元法则|公理|定理|方法|数据|风险|决策|通用\", \"confidence\":0.0-1.0}]，不要解释。"
        user_prompt = f"请对以下真值进行分类：\n{truth_list}"

        result = self.llm.call_with_fallback(system_prompt, user_prompt, complexity="simple", max_tokens=500)
        if not result:
            logger.error("真值分类失败")
            self.state.increment("error_count")
            return

        # 解析结果并写入
        try:
            # 提取JSON
            json_start = result.find("[")
            json_end = result.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                classifications = json.loads(result[json_start:json_end])
                for item in classifications:
                    key = item.get("key", "")
                    category = item.get("category", "通用")
                    confidence = item.get("confidence", 0.5)
                    if key and confidence >= 0.5:
                        write_key = f"CLASSIFICATION.{key}.{int(time.time())}"
                        self.writer.write(
                            write_key,
                            {"original_key": key, "category": category, "confidence": confidence, "classifier": "qwen2.5-0.5b"},
                            category="classification",
                        )
                self.audit.log("truth_classification", {"count": len(classifications), "sample": classifications[:3]})
                self.state.increment("success_count")
                self.state.increment("local_llm_calls")
                self.state.increment("truths_written")
                logger.info(f"真值分类完成: {len(classifications)}条")
        except Exception as e:
            logger.error(f"分类结果解析失败: {e}")
            self.state.increment("error_count")

    def task_conflict_detection(self):
        """任务2：冲突语义检测（每30分钟）"""
        logger.info("=== 执行任务：冲突语义检测 ===")
        truths = self.writer.get_recent_truths(20)
        if len(truths) < 2:
            logger.info("真值不足，跳过冲突检测")
            return

        # 重点检测元法则/公理类
        critical = [t for t in truths if t.get("category") in ["META_RULE", "axiom", "meta_law"]]
        if not critical:
            logger.info("无关键真值，跳过冲突检测")
            return

        truth_list = "\n".join([f"- {t['truth_key']}: {t['truth_value'][:100]}" for t in critical[:8]])
        system_prompt = "你是一个冲突检测器。检查输入的真值之间是否存在语义矛盾或冲突。只输出JSON：{\"has_conflict\":true/false, \"conflicts\":[{\"keys\":[\"...\",\"...\"],\"reason\":\"...\"}], \"summary\":\"...\"}"
        user_prompt = f"检查以下真值是否存在冲突：\n{truth_list}"

        result = self.llm.call_with_fallback(system_prompt, user_prompt, complexity="simple", max_tokens=300)
        if not result:
            logger.error("冲突检测失败")
            self.state.increment("error_count")
            return

        try:
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                detection = json.loads(result[json_start:json_end])
                write_key = f"CONFLICT_DETECT.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.writer.write(write_key, detection, category="conflict_detection")
                self.audit.log("conflict_detection", detection)
                self.state.increment("success_count")
                self.state.increment("local_llm_calls")
                self.state.increment("truths_written")
                if detection.get("has_conflict"):
                    logger.warning(f"发现冲突: {detection.get('summary', '')}")
                else:
                    logger.info("冲突检测完成: 无冲突")
        except Exception as e:
            logger.error(f"冲突检测结果解析失败: {e}")
            self.state.increment("error_count")

    def task_log_summary(self):
        """任务3：日志摘要提炼（每小时）"""
        logger.info("=== 执行任务：日志摘要提炼 ===")
        # 读取最近的系统日志/服务日志
        log_snippets = []
        log_files = [
            "/opt/ZONGYUAN-ROOT/log/dr_self_healing.log",
            "/opt/ZONGYUAN-ROOT/ops/resource_monitor/state.json",
            "/opt/llama.cpp/logs/server-error.log",
        ]
        for log_file in log_files:
            try:
                if os.path.exists(log_file):
                    with open(log_file, "r") as f:
                        lines = f.readlines()[-20:]
                        log_snippets.append(f"=== {log_file} ===\n" + "".join(lines))
            except Exception:
                pass

        if not log_snippets:
            logger.info("无日志内容，跳过摘要")
            return

        log_content = "\n".join(log_snippets)[:2000]
        system_prompt = "你是一个日志分析专家。将输入的系统日志提炼为高纯度摘要，包括：关键事件、异常告警、服务状态变化、趋势判断。输出不超过200字。"
        user_prompt = f"请提炼以下日志摘要：\n{log_content}"

        result = self.llm.call_with_fallback(system_prompt, user_prompt, complexity="simple", max_tokens=300)
        if not result:
            logger.error("日志摘要失败")
            self.state.increment("error_count")
            return

        write_key = f"LOG_SUMMARY.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.writer.write(write_key, {"summary": result, "source": "system_logs", "analyzer": "qwen2.5-0.5b"}, category="log_summary")
        self.audit.log("log_summary", {"summary": result[:100]})
        self.state.increment("success_count")
        self.state.increment("local_llm_calls")
        self.state.increment("truths_written")
        logger.info(f"日志摘要完成: {result[:80]}...")

    def task_anomaly_detection(self):
        """任务4：异常模式检测（每小时）"""
        logger.info("=== 执行任务：异常模式检测 ===")
        # 获取系统状态
        try:
            import subprocess
            mem_info = subprocess.check_output(["free", "-h"]).decode()
            disk_info = subprocess.check_output(["df", "-h", "/"]).decode()
            services = subprocess.check_output(["systemctl", "list-units", "--type=service", "--state=failed", "--no-pager"]).decode()
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            mem_info = disk_info = services = "N/A"

        system_status = f"内存:\n{mem_info}\n磁盘:\n{disk_info}\n失败服务:\n{services}"
        system_prompt = "你是一个系统异常检测器。分析系统状态，识别异常模式和潜在风险。输出JSON：{\"anomalies\":[{\"type\":\"...\",\"severity\":\"低|中|高\",\"description\":\"...\",\"suggestion\":\"...\"}], \"overall_status\":\"正常|注意|警告|严重\"}"
        user_prompt = f"分析以下系统状态：\n{system_status}"

        result = self.llm.call_with_fallback(system_prompt, user_prompt, complexity="simple", max_tokens=400)
        if not result:
            logger.error("异常检测失败")
            self.state.increment("error_count")
            return

        try:
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                detection = json.loads(result[json_start:json_end])
                write_key = f"ANOMALY_DETECT.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.writer.write(write_key, detection, category="anomaly_detection")
                self.audit.log("anomaly_detection", detection)
                self.state.increment("success_count")
                self.state.increment("local_llm_calls")
                self.state.increment("truths_written")
                status = detection.get("overall_status", "未知")
                logger.info(f"异常检测完成: 整体状态={status}")
        except Exception as e:
            logger.error(f"异常检测结果解析失败: {e}")
            self.state.increment("error_count")

    def task_self_reflection(self):
        """任务5：自状态反思（每2小时）— 使用外部API做深度反思"""
        logger.info("=== 执行任务：自状态反思（深度） ===")
        # 收集内核状态
        truths_count = "未知"
        try:
            conn = sqlite3.connect(CONFIG["gateway"]["db_path"])
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM truths")
            truths_count = cursor.fetchone()[0]
            conn.close()
        except Exception:
            pass

        state_summary = json.dumps(self.state.state, ensure_ascii=False, indent=2)[:1500]
        system_prompt = "你是ZONGYUAN-ROOT元内核的自反思引擎。基于当前运行状态，进行深度自我评估，识别：1)当前优势 2)存在问题 3)进化方向 4)具体优化建议。输出结构化反思报告，不超过500字。"
        user_prompt = f"当前内核状态：\n真值总数: {truths_count}\n运行状态:\n{state_summary}\n\n请进行深度自反思。"

        # 自反思使用外部API（复杂任务）
        result = self.llm.call_with_fallback(system_prompt, user_prompt, complexity="complex", max_tokens=600)
        if not result:
            logger.error("自反思失败")
            self.state.increment("error_count")
            return

        write_key = f"SELF_REFLECTION.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.writer.write(write_key, {"reflection": result, "truths_count": truths_count, "engine": "external_api"}, category="self_reflection")
        self.audit.log("self_reflection", {"reflection": result[:150]})
        self.state.increment("success_count")
        self.state.increment("external_api_calls")
        self.state.increment("truths_written")
        logger.info(f"自反思完成: {result[:100]}...")

    def task_truth_dedup(self):
        """任务6：真值去重合并（每天）"""
        logger.info("=== 执行任务：真值去重合并 ===")
        truths = self.writer.get_recent_truths(50)
        if len(truths) < 5:
            logger.info("真值不足，跳过去重")
            return

        # 按key前缀分组
        groups = {}
        for t in truths:
            key = t["truth_key"]
            prefix = ".".join(key.split(".")[:2]) if "." in key else key
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(t)

        # 找出重复候选组
        dup_candidates = {k: v for k, v in groups.items() if len(v) >= 3}
        if not dup_candidates:
            logger.info("无明显重复组")
            return

        dup_summary = []
        for prefix, items in list(dup_candidates.items())[:5]:
            dup_summary.append(f"组[{prefix}]: {len(items)}条真值")

        system_prompt = "你是一个真值去重专家。分析以下真值组，建议哪些可以合并、哪些是冗余的。输出JSON：{\"merge_suggestions\":[{\"group\":\"...\",\"keys\":[\"...\"],\"reason\":\"...\",\"merged_summary\":\"...\"}], \"redundant_keys\":[\"...\"]}"
        user_prompt = f"分析以下重复候选组：\n" + "\n".join(dup_summary)

        result = self.llm.call_with_fallback(system_prompt, user_prompt, complexity="simple", max_tokens=400)
        if not result:
            logger.error("去重分析失败")
            self.state.increment("error_count")
            return

        try:
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                dedup = json.loads(result[json_start:json_end])
                write_key = f"TRUTH_DEDUP.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.writer.write(write_key, dedup, category="truth_dedup")
                self.audit.log("truth_dedup", dedup)
                self.state.increment("success_count")
                self.state.increment("local_llm_calls")
                self.state.increment("truths_written")
                logger.info(f"去重分析完成: {len(dedup.get('merge_suggestions', []))}个合并建议")
        except Exception as e:
            logger.error(f"去重结果解析失败: {e}")
            self.state.increment("error_count")


# ============================================================
# 主调度器
# ============================================================
class MR010Scheduler:
    def __init__(self):
        self.state = StateManager(CONFIG["state_file"])
        self.audit = AuditLogger(CONFIG["audit_log"])
        self.llm = LLMClient()
        self.writer = TruthWriter(CONFIG["gateway"]["db_path"])
        self.executor = TaskExecutor(self.llm, self.writer, self.audit, self.state)

        # 任务映射
        self.tasks = {
            "truth_classification": (self.executor.task_truth_classification, CONFIG["intervals"]["truth_classification"]),
            "conflict_detection": (self.executor.task_conflict_detection, CONFIG["intervals"]["conflict_detection"]),
            "log_summary": (self.executor.task_log_summary, CONFIG["intervals"]["log_summary"]),
            "anomaly_detection": (self.executor.task_anomaly_detection, CONFIG["intervals"]["anomaly_detection"]),
            "self_reflection": (self.executor.task_self_reflection, CONFIG["intervals"]["self_reflection"]),
            "truth_dedup": (self.executor.task_truth_dedup, CONFIG["intervals"]["truth_dedup"]),
        }

    def run_cycle(self):
        """执行一轮调度"""
        logger.info("=" * 60)
        logger.info("MR-010 双轮算力调度循环开始")
        logger.info("=" * 60)

        for task_name, (task_func, interval) in self.tasks.items():
            if self.state.should_run(task_name, interval):
                logger.info(f"--- 执行任务: {task_name} (间隔{interval}秒) ---")
                try:
                    task_func()
                    self.state.mark_run(task_name)
                except Exception as e:
                    logger.error(f"任务 {task_name} 执行异常: {e}")
                    self.state.increment("error_count")
                self.state.save()
            else:
                last = self.state.state["last_run"].get(task_name, 0)
                next_run = interval - (time.time() - last)
                logger.debug(f"任务 {task_name} 未到执行时间，下次还有{next_run:.0f}秒")

        logger.info("=" * 60)
        logger.info(f"调度循环完成 | 成功:{self.state.state.get('success_count',0)} 失败:{self.state.state.get('error_count',0)} 本地调用:{self.state.state.get('local_llm_calls',0)} 外部调用:{self.state.state.get('external_api_calls',0)} 真值写入:{self.state.state.get('truths_written',0)}")
        logger.info("=" * 60)

    def run_forever(self):
        """常驻运行"""
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════╗")
        logger.info("║  MR-010 双轮算力调度器启动                           ║")
        logger.info("║  本地LLM: Qwen2.5-0.5B @ 127.0.0.1:8081           ║")
        logger.info("║  外部API: ai-proxy @ 127.0.0.1:8021 (doubao)      ║")
        logger.info("║  真值网关: 9120 (SQLite直写)                         ║")
        logger.info("║  任务: 6类定时任务 (分类/冲突/摘要/异常/反思/去重)  ║")
        logger.info("╚══════════════════════════════════════════════════════╝")
        logger.info("")

        # 启动时立即执行一轮
        self.run_cycle()

        # 然后每60秒检查一次
        while True:
            time.sleep(60)
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"调度循环异常: {e}")
                self.state.increment("error_count")
                self.state.save()


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MR-010 双轮算力调度器")
    parser.add_argument("--once", action="store_true", help="只运行一轮")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--daemon", action="store_true", help="常驻运行（默认）")

    args = parser.parse_args()

    scheduler = MR010Scheduler()

    if args.status:
        print(json.dumps(scheduler.state.state, ensure_ascii=False, indent=2))
    elif args.once:
        scheduler.run_cycle()
        print("一轮调度完成")
    else:
        scheduler.run_forever()
