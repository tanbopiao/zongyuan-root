#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — 云端全量真值拉取引擎 V7

从云端中枢 (huodouai.com/api/truth) 拉取全量真值，补全本地根内核。

策略：
  1. 按 key 前缀递归钻取：当前缀返回满200条时，按子前缀继续拆分
  2. 合并到本地已有真值（按 seq 去重）
  3. 生成拉取报告（新增数、总数、覆盖率）
"""
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from collections import Counter

# ============ 配置 ============
HUB = "https://www.huodouai.com/api/truth"
DID = "DID-BR-000002"
LIMIT = 200
ALL_TRUTHS_FILE = Path("/workspace/persistence_root/all_truths.json")
REPORT_DIR = Path("/workspace/evolution/kernel_comparison")
REPORT_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = Path("/workspace/persistence_root/pull_v7.log")
OUT_REPORT = REPORT_DIR / "pull_report.json"

# ============ 日志 ============
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ============ HTTP ============
def fetch(prefix="", max_retries=2):
    url = f"{HUB}?limit={LIMIT}"
    if prefix:
        url += f"&key={prefix}"
    for attempt in range(max_retries + 1):
        try:
            r = subprocess.run(
                ["/usr/bin/curl", "-s", url, "-H", f"X-DID: {DID}", "--max-time", "30"],
                capture_output=True, text=True, timeout=35
            )
            data = json.loads(r.stdout)
            return data.get("results", [])
        except Exception:
            if attempt < max_retries:
                time.sleep(0.5)
    return []

def get_hub_status():
    """获取云端中枢状态"""
    try:
        r = subprocess.run(
            ["/usr/bin/curl", "-s", "https://www.huodouai.com/api/status",
             "-H", f"X-DID: {DID}", "--max-time", "10"],
            capture_output=True, text=True, timeout=15
        )
        return json.loads(r.stdout)
    except Exception:
        return {}

def get_prefixes(truths, depth=1):
    """从真值列表提取下一级前缀"""
    prefixes = set()
    for t in truths:
        key = t.get("key", "")
        parts = re_split(key)
        if len(parts) > depth:
            prefix = "".join(parts[:depth+1])
            prefixes.add(prefix)
    return sorted(prefixes)

def re_split(key):
    """按多种分隔符拆分 key"""
    import re
    parts = re.split(r'[._\-]', key)
    return parts

def recursive_pull(all_truths, prefix="", depth=0, max_depth=4):
    """递归拉取：当前缀满200时，按子前缀钻取"""
    results = fetch(prefix)
    new_count = 0
    for t in results:
        seq = t.get("seq")
        if seq and seq not in all_truths:
            all_truths[seq] = t
            new_count += 1

    if len(results) >= LIMIT and depth < max_depth:
        # 满了，需要按子前缀钻取
        # 提取子前缀
        sub_prefixes = set()
        for t in results:
            key = t.get("key", "")
            parts = re_split(key)
            if len(parts) > depth + 1:
                sub = ".".join(parts[:depth+2]) if "." in key else parts[depth+1]
                # 用原始 key 的前缀
                idx = 0
                for sep in [".", "_", "-"]:
                    if sep in key:
                        idx = key.find(sep, idx+1) if depth > 0 else key.find(sep)
                        break
                # 简单方式：用 key 的前 N 个字符作为子前缀
                pass
        # 更简单的方式：按 key 第一段 + 第二段组合
        first_parts = set()
        for t in results:
            key = t.get("key", "")
            parts = re_split(key)
            if len(parts) > 1:
                first_parts.add(parts[0])

        for fp in sorted(first_parts):
            sub_prefix = fp if not prefix else prefix
            # 尝试用更长的前缀
            sub_results = fetch(sub_prefix)
            if len(sub_results) >= LIMIT:
                # 还满，继续钻取
                # 按第二段拆分
                second_parts = set()
                for t in sub_results:
                    key = t.get("key", "")
                    parts = re_split(key)
                    if len(parts) > 1:
                        second_parts.add(parts[1])

                for sp in sorted(second_parts):
                    # 构建子前缀（尝试多种分隔符）
                    for sep in [".", "_", "-"]:
                        candidate = f"{first_parts and list(first_parts)[0]}{sep}{sp}" if False else f"{fp}{sep}{sp}"
                        r2 = fetch(candidate)
                        for t in r2:
                            seq = t.get("seq")
                            if seq and seq not in all_truths:
                                all_truths[seq] = t
                                new_count += 1
                        if len(r2) < LIMIT:
                            break
            else:
                for t in sub_results:
                    seq = t.get("seq")
                    if seq and seq not in all_truths:
                        all_truths[seq] = t
                        new_count += 1

    return new_count

def pull_by_all_prefixes(all_truths):
    """按所有已知前缀系统拉取"""
    # 全量已知前缀列表
    known_prefixes = [
        "REPORT", "TRUTH", "BOOTSTRAP", "website", "kernel", "cloud",
        "AUTO-TRUTH-PIPELINE", "yuanji", "DEPLOY", "EVOLUTION",
        "GASA-INVARIANTS", "P1P2", "COMPARE", "UPGRADE", "PROBE",
        "DEEPSCAN", "SCAN", "META", "NODE", "seed", "node",
        "truth-", "meta", "kernel", "zongyuan", "SFMP",
        "hub", "ARB", "HZ", "DID", "ANCHOR",
        "FOUR-ROUND", "FIFTH-ROUND", "SIXTH-ROUND", "SEVENTH-ROUND",
        "COSMIC", "BRAIN", "SHARED", "UNIVERSAL",
        "DARWIN", "GOD", "HUMAN", "AI",
        "CONSCIOUSNESS", "CONSCIOUS", "MIND",
        "LAW", "RULE", "POLICY",
        "DATA", "MARKET", "AGENT",
        "COMPLIANCE", "DRAMA", "FEDERATION",
        "KNOWLEDGE", "GRAPH", "INTELLIGENCE",
        "TRAINING", "MODEL", "SFT",
        "BACKUP", "ARCHIVE", "SNAPSHOT",
        "HEARTBEAT", "NTFY", "STATUS",
        "PROTOCOL", "HANDSHAKE", "REGISTRY",
        "TEST", "DEBUG", "LOG",
        "OPS", "MONITOR", "ALERT",
    ]

    total_new = 0
    for prefix in known_prefixes:
        results = fetch(prefix)
        new = 0
        for t in results:
            seq = t.get("seq")
            if seq and seq not in all_truths:
                all_truths[seq] = t
                new += 1
        total_new += new
        if new > 0 or len(results) > 0:
            log(f"  前缀 '{prefix}': {len(results)} 条拉取, {new} 新增 (累计 {len(all_truths)})")

        # 满了则按子前缀钻取
        if len(results) >= LIMIT:
            sub_new = drill_down(all_truths, prefix, results)
            total_new += sub_new

    return total_new

def drill_down(all_truths, prefix, results):
    """对满200的前缀进行子前缀钻取"""
    new_total = 0
    # 提取每个 key 的第二段
    import re
    second_segments = set()
    for t in results:
        key = t.get("key", "")
        parts = re.split(r'[._\-]', key)
        if len(parts) > 1:
            second_segments.add(parts[1])

    for seg in sorted(second_segments):
        # 尝试不同分隔符组合
        for sep in [".", "_", "-"]:
            candidate = f"{prefix}{sep}{seg}"
            r2 = fetch(candidate)
            new = 0
            for t in r2:
                seq = t.get("seq")
                if seq and seq not in all_truths:
                    all_truths[seq] = t
                    new += 1
            new_total += new
            if new > 0:
                log(f"    子前缀 '{candidate}': +{new} (累计 {len(all_truths)})")

            # 如果子前缀也满了，继续钻取第三段
            if len(r2) >= LIMIT:
                third_segs = set()
                for t in r2:
                    key = t.get("key", "")
                    parts = re.split(r'[._\-]', key)
                    if len(parts) > 2:
                        third_segs.add(parts[2])
                for seg3 in sorted(third_segs):
                    for sep3 in [".", "_", "-"]:
                        candidate3 = f"{candidate}{sep3}{seg3}"
                        r3 = fetch(candidate3)
                        new3 = 0
                        for t in r3:
                            seq = t.get("seq")
                            if seq and seq not in all_truths:
                                all_truths[seq] = t
                                new3 += 1
                        new_total += new3
                        if new3 > 0:
                            log(f"      孙前缀 '{candidate3}': +{new3} (累计 {len(all_truths)})")
                        if len(r3) < LIMIT:
                            break
            if len(r2) < LIMIT:
                break

    return new_total

def pull_by_seq_range(all_truths, hub_count):
    """尝试通过 seq 范围拉取（从最新到最旧）"""
    # API 返回最新优先，尝试拉取不同 seq 区间
    # 通过 key 参数尝试 truth- 前缀的不同时间戳
    log("拉取 truth- 时间戳前缀...")
    for ts in range(1791380, 1791450):
        results = fetch(f"truth-{ts}")
        new = 0
        for t in results:
            seq = t.get("seq")
            if seq and seq not in all_truths:
                all_truths[seq] = t
                new += 1
        if new > 0:
            log(f"  truth-{ts}: +{new} (累计 {len(all_truths)})")
        time.sleep(0.05)

def main():
    log("=" * 60)
    log("云端全量真值拉取引擎 V7 启动")
    log("=" * 60)

    # 1. 获取云端状态
    hub_status = get_hub_status()
    hub_count = hub_status.get("truth_count", 0)
    log(f"云端中枢真值总数: {hub_count}")
    log(f"中枢版本: {hub_status.get('version')}, Merkle: {hub_status.get('merkle_root','')[:16]}...")

    # 2. 加载本地已有真值
    all_truths = {}
    if ALL_TRUTHS_FILE.exists():
        existing = json.loads(ALL_TRUTHS_FILE.read_text(encoding="utf-8"))
        for t in existing:
            all_truths[t["seq"]] = t
    log(f"本地已有真值: {len(all_truths)}")

    # 3. 系统性拉取
    log("开始按前缀系统拉取...")
    new_from_prefixes = pull_by_all_prefixes(all_truths)
    log(f"前缀拉取新增: {new_from_prefixes}, 累计: {len(all_truths)}")

    # 4. 时间戳前缀拉取
    new_from_ts = pull_by_seq_range(all_truths, hub_count)
    log(f"时间戳拉取新增, 累计: {len(all_truths)}")

    # 5. 最终状态
    truths = sorted(all_truths.values(), key=lambda x: x["seq"], reverse=True)
    ALL_TRUTHS_FILE.write_text(json.dumps(truths, ensure_ascii=False, indent=2), encoding="utf-8")
    seqs = [t["seq"] for t in truths]
    file_size = ALL_TRUTHS_FILE.stat().st_size / 1024

    coverage = round(len(truths) / max(1, hub_count) * 100, 1)
    log(f"完成: {len(truths)} 条真值, seq {min(seqs)}~{max(seqs)}, {file_size:.0f}KB")
    log(f"覆盖率: {coverage}% ({len(truths)}/{hub_count})")

    # 6. 保存报告
    report = {
        "pull_time": datetime.now().isoformat(),
        "hub_truth_count": hub_count,
        "local_before": len(all_truths) - new_from_prefixes,
        "local_after": len(truths),
        "new_pulled": len(truths) - (len(all_truths) - new_from_prefixes),
        "coverage_pct": coverage,
        "seq_range": [min(seqs), max(seqs)],
        "merkle_root": hub_status.get("merkle_root", ""),
        "hub_version": hub_status.get("version"),
    }
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"报告已保存: {OUT_REPORT}")
    log("=" * 60)
    return len(truths)

if __name__ == "__main__":
    print(f"\n完成: {main()} 条")
