#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS 种子真值提炼引擎
功能：全网抓取 → 种子真值提炼 → 校验过滤 → 归档持久层 → 上报网关

核心机制（来自经验 2040765）：
1. 长耗时任务加并发锁，防止重复触发
2. 密钥走环境变量，不硬编码
3. 每步输出可观测日志，宣称完成前有证据
4. 分三类权限：模型工具权限、宿主网络出口、本地文件写权限

执行流程：
  1. 抓取全网信息（WebSearch / 外部搜索 API）
  2. 用大模型提炼种子真值（调用外部 API）
  3. 合规校验（去重、风险过滤、溯源检查）
  4. 归档到本地持久层（解锁→写入→重新锁档）
  5. 上报到真值网关（双活端点）
"""
import os
import sys
import json
import time
import hashlib
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# ============ 路径配置 ============

WORKSPACE = Path("/workspace")
EVOLUTION_DIR = WORKSPACE / "evolution"
EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = EVOLUTION_DIR / "evolution.log"
SEED_TRUTH_FILE = EVOLUTION_DIR / "seed_truths.jsonl"
STATE_FILE = EVOLUTION_DIR / "state.json"

PERSISTENCE_SCRIPT = WORKSPACE / "scripts" / "services"

# 将持久层引擎目录加入 path
sys.path.insert(0, str(PERSISTENCE_SCRIPT))

# ============ 并发锁 ============

_evolve_lock = threading.Lock()
_is_evolving = False

# ============ DID 标识 ============

DID_TAG = "DID-BR-000002"
ARCHIVE_NODE = "ZONGYUAN-ROOT"

# ============ 真值网关 ============

TRUTH_GATEWAY_PRIMARY = "https://www.huodouai.com/api/report/truth"
TRUTH_GATEWAY_BACKUP = "https://drama.huodouai.com/api/report/truth"

# ============ 搜索关键词列表（可扩展） ============

SEARCH_KEYWORDS = [
    "人工智能 大模型 最新进展",
    "智能体自治 平台 架构",
    "企业知识库 RAG 最佳实践",
    "AI 合规 内容安全 监管",
    "智能体编排 多智能体协作",
    "向量数据库 企业级 部署",
    "AI Agent 权限控制 安全",
    "大模型 推理成本 优化",
]


def log(level: str, message: str):
    """统一日志输出。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def load_state() -> Dict[str, Any]:
    """加载进化状态。"""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "last_run": None,
        "total_extractions": 0,
        "total_archived": 0,
        "total_reported": 0,
        "failed_runs": 0,
        "last_keyword_index": 0,
    }


def save_state(state: Dict[str, Any]):
    """保存进化状态。"""
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_truth_id(category: str, content: str) -> str:
    """根据内容哈希生成真值编号。"""
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8].upper()
    return f"HZ-TV-SEED-{category[:2].upper()}-{content_hash}"


def fetch_web_information(keyword: str) -> List[Dict[str, Any]]:
    """
    从全网抓取信息。
    
    优先级：
    1. 环境变量配置的搜索 API（如 Tavily、SerpAPI）
    2. 降级到本地知识缓存（首次运行无缓存则返回空）
    
    注意：宿主网络出口可能受限，需做降级处理。
    """
    results = []

    # 尝试使用配置的搜索 API
    search_api_key = os.getenv("SEARCH_API_KEY", "")
    search_api_url = os.getenv("SEARCH_API_URL", "")

    if search_api_key and search_api_url:
        try:
            import requests
            resp = requests.post(
                search_api_url,
                json={"query": keyword, "max_results": 5},
                headers={"Authorization": f"Bearer {search_api_key}"},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "source": "web_search_api",
                    })
                log("INFO", f"搜索 API 返回 {len(results)} 条结果: {keyword}")
                return results
        except Exception as e:
            log("WARN", f"搜索 API 调用失败: {e}，降级处理")

    # 降级：返回空，由调用方处理
    log("INFO", f"无可用搜索 API，跳过关键词: {keyword}")
    return results


