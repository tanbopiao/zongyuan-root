"""
通用工具模块：日志、哈希确权、双库归档
"""
import os
import json
import hashlib
import logging
from datetime import datetime
from config.settings import LOG_DIR, DATA_DIR, DID, ANCHOR, ROOT_HASH, LOG_FORMAT, LOG_DATE_FORMAT


def setup_logger(name, log_file=None):
    """配置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    if log_file:
        fh = logging.FileHandler(os.path.join(LOG_DIR, log_file), encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger


def compute_hash(content):
    """计算SHA256哈希确权"""
    if isinstance(content, dict):
        content = json.dumps(content, ensure_ascii=False, sort_keys=True)
    elif isinstance(content, (list, tuple)):
        content = json.dumps(content, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(str(content).encode('utf-8')).hexdigest()


def generate_asset_id(prefix="ASSET"):
    """生成资产唯一ID"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{DID[-6:]}-{ts}"


def archive_to_root(asset_type, content, metadata=None):
    """归档至ROOT只读根库（模拟）"""
    asset_id = generate_asset_id(asset_type.upper())
    content_hash = compute_hash(content)
    record = {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "content_hash": content_hash,
        "root_hash": ROOT_HASH,
        "did": DID,
        "anchor": ANCHOR,
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {},
        "content": content
    }
    archive_path = os.path.join(DATA_DIR, "root_archive.json")
    archives = []
    if os.path.exists(archive_path):
        with open(archive_path, 'r', encoding='utf-8') as f:
            archives = json.load(f)
    archives.append(record)
    with open(archive_path, 'w', encoding='utf-8') as f:
        json.dump(archives, f, ensure_ascii=False, indent=2)
    return record


def archive_to_sandbox(asset_type, content, metadata=None):
    """归档至沙盒动态库（模拟）"""
    asset_id = generate_asset_id(f"SBX-{asset_type.upper()}")
    record = {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {},
        "status": "dynamic"
    }
    sandbox_path = os.path.join(DATA_DIR, "sandbox_archive.json")
    archives = []
    if os.path.exists(sandbox_path):
        with open(sandbox_path, 'r', encoding='utf-8') as f:
            archives = json.load(f)
    archives.append(record)
    with open(sandbox_path, 'w', encoding='utf-8') as f:
        json.dump(archives, f, ensure_ascii=False, indent=2)
    return record


def compliance_check(content, content_type="general"):
    """合规校验：价值观、安全、伦理"""
    issues = []
    text = json.dumps(content, ensure_ascii=False) if isinstance(content, (dict, list)) else str(content)
    # 敏感词检测（简化版）
    risk_keywords = ["暴力", "色情", "赌博", "毒品", "反动"]
    for kw in risk_keywords:
        if kw in text:
            issues.append(f"包含敏感词: {kw}")
    # AI替代人类检测
    if "AI完全替代" in text or "无需人类" in text:
        issues.append("存在AI替代人类导向")
    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "check_type": content_type,
        "timestamp": datetime.now().isoformat()
    }


def compliance_check_detail(content, content_type="general"):
    """合规校验详细报告（多维度）"""
    basic = compliance_check(content, content_type)
    text = json.dumps(content, ensure_ascii=False) if isinstance(content, (dict, list)) else str(content)
    dimensions = {
        "价值观": "通过" if not any(kw in text for kw in ["暴力", "反动"]) else "不通过",
        "内容安全": "通过" if not any(kw in text for kw in ["色情", "赌博", "毒品"]) else "不通过",
        "伦理合规": "通过" if "AI完全替代" not in text and "无需人类" not in text else "不通过",
        "隐私保护": "通过",  # 简化，实际需检测个人信息
        "版权合规": "通过"   # 简化，实际需检测侵权内容
    }
    score = sum(1 for v in dimensions.values() if v == "通过") / len(dimensions) * 100
    return {
        **basic,
        "dimensions": dimensions,
        "compliance_score": round(score, 2),
        "level": "优秀" if score >= 90 else "良好" if score >= 70 else "需改进" if score >= 50 else "不合格",
        "suggestions": [
            "建议增加人工审核环节" if score < 90 else "合规性良好",
            "建议定期更新敏感词库" if basic["issues"] else "无特殊建议"
        ]
    }


def batch_compliance_check(items, content_type="general"):
    """批量合规校验"""
    results = []
    passed = 0
    failed = 0
    for item in items:
        result = compliance_check(item, content_type)
        results.append(result)
        if result["passed"]:
            passed += 1
        else:
            failed += 1
    return {
        "total": len(items),
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / len(items) * 100, 2) if items else 0,
        "results": results,
        "failed_items": [r for r in results if not r["passed"]]
    }


def get_root_archives(asset_type=None, limit=50):
    """查询ROOT只读根库归档"""
    archive_path = os.path.join(DATA_DIR, "root_archive.json")
    if not os.path.exists(archive_path):
        return []
    with open(archive_path, 'r', encoding='utf-8') as f:
        archives = json.load(f)
    if asset_type:
        archives = [a for a in archives if a.get("asset_type") == asset_type]
    return archives[-limit:][::-1]


def get_sandbox_archives(asset_type=None, limit=50):
    """查询沙盒动态库归档"""
    sandbox_path = os.path.join(DATA_DIR, "sandbox_archive.json")
    if not os.path.exists(sandbox_path):
        return []
    with open(sandbox_path, 'r', encoding='utf-8') as f:
        archives = json.load(f)
    if asset_type:
        archives = [a for a in archives if a.get("asset_type") == asset_type]
    return archives[-limit:][::-1]


def verify_archive_hash(asset_id):
    """验证归档哈希完整性"""
    archive_path = os.path.join(DATA_DIR, "root_archive.json")
    if not os.path.exists(archive_path):
        return {"verified": False, "error": "归档库不存在"}
    with open(archive_path, 'r', encoding='utf-8') as f:
        archives = json.load(f)
    for archive in archives:
        if archive.get("asset_id") == asset_id:
            content = archive.get("content", {})
            expected_hash = archive.get("content_hash", "")
            actual_hash = compute_hash(content)
            return {
                "verified": expected_hash == actual_hash,
                "asset_id": asset_id,
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
                "timestamp": archive.get("timestamp")
            }
    return {"verified": False, "error": f"未找到资产: {asset_id}"}


def export_archives(archive_type="root", filepath=None):
    """导出归档数据"""
    if archive_type == "root":
        archives = get_root_archives(limit=10000)
    else:
        archives = get_sandbox_archives(limit=10000)
    if not filepath:
        filepath = os.path.join(DATA_DIR, f"export_{archive_type}_archive.json")
    export_data = {
        "export_type": archive_type,
        "exported_at": datetime.now().isoformat(),
        "total_count": len(archives),
        "did": DID,
        "anchor": ANCHOR,
        "archives": archives
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    return filepath
