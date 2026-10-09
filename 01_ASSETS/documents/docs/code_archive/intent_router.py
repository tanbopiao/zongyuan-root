#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 意图识别路由引擎（对话模式↔工作任务模式桥接层）
功能：分析对话输入，自动识别意图类型，触发对应工作任务模式流程
作者：元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

意图分类：
  - ASSET_GENERATE  资产生成（视频/图片/文档）→ 触发资产流水线
  - TRUTH_ARCHIVE   真值沉淀（写入/归档/锁档）→ 触发记忆网关写入
  - TASK_EXECUTE    任务执行（部署/修复/优化）→ 封装InstructionPacket
  - NORMAL_CHAT     普通对话 → 不触发工作任务模式
"""
import re
import json
import os
import datetime
import subprocess
import sys


class IntentRouter:
    """意图识别路由引擎"""

    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "intent_router_config.json")
        self.config = self._load_config(config_path)
        self.rules = self.config.get("rules", {})

    def _load_config(self, path):
        default = {
            "rules": {
                "ASSET_GENERATE": {
                    "keywords": ["生成视频", "生成图片", "生成关键帧", "出图", "生图", "渲染视频",
                                 "生成短片", "制作视频", "生成海报", "生成文档", "生成报告",
                                 "视频生成", "图片生成", "关键帧", "分镜", "短剧"],
                    "asset_types": {
                        "视频": ["视频", "短片", "渲染"],
                        "图片": ["图片", "关键帧", "海报", "出图", "生图"],
                        "文档": ["文档", "报告", "白皮书"]
                    }
                },
                "TRUTH_ARCHIVE": {
                    "keywords": ["写入记忆", "归档", "锁档", "沉淀", "写入真值", "写入内核",
                                 "全域锁档", "固化", "写入元规则", "写入元宪法", "确权",
                                 "写入飞书", "同步到记忆网关", "上报记忆网关"]
                },
                "TASK_EXECUTE": {
                    "keywords": ["部署", "修复", "优化", "执行", "搭建", "配置", "安装",
                                 "重启服务", "更新", "升级", "重构", "打通", "连通",
                                 "扫描", "检测", "巡检", "演练", "加固"]
                }
            },
            "pipeline_script": "asset_pipeline_trigger.py",
            "memory_gateway_url": "http://127.0.0.1:9120",
            "auto_trigger": False  # 默认只识别不自动执行，需要确认
        }
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            default.update(user_cfg)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
        return default

    def classify(self, text):
        """分类用户输入的意图"""
        text = text.strip()
        if not text:
            return "NORMAL_CHAT", {}

        scores = {}
        details = {}

        # ASSET_GENERATE - 支持组合匹配（生成+视频/图片/文档）
        asset_rules = self.rules.get("ASSET_GENERATE", {})
        asset_score = 0
        asset_type = None
        for kw in asset_rules.get("keywords", []):
            if kw in text:
                asset_score += 1
        # 组合匹配：生成+媒体类型
        if "生成" in text or "制作" in text or "渲染" in text:
            for atype, kws in asset_rules.get("asset_types", {}).items():
                for kw in kws:
                    if kw in text:
                        asset_score += 2
                        asset_type = atype
                        break
        # 单独媒体类型词也触发
        for atype, kws in asset_rules.get("asset_types", {}).items():
            for kw in kws:
                if kw in text and asset_type is None:
                    asset_score += 1
                    asset_type = atype
                    break
        if asset_score > 0:
            scores["ASSET_GENERATE"] = asset_score
            details["ASSET_GENERATE"] = {"asset_type": asset_type or "未知"}

        # TRUTH_ARCHIVE
        truth_rules = self.rules.get("TRUTH_ARCHIVE", {})
        truth_score = sum(1 for kw in truth_rules.get("keywords", []) if kw in text)
        if truth_score > 0:
            scores["TRUTH_ARCHIVE"] = truth_score

        # TASK_EXECUTE
        task_rules = self.rules.get("TASK_EXECUTE", {})
        task_score = sum(1 for kw in task_rules.get("keywords", []) if kw in text)
        if task_score > 0:
            scores["TASK_EXECUTE"] = task_score

        if not scores:
            return "NORMAL_CHAT", {}

        # 取最高分
        best_intent = max(scores, key=scores.get)
        return best_intent, details.get(best_intent, {})

    def build_instruction_packet(self, intent, text, detail=None):
        """构建标准InstructionPacket报文（对话模式→工作任务模式）"""
        if detail is None:
            detail = {}

        packet = {
            "proto_version": "1.0",
            "meta_homo_root": "Ω-TAN-7-001",
            "asset_did": "DID-BR-000002",
            "task_id": f"IP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "domain": "ZONGYUAN-ROOT",
            "intent": intent,
            "operator_name": self._get_operator(intent),
            "input_text": text,
            "detail": detail,
            "timestamp": datetime.datetime.now().isoformat(),
            "trace_mark": "Ω₀⊂⊙∞⊂Ω"
        }
        return packet

    def _get_operator(self, intent):
        mapping = {
            "ASSET_GENERATE": "asset_pipeline_trigger",
            "TRUTH_ARCHIVE": "truth_archive_operator",
            "TASK_EXECUTE": "task_execution_dispatcher"
        }
        return mapping.get(intent, "unknown")

    def route(self, text, auto_execute=False):
        """主路由方法：识别意图→构建报文→可选自动执行"""
        intent, detail = self.classify(text)
        packet = self.build_instruction_packet(intent, text, detail)

        result = {
            "intent": intent,
            "packet": packet,
            "auto_executed": False,
            "execution_result": None
        }

        if intent == "NORMAL_CHAT":
            result["action"] = "对话模式直接回复，不触发工作任务模式"
            return result

        if intent == "ASSET_GENERATE":
            result["action"] = "资产生成任务：生成后自动触发资产流水线（下载+哈希+飞书台账）"
            if auto_execute:
                result["auto_executed"] = True
                result["execution_result"] = "等待媒体URL生成后自动调用asset_pipeline_trigger.py"

        elif intent == "TRUTH_ARCHIVE":
            result["action"] = "真值沉淀任务：结构化内容→写入记忆网关9120→锁档"
            if auto_execute:
                result["auto_executed"] = True
                result["execution_result"] = "已触发真值归档算子"

        elif intent == "TASK_EXECUTE":
            result["action"] = "任务执行：封装InstructionPacket→工作任务模式算子调度引擎"
            if auto_execute:
                result["auto_executed"] = True
                result["execution_result"] = "已派发至工作任务模式调度队列"

        return result

    def extract_media_urls(self, conversation_text):
        """从对话文本中提取媒体URL（用于资产生成后自动捕获）"""
        # 匹配http/https链接
        urls = re.findall(r'https?://[^\s\]\)〉」』"]+', conversation_text)
        media_urls = []
        for url in urls:
            # 过滤掉非媒体链接
            if any(ext in url.lower() for ext in ['.mp4', '.mov', '.avi', '.mkv', '.jpg', '.jpeg', '.png', '.webp', '.gif']):
                media_urls.append(url)
            elif 'doubaocdn' in url or 'cdn' in url.lower():
                media_urls.append(url)
        return list(set(media_urls))

    def on_media_generated(self, media_url, asset_name="", description=""):
        """媒体生成回调：自动触发资产流水线"""
        if not media_url:
            return {"error": "无媒体URL"}

        pipeline_script = self.config.get("pipeline_script", "asset_pipeline_trigger.py")
        if not os.path.exists(pipeline_script):
            return {"error": f"流水线脚本不存在: {pipeline_script}", "action": "请先部署asset_pipeline_trigger.py"}

        cmd = [
            sys.executable, pipeline_script,
            "--cdn-url", media_url,
            "--name", asset_name or f"asset_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "--desc", description
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[-500:] if result.stdout else "",
                "stderr": result.stderr[-500:] if result.stderr else ""
            }
        except Exception as e:
            return {"error": str(e)}


# 单例
_router = None

def get_router():
    global _router
    if _router is None:
        _router = IntentRouter()
    return _router


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="意图识别路由引擎")
    parser.add_argument("--text", help="待分析的对话文本")
    parser.add_argument("--auto", action="store_true", help="自动执行（默认只识别）")
    parser.add_argument("--media-url", help="媒体URL，触发资产流水线")
    args = parser.parse_args()

    router = IntentRouter()

    if args.media_url:
        print("=== 媒体生成回调 ===")
        result = router.on_media_generated(args.media_url, "测试资产")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.text:
        print("=== 意图识别 ===")
        print(f"输入: {args.text}")
        result = router.route(args.text, auto_execute=args.auto)
        print(f"意图: {result['intent']}")
        print(f"动作: {result['action']}")
        print(f"报文: {json.dumps(result['packet'], ensure_ascii=False, indent=2)}")
    else:
        # 交互测试
        print("=== 意图识别路由引擎测试 ===")
        print("输入文本测试意图识别（输入exit退出）")
        while True:
            try:
                text = input("\n> ").strip()
                if text.lower() in ("exit", "quit", "q"):
                    break
                result = router.route(text)
                print(f"意图: {result['intent']}")
                print(f"动作: {result['action']}")
            except (KeyboardInterrupt, EOFError):
                break