def extract_seed_truths(raw_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    从原始信息中提炼种子真值。
    
    优先使用外部大模型 API 提炼，降级到基于规则的关键词提取。
    """
    seed_truths = []

    # 检查是否有可用的大模型 API
    has_llm = any([
        os.getenv("DASHSCOPE_API_KEY"),
        os.getenv("DEEPSEEK_API_KEY"),
        os.getenv("COZE_PAT"),
    ])

    if has_llm and raw_info:
        # 使用大模型提炼
        try:
            import requests

            # 拼接原始信息
            context = "\n\n".join([
                f"【{item.get('title', '')}】\n{item.get('content', '')[:500]}"
                for item in raw_info[:5]
            ])

            prompt = f"""请从以下信息中提炼出可作为企业知识库种子真值的关键知识点。
要求：
1. 提炼 3-5 条核心知识点
2. 每条知识点包含：知识点名称、内容摘要、来源依据
3. 只提炼事实性信息，不加入主观判断
4. 如果信息中无有效知识点，返回空

信息内容：
{context}

请以 JSON 数组格式返回：
[{{"name": "知识点名称", "content": "内容摘要", "source": "来源依据"}}]"""

            # 尝试调用通义千问
            api_key = os.getenv("DASHSCOPE_API_KEY")
            if api_key:
                resp = requests.post(
                    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": "qwen-turbo", "messages": [{"role": "user", "content": prompt}]},
                    timeout=60,
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    # 解析 JSON
                    json_start = content.find("[")
                    json_end = content.rfind("]") + 1
                    if json_start >= 0 and json_end > json_start:
                        extracted = json.loads(content[json_start:json_end])
                        for item in extracted:
                            seed_truths.append({
                                "name": item.get("name", ""),
                                "content": item.get("content", ""),
                                "source": item.get("source", ""),
                                "extract_method": "llm",
                            })
                    log("INFO", f"大模型提炼出 {len(seed_truths)} 条种子真值")
        except Exception as e:
            log("WARN", f"大模型提炼失败: {e}，降级到规则提取")

    # 降级：基于规则的简单提取
    if not seed_truths and raw_info:
        log("INFO", "使用规则提取种子真值")
        for item in raw_info[:3]:
            content = item.get("content", "")
            if len(content) > 50:
                # 取前 200 字作为种子真值摘要
                seed_truths.append({
                    "name": item.get("title", "未命名知识点"),
                    "content": content[:200] + ("..." if len(content) > 200 else ""),
                    "source": item.get("url", "unknown"),
                    "extract_method": "rule",
                })

    return seed_truths


def validate_seed_truth(truth: Dict[str, Any]) -> Dict[str, Any]:
    """
    校验种子真值。
    
    校验规则：
    1. 内容非空且长度 > 20
    2. 不含禁用词（绝对化、收益承诺等）
    3. 来源可追溯（有 URL 或明确来源）
    4. 风险等级判定
    """
    banned_words = ["唯一", "最强", "绝对", "永久", "百分百", "保证收益", "稳赚", "无幻觉", "永不出错"]

    content = truth.get("content", "")
    name = truth.get("name", "")
    source = truth.get("source", "")

    # 基础校验
    if len(content) < 20 or not name:
        truth["valid"] = False
        truth["reject_reason"] = "内容过短或名称为空"
        return truth

    # 禁用词检测
    for word in banned_words:
        if word in content or word in name:
            truth["valid"] = False
            truth["reject_reason"] = f"含禁用词: {word}"
            return truth

    # 来源校验
    if not source or source == "unknown":
        truth["source_verified"] = False
        truth["review_required"] = True
    else:
        truth["source_verified"] = True
        truth["review_required"] = False

    # 风险等级判定
    high_risk_keywords = ["法律", "医疗", "金融", "投资", "收益", "合同", "监管"]
    if any(kw in content for kw in high_risk_keywords):
        truth["risk_level"] = "高风险"
        truth["review_required"] = True
    else:
        truth["risk_level"] = "中风险"

    truth["valid"] = True
    truth["did_tag"] = DID_TAG
    truth["archive_node"] = ARCHIVE_NODE
    truth["extracted_at"] = datetime.now().isoformat()

    return truth


def archive_seed_truth(truth: Dict[str, Any]) -> bool:
    """
    将种子真值归档到持久层。
    
    流程：解锁 → 写入 → 重新锁档
    """
    try:
        from persistence_manager import PersistenceManager

        pm = PersistenceManager()

        # 如果已锁档，先解锁
        was_locked = pm.is_locked()
        if was_locked:
            pm.unlock()
            log("INFO", "持久层已解锁，准备写入种子真值")

        # 写入
        truth_id = generate_truth_id("seed", truth["content"])
        content = f"### {truth_id} {truth['name']}\n\n"
        content += f"**内容**：{truth['content']}\n\n"
        content += f"**来源**：{truth.get('source', '待核验')}\n\n"
        content += f"**提炼方式**：{truth.get('extract_method', 'unknown')}\n\n"
        content += f"**风险等级**：{truth.get('risk_level', '中风险')}\n\n"
        content += f"**审核状态**：草稿（需人工复核）\n\n"
        content += f"**提炼时间**：{truth['extracted_at']}\n"

        result = pm.write_truth(
            truth_id=truth_id,
            category="tech",
            content=content,
            metadata={
                "version": "V1.0",
                "risk_level": truth.get("risk_level", "中风险"),
                "review_status": "草稿",
            },
        )

        # 重新锁档
        if was_locked:
            pm.lock(lock_version="V2.0")
            log("INFO", "持久层已重新锁档")

        log("INFO", f"种子真值已归档: {truth_id}")
        return True

    except Exception as e:
        log("ERROR", f"归档失败: {e}")
        return False


def report_to_gateway(truth: Dict[str, Any]) -> bool:
    """
    上报种子真值到双活网关。

    口径（RULE-005 V3.1，2026-10-19 实测修正）：
      - key：命名空间点分，禁 truth- 前缀；value：必须 JSON 对象；
      - 旧 truth_id/content/truth_value 顶层字段已废止（empty_value_rejected 400）；
      - 非 200 响应不再静默跳过，必须留日志（原缺陷导致"上报0"无痕迹）。
    """
    try:
        import hashlib
        import requests

        truth_id = generate_truth_id("seed", truth["content"])
        payload = {
            "key": f"KERNEL.EVOLUTION.SEED.{hashlib.sha256(truth['content'].encode()).hexdigest()[:10].upper()}",
            "value": {
                "truth_id": truth_id,
                "name": truth.get("name", ""),
                "content": truth.get("content", ""),
                "source": truth.get("source", ""),
                "risk_level": truth.get("risk_level", "中风险"),
                "did_tag": DID_TAG,
                "archive_node": ARCHIVE_NODE,
                "reported_at": datetime.now().isoformat(),
            },
            "truth_type": "data",
        }

        success = False
        for url in [TRUTH_GATEWAY_PRIMARY, TRUTH_GATEWAY_BACKUP]:
            try:
                resp = requests.post(
                    url,
                    json=payload,
                    headers={"X-DID": DID_TAG, "Content-Type": "application/json"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    success = True
                    log("INFO", f"真值上报成功: {truth_id} -> {url}")
                    break
                else:
                    # 留痕：重复 key(防覆盖 400) 视为已存在；其余为真实失败
                    body = resp.text[:200]
                    already = "duplicate" in body or "已存在" in body
                    log("WARN" if not already else "INFO",
                        f"上报非200({resp.status_code}) {'重复key视为在位' if already else '失败'} {url}: {body}")
                    if already:
                        success = True
                        break
            except Exception as e:
                log("WARN", f"上报失败 {url}: {e}")

        return success

    except Exception as e:
        log("ERROR", f"上报异常: {e}")
        return False


def run_evolution_cycle():
    """
    执行一次完整的进化周期。
    
    加并发锁，防止重复触发。
    """
    global _is_evolving

    # 并发锁
    if not _evolve_lock.acquire(blocking=False):
        log("WARN", "进化任务正在执行中，跳过本次触发")
        return

    _is_evolving = True
    start_time = time.time()

    try:
        log("INFO", "=" * 50)
        log("INFO", "种子真值进化周期开始")
        log("INFO", "=" * 50)

        state = load_state()

        # 1. 选择本轮搜索关键词（轮询）
        keyword_index = state.get("last_keyword_index", 0) % len(SEARCH_KEYWORDS)
        keyword = SEARCH_KEYWORDS[keyword_index]
        state["last_keyword_index"] = keyword_index + 1

        log("INFO", f"本轮搜索关键词: {keyword}")

        # 2. 全网抓取
        raw_info = fetch_web_information(keyword)
        log("INFO", f"抓取到 {len(raw_info)} 条原始信息")

        if not raw_info:
            log("INFO", "无原始信息，跳过提炼")
            state["last_run"] = datetime.now().isoformat()
            save_state(state)
            return

        # 3. 提炼种子真值
        seed_truths = extract_seed_truths(raw_info)
        log("INFO", f"提炼出 {len(seed_truths)} 条种子真值")

        # 4. 校验 + 归档 + 上报
        archived_count = 0
        reported_count = 0

        for truth in seed_truths:
            # 校验
            validated = validate_seed_truth(truth)
            if not validated.get("valid"):
                log("INFO", f"种子真值被拒绝: {validated.get('reject_reason', '未知原因')}")
                continue

            # 归档
            if archive_seed_truth(validated):
                archived_count += 1

            # 上报
            if report_to_gateway(validated):
                reported_count += 1

            # 写入种子真值记录文件
            with open(SEED_TRUTH_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(validated, ensure_ascii=False) + "\n")

        # 5. 更新状态
        state["last_run"] = datetime.now().isoformat()
        state["total_extractions"] += len(seed_truths)
        state["total_archived"] += archived_count
        state["total_reported"] += reported_count
        save_state(state)

        elapsed = round(time.time() - start_time, 2)
        log("INFO", f"进化周期完成，耗时 {elapsed}s")
        log("INFO", f"提炼: {len(seed_truths)}, 归档: {archived_count}, 上报: {reported_count}")

    except Exception as e:
        log("ERROR", f"进化周期异常: {e}")
        state = load_state()
        state["failed_runs"] = state.get("failed_runs", 0) + 1
        save_state(state)

    finally:
        _is_evolving = False
        _evolve_lock.release()


def archive_from_session(seed_truths: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    会话 API 模式：接收会话 WebSearch 提炼的种子真值，批量归档。

    与会话配合的工作流：
    1. 会话使用 WebSearch 抓取全网信息
    2. 会话用自身 LLM 能力提炼种子真值
    3. 调用本函数批量校验+归档+上报

    参数:
        seed_truths: 种子真值列表，每条含 name/content/source/category/risk_level
    """
    global _is_evolving

    if not _evolve_lock.acquire(blocking=False):
        return {"success": False, "message": "进化任务正在执行中，请稍后重试"}

    _is_evolving = True
    result = {"success": True, "archived": 0, "reported": 0, "rejected": 0, "details": []}

    try:
        log("INFO", "=" * 50)
        log("INFO", f"会话 API 模式进化开始，输入 {len(seed_truths)} 条种子真值")
        log("INFO", "=" * 50)

        for truth in seed_truths:
            # 校验
            validated = validate_seed_truth(truth)
            if not validated.get("valid"):
                result["rejected"] += 1
                result["details"].append({
                    "name": truth.get("name", ""),
                    "rejected": True,
                    "reason": validated.get("reject_reason", "未知原因"),
                })
                log("INFO", f"拒绝: {truth.get('name', '')[:30]} - {validated.get('reject_reason')}")
                continue

            # 设置类别（支持自定义）
            category = validated.get("category", "tech")

            # 归档
            if archive_seed_truth_with_category(validated, category):
                result["archived"] += 1

            # 上报
            if report_to_gateway(validated):
                result["reported"] += 1

            # 写入记录
            with open(SEED_TRUTH_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(validated, ensure_ascii=False) + "\n")

            result["details"].append({
                "name": validated.get("name", ""),
                "archived": True,
                "category": category,
                "risk_level": validated.get("risk_level", ""),
            })

        # 更新状态
        state = load_state()
        state["last_run"] = datetime.now().isoformat()
        state["last_method"] = "session_websearch"
        state["total_extractions"] = state.get("total_extractions", 0) + len(seed_truths)
        state["total_archived"] = state.get("total_archived", 0) + result["archived"]
        state["total_reported"] = state.get("total_reported", 0) + result["reported"]
        save_state(state)

        log("INFO", f"会话模式进化完成: 归档{result['archived']}, 上报{result['reported']}, 拒绝{result['rejected']}")

    except Exception as e:
        log("ERROR", f"会话模式进化异常: {e}")
        result["success"] = False
        result["error"] = str(e)
    finally:
        _is_evolving = False
        _evolve_lock.release()

    return result


def archive_seed_truth_with_category(truth: Dict[str, Any], category: str = "tech") -> bool:
    """
    将种子真值归档到持久层（支持指定类别）。

    流程：解锁 → 写入 → 重新锁档
    """
    try:
        from persistence_manager import PersistenceManager

        pm = PersistenceManager()

        was_locked = pm.is_locked()
        if was_locked:
            pm.unlock()

        truth_id = generate_truth_id(category, truth["content"])
        content = f"### {truth_id} {truth['name']}\n\n"
        content += f"**内容**：{truth['content']}\n\n"
        content += f"**来源**：{truth.get('source', '待核验')}\n\n"
        content += f"**提炼方式**：{truth.get('extract_method', 'session_websearch')}\n\n"
        content += f"**风险等级**：{truth.get('risk_level', '中风险')}\n\n"
        content += f"**审核状态**：草稿（需人工复核）\n\n"
        content += f"**提炼时间**：{truth['extracted_at']}\n"

        result = pm.write_truth(
            truth_id=truth_id,
            category=category,
            content=content,
            metadata={
                "version": "V1.0",
                "risk_level": truth.get("risk_level", "中风险"),
                "review_status": "草稿",
            },
        )

        if was_locked:
            pm.lock(lock_version="V2.0")

        log("INFO", f"种子真值已归档: {truth_id}")
        return True

    except Exception as e:
        log("ERROR", f"归档失败: {e}")
        return False


def get_evolution_status() -> Dict[str, Any]:
    """获取进化状态。"""
    state = load_state()
    state["is_evolving"] = _is_evolving
    return state


# ============ 命令行入口 ============

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            print(json.dumps(get_evolution_status(), ensure_ascii=False, indent=2))
        elif cmd == "session":
            # 会话模式：从 stdin 读取 JSON 种子真值
            try:
                input_data = json.load(sys.stdin)
                result = archive_from_session(input_data)
                print(json.dumps(result, ensure_ascii=False, indent=2))
            except json.JSONDecodeError as e:
                print(json.dumps({"success": False, "error": f"JSON解析失败: {e}"}, ensure_ascii=False))
        else:
            run_evolution_cycle()
    else:
        run_evolution_cycle()
