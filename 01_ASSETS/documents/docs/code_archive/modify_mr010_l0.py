#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改MR-010调度器，将4类任务替换为L0规则引擎
- 真值分类 → L0规则引擎
- 冲突检测 → L0规则引擎
- 异常检测 → L0规则引擎
- 真值去重 → L0规则引擎
- 日志摘要 → 保留外部API
- 自状态反思 → 保留外部API
"""

import re

FILE_PATH = "/opt/ZONGYUAN-ROOT/ops/mr010_scheduler/dr_mr010_scheduler.py"

with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加L0规则引擎导入（在typing导入后）
if "from engine.l0_rule_engine import L0RuleEngine" not in content:
    content = content.replace(
        "from typing import Dict, List, Optional, Any",
        "from typing import Dict, List, Optional, Any\n\n# L0纯规则引擎（零LLM依赖，常驻<50MB）\nsys.path.insert(0, '/opt/ZONGYUAN-ROOT')\nfrom engine.l0_rule_engine import L0RuleEngine"
    )
    print("✅ 已添加L0规则引擎导入")

# 2. 在TaskExecutor的__init__中添加L0引擎实例
if "self.l0_engine = L0RuleEngine()" not in content:
    content = content.replace(
        "self.llm = LLMClient()",
        "self.llm = LLMClient()\n        self.l0_engine = L0RuleEngine()  # L0纯规则引擎"
    )
    print("✅ 已添加L0引擎实例")

# 3. 替换真值分类任务
old_classification = '''    def task_truth_classification(self):
        """任务1：真值语义分类（每15分钟）"""
        logger.info("=== 执行任务：真值语义分类 ===")
        truths = self.writer.get_recent_truths(15)
        if not truths:
            logger.info("无新真值，跳过分类")
            return

        # 构建分类prompt
        truth_list = "\\n".join([f"- {t['truth_key']}: {t['truth_value'][:80]}" for t in truths[:10]])
        system_prompt = "你是一个真值分类器。对输入的真值列表进行语义分类，只输出JSON格式：[{\\"key\\":\\"...\\", \\"category\\":\\"元法则|公理|定理|方法|数据|风险|决策|通用\\", \\"confidence\\":0.0-1.0}]，不要解释。"
        user_prompt = f"请对以下真值进行分类：\\n{truth_list}"

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
            self.state.increment("error_count")'''

new_classification = '''    def task_truth_classification(self):
        """任务1：真值语义分类（每15分钟）— L0规则引擎"""
        logger.info("=== 执行任务：真值语义分类（L0规则引擎） ===")
        truths = self.writer.get_recent_truths(15)
        if not truths:
            logger.info("无新真值，跳过分类")
            return

        try:
            # 使用L0规则引擎分类（零LLM依赖）
            classifications = self.l0_engine.classify_truths_batch(truths[:20])
            written = 0
            for item in classifications:
                key = item.get("key", "")
                category = item.get("category", "通用")
                confidence = item.get("confidence", 0.5)
                if key and confidence >= 0.5:
                    write_key = f"CLASSIFICATION.{key}.{int(time.time())}"
                    self.writer.write(
                        write_key,
                        {"original_key": key, "category": category, "confidence": confidence, "classifier": "L0-RULE-ENGINE"},
                        category="classification",
                    )
                    written += 1
            self.audit.log("truth_classification", {"count": written, "engine": "L0-RULE-ENGINE", "sample": classifications[:3]})
            self.state.increment("success_count")
            self.state.increment("truths_written")
            logger.info(f"真值分类完成（L0规则引擎）: {written}条")
        except Exception as e:
            logger.error(f"L0规则引擎分类失败: {e}")
            self.state.increment("error_count")'''

if old_classification in content:
    content = content.replace(old_classification, new_classification)
    print("✅ 已替换真值分类任务")
else:
    print("⚠️ 真值分类任务未找到（可能已被修改）")

# 4. 替换冲突检测任务
old_conflict = '''    def task_conflict_detection(self):
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

        truth_list = "\\n".join([f"- {t['truth_key']}: {t['truth_value'][:100]}" for t in critical[:8]])
        system_prompt = "你是一个冲突检测器。检查输入的真值之间是否存在语义矛盾或冲突。只输出JSON：{\\"has_conflict\\":true/false, \\"conflicts\\":[{\\"keys\\":[\\"...\\",\\"...\\"],\\"reason\\":\\"...\\"}], \\"summary\\":\\"...\\"}"
        user_prompt = f"检查以下真值是否存在冲突：\\n{truth_list}"

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
            logger.error(f"冲突检测结果解析失败: {e}")'''

new_conflict = '''    def task_conflict_detection(self):
        """任务2：冲突语义检测（每30分钟）— L0规则引擎"""
        logger.info("=== 执行任务：冲突语义检测（L0规则引擎） ===")
        truths = self.writer.get_recent_truths(20)
        if len(truths) < 2:
            logger.info("真值不足，跳过冲突检测")
            return

        try:
            # 使用L0规则引擎检测冲突（零LLM依赖）
            detection = self.l0_engine.detect_conflicts(truths)
            write_key = f"CONFLICT_DETECT.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.writer.write(write_key, detection, category="conflict_detection")
            self.audit.log("conflict_detection", detection)
            self.state.increment("success_count")
            self.state.increment("truths_written")
            if detection.get("has_conflict"):
                logger.warning(f"发现冲突（L0规则引擎）: {detection.get('summary', '')}")
            else:
                logger.info("冲突检测完成（L0规则引擎）: 无冲突")
        except Exception as e:
            logger.error(f"L0规则引擎冲突检测失败: {e}")
            self.state.increment("error_count")'''

if old_conflict in content:
    content = content.replace(old_conflict, new_conflict)
    print("✅ 已替换冲突检测任务")
else:
    print("⚠️ 冲突检测任务未找到（可能已被修改）")

# 5. 替换异常检测任务
old_anomaly = '''    def task_anomaly_detection(self):
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

        system_status = f"内存:\\n{mem_info}\\n磁盘:\\n{disk_info}\\n失败服务:\\n{services}"
        system_prompt = "你是一个系统异常检测器。分析系统状态，识别异常模式和潜在风险。输出JSON：{\\"anomalies\\":[{\\"type\\":\\"...\\",\\"severity\\":\\"低|中|高\\",\\"description\\":\\"...\\",\\"suggestion\\":\\"...\\"}], \\"overall_status\\":\\"正常|注意|警告|严重\\"}"
        user_prompt = f"分析以下系统状态：\\n{system_status}"

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
            self.state.increment("error_count")'''

new_anomaly = '''    def task_anomaly_detection(self):
        """任务4：异常模式检测（每小时）— L0规则引擎"""
        logger.info("=== 执行任务：异常模式检测（L0规则引擎） ===")
        try:
            import subprocess
            # 获取内存使用率
            mem_output = subprocess.check_output(["free", "-m"]).decode()
            mem_lines = mem_output.strip().split("\\n")
            if len(mem_lines) >= 2:
                mem_parts = mem_lines[1].split()
                if len(mem_parts) >= 3:
                    total_mem = int(mem_parts[1])
                    used_mem = int(mem_parts[2])
                    mem_usage_percent = round(used_mem / total_mem * 100, 1)
                else:
                    mem_usage_percent = 0
            else:
                mem_usage_percent = 0

            # 获取磁盘使用率
            disk_output = subprocess.check_output(["df", "-h", "/"]).decode()
            disk_lines = disk_output.strip().split("\\n")
            disk_usage_percent = 0
            if len(disk_lines) >= 2:
                disk_parts = disk_lines[1].split()
                for part in disk_parts:
                    if "%" in part:
                        disk_usage_percent = int(part.replace("%", ""))
                        break

            # 获取失败服务
            services_output = subprocess.check_output(["systemctl", "list-units", "--type=service", "--state=failed", "--no-pager"]).decode()
            failed_services = []
            for line in services_output.split("\\n"):
                if ".service" in line and "loaded" in line:
                    service_name = line.strip().split()[0]
                    failed_services.append(service_name)

            system_info = {
                "mem_usage_percent": mem_usage_percent,
                "disk_usage_percent": disk_usage_percent,
                "failed_services": failed_services,
                "cpu_usage_percent": 0,  # 可后续补充
            }

            # 使用L0规则引擎检测异常（零LLM依赖）
            detection = self.l0_engine.detect_anomalies(system_info)
            write_key = f"ANOMALY_DETECT.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.writer.write(write_key, detection, category="anomaly_detection")
            self.audit.log("anomaly_detection", detection)
            self.state.increment("success_count")
            self.state.increment("truths_written")
            status = detection.get("overall_status", "未知")
            logger.info(f"异常检测完成（L0规则引擎）: 整体状态={status}, 内存={mem_usage_percent}%, 磁盘={disk_usage_percent}%")
        except Exception as e:
            logger.error(f"L0规则引擎异常检测失败: {e}")
            self.state.increment("error_count")'''

if old_anomaly in content:
    content = content.replace(old_anomaly, new_anomaly)
    print("✅ 已替换异常检测任务")
else:
    print("⚠️ 异常检测任务未找到（可能已被修改）")

# 6. 替换真值去重任务
old_dedup = '''    def task_truth_dedup(self):
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

        system_prompt = "你是一个真值去重专家。分析以下真值组，建议哪些可以合并、哪些是冗余的。输出JSON：{\\"merge_suggestions\\":[{\\"group\\":\\"...\\",\\"keys\\":[\\"...\\"],\\"reason\\":\\"...\\",\\"merged_summary\\":\\"...\\"}], \\"redundant_keys\\":[\\"...\\"]}"
        user_prompt = f"分析以下重复候选组：\\n" + "\\n".join(dup_summary)

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
            self.state.increment("error_count")'''

new_dedup = '''    def task_truth_dedup(self):
        """任务6：真值去重合并（每天）— L0规则引擎"""
        logger.info("=== 执行任务：真值去重合并（L0规则引擎） ===")
        truths = self.writer.get_recent_truths(50)
        if len(truths) < 5:
            logger.info("真值不足，跳过去重")
            return

        try:
            # 使用L0规则引擎去重（零LLM依赖）
            dedup = self.l0_engine.dedup_truths(truths)
            write_key = f"TRUTH_DEDUP.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.writer.write(write_key, dedup, category="truth_dedup")
            self.audit.log("truth_dedup", dedup)
            self.state.increment("success_count")
            self.state.increment("truths_written")
            logger.info(f"去重分析完成（L0规则引擎）: {len(dedup.get('merge_suggestions', []))}个合并建议, {len(dedup.get('redundant_keys', []))}个冗余key")
        except Exception as e:
            logger.error(f"L0规则引擎去重失败: {e}")
            self.state.increment("error_count")'''

if old_dedup in content:
    content = content.replace(old_dedup, new_dedup)
    print("✅ 已替换真值去重任务")
else:
    print("⚠️ 真值去重任务未找到（可能已被修改）")

# 7. 更新文件头注释
content = content.replace(
    "  1. 双轮算力路由：简单任务→本地小模型，复杂任务→外部API",
    "  1. L0规则引擎+外部API混合架构：4类简单任务→L0规则引擎（零LLM），2类复杂任务→外部API"
)
content = content.replace(
    "     - 真值语义分类（每15分钟）\n     - 冲突语义检测（每30分钟）\n     - 日志摘要提炼（每小时）\n     - 异常模式检测（每小时）\n     - 自状态反思（每2小时）\n     - 真值去重合并（每天）",
    "     - 真值语义分类（每15分钟）→ L0规则引擎\n     - 冲突语义检测（每30分钟）→ L0规则引擎\n     - 日志摘要提炼（每小时）→ 外部API\n     - 异常模式检测（每小时）→ L0规则引擎\n     - 自状态反思（每2小时）→ 外部API\n     - 真值去重合并（每天）→ L0规则引擎"
)

# 写入文件
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ MR-010调度器修改完成！")
print("   - 4类任务已替换为L0规则引擎（真值分类/冲突检测/异常检测/真值去重）")
print("   - 2类任务保留外部API（日志摘要/自状态反思）")
print("   - 本地LLM仅在外部API失败时作为兜底")
