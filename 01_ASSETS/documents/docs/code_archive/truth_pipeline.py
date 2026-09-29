#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜真值流水线引擎
完整链路：真值提取 → 网关上报 → Merkle根计算 → 飞书审批 → 全域广播
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""
import sys
import json
import time
import hashlib
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR / "comm" / "protocol"))
from comm_protocol import build_message, write_broadcast, sha256_str

GATEWAY_URL = "https://www.huodouai.com/api/report/truth"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
LEDGER_DIR = BASE_DIR / "ledger"
PIPELINE_LOG = BASE_DIR / "logs" / "pipeline.log"


def log(msg, level="INFO"):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [PIPELINE] [{level}] {msg}"
    print(line, flush=True)
    PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_LOG, "a") as f:
        f.write(line + "\n")


def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_merkle_root(leaf_hashes):
    nodes = leaf_hashes.copy()
    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])
        new_nodes = []
        for i in range(0, len(nodes), 2):
            new_nodes.append(sha256_str(nodes[i] + nodes[i+1]))
        nodes = new_nodes
    return nodes[0] if nodes else ""


def report_truth(truth_key, truth_value, truth_type="protocol", confidence=0.98):
    """阶段1：上报真值到记忆网关"""
    try:
        resp = requests.post(GATEWAY_URL, json={
            "truth_key": truth_key,
            "truth_value": truth_value,
            "source_node": DID,
            "confidence": confidence,
            "truth_type": truth_type
        }, timeout=15)
        data = resp.json()
        success = data.get("written_to_gateway", False) or data.get("success", False)
        log(f"[阶段1] 真值上报: {truth_key} | {'成功' if success else '失败'}")
        return success, data
    except Exception as e:
        log(f"[阶段1] 上报异常: {e}", "ERROR")
        return False, {"error": str(e)}


def calculate_merkle(truth_items):
    """阶段2：计算Merkle根"""
    leaves = []
    for item in truth_items:
        raw = item.get("truth_key", "") + "|" + item.get("truth_value", "")
        leaves.append(sha256_str(raw))
    root = build_merkle_root(leaves)
    log(f"[阶段2] Merkle根计算: {root[:16]}... ({len(leaves)}叶子)")

    # 保存到账本
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    merkle_file = LEDGER_DIR / "merkle_tree.json"
    tree = {"leaves": leaves, "root": root, "updated_at": time.time()}
    merkle_file.write_text(json.dumps(tree, indent=2, ensure_ascii=False), encoding="utf-8")
    return root


def create_approval(merkle_root, truth_count, title="元规则全域锁档审批"):
    """阶段3：创建审批（本地记录+网关上报）"""
    approval_id = f"APR-{int(time.time())}-{sha256_str(merkle_root)[:8]}"
    log(f"[阶段3] 创建审批: {approval_id}")

    # 上报审批真值到网关
    report_truth(
        f"APPROVAL.{approval_id}",
        json.dumps({
            "approval_id": approval_id,
            "title": title,
            "merkle_root": merkle_root,
            "truth_count": truth_count,
            "status": "pending",
            "did": DID
        }, ensure_ascii=False),
        "decision", 0.99
    )

    # 本地保存审批记录
    approval_dir = BASE_DIR / "approval"
    approval_dir.mkdir(parents=True, exist_ok=True)
    (approval_dir / f"{approval_id}.json").write_text(
        json.dumps({"approval_id": approval_id, "title": title,
                     "merkle_root": merkle_root, "status": "pending",
                     "create_time": time.time()}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return approval_id


def approve(approval_id):
    """审批通过"""
    approval_file = BASE_DIR / "approval" / f"{approval_id}.json"
    if not approval_file.exists():
        log(f"审批不存在: {approval_id}", "WARN")
        return False
    data = json.loads(approval_file.read_text(encoding="utf-8"))
    data["status"] = "approved"
    data["approve_time"] = time.time()
    approval_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"[阶段3] 审批通过: {approval_id}")

    # 上报网关
    report_truth(f"APPROVAL.{approval_id}.RESULT",
        json.dumps({"approval_id": approval_id, "status": "approved"}, ensure_ascii=False),
        "decision", 1.0)
    return True


def broadcast_merkle(merkle_root, truth_count):
    """阶段4：全域广播Merkle根到所有次中枢"""
    msg = build_message("BROADCAST", "MASTER", "ALL", {
        "action": "SYNC_LEDGER",
        "merkle_root": merkle_root,
        "truth_count": truth_count,
        "timestamp": time.time()
    }, priority=10)
    write_broadcast(msg)
    log(f"[阶段4] 全域广播已发送: Merkle={merkle_root[:16]}...")
    return msg


def run_full_pipeline(truth_items, title="全域锁档"):
    """执行完整流水线"""
    log("=" * 50)
    log(f"启动真值流水线: {title} ({len(truth_items)}条真值)")
    log("=" * 50)

    # 阶段1：批量上报真值
    success_count = 0
    for item in truth_items:
        ok, _ = report_truth(
            item["truth_key"], item["truth_value"],
            item.get("truth_type", "protocol"), item.get("confidence", 0.98)
        )
        if ok:
            success_count += 1
    log(f"阶段1完成: {success_count}/{len(truth_items)} 上报成功")

    # 阶段2：计算Merkle根
    merkle_root = calculate_merkle(truth_items)

    # 阶段3：创建审批
    approval_id = create_approval(merkle_root, len(truth_items), title)

    # 阶段4：自动审批通过（本地自治模式，可配置为人工审批）
    approve(approval_id)

    # 阶段5：全域广播
    broadcast_merkle(merkle_root, len(truth_items))

    log("=" * 50)
    log(f"流水线完成! Merkle根: {merkle_root[:16]}...")
    log(f"审批ID: {approval_id}")
    log("=" * 50)

    return {
        "merkle_root": merkle_root,
        "approval_id": approval_id,
        "truth_count": len(truth_items),
        "success_count": success_count
    }


if __name__ == "__main__":
    # 测试：用系统元规则跑一次流水线
    test_truths = [
        {"truth_key": "META_RULE.TRISTATE.WORKER.DRIVE",
         "truth_value": "三态正交指令驱动宿主机Worker元法则",
         "truth_type": "meta_law", "confidence": 1.0},
        {"truth_key": "META_RULE.FILE.ATOMIC_WRITE",
         "truth_value": "资产原子写入，残缺文件自动丢弃",
         "truth_type": "rule", "confidence": 0.99},
        {"truth_key": "META_RULE.LEDGER.APPEND_ONLY",
         "truth_value": "M9账本仅追加，禁止修改历史",
         "truth_type": "rule", "confidence": 0.99},
    ]
    result = run_full_pipeline(test_truths, "系统元规则全域锁档")
    print(json.dumps(result, indent=2, ensure_ascii=False))
