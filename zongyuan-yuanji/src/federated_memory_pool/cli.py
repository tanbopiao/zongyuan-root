"""Federated Memory Pool CLI

用法:
    python3 -m federated_memory_pool <cmd> [options]

命令:
    add       写入记忆（propose + validate）
    query     查询记忆
    recall    召回记忆（更新命中）
    reflect   反思调整价值分
    vote      投票
    confirm   确认（跨节点确权）
    sync      跨节点增量同步
    decay     应用生命周期衰减
    softforget 软遗忘指定 key
    verify    校验账本完整性
    stats     联邦统计
    submit-high-value  一键高价值记忆跨节点确认（五阶段全跑）
    demo      端到端演示

示例:
    python3 -m federated_memory_pool demo
"""

import argparse
import json
import sys
import time
from pathlib import Path
from .core import (
    FederatedMemoryPool, MemoryNode, MemoryRecord,
    verify_ledger_integrity, merkle_root_from_ledger,
    ANCHOR, DEFAULT_DID, KERNEL_VERSION,
    STATE_CONFIRMED, STATE_PROPOSED, STATE_VALIDATED, STATE_DECAYED,
    STATE_REINFORCED, STATE_SOFT_FORGOTTEN,
    HIGH_VALUE_THRESHOLD, CONFIRM_VOTE_QUORUM,
)  # noqa: F401


def _load_or_create_pool(pool_dir: Path) -> FederatedMemoryPool:
    pool = FederatedMemoryPool()
    pool_dir.mkdir(parents=True, exist_ok=True)
    for path in pool_dir.glob("node-*.json"):
        try:
            pool.load_node(path)
        except Exception as e:
            print(f"  [WARN] load_node {path} failed: {e}", file=sys.stderr)
    return pool


def _save_pool(pool: FederatedMemoryPool, pool_dir: Path) -> None:
    pool_dir.mkdir(parents=True, exist_ok=True)
    for name, node in pool.nodes.items():
        if node.local_dir is None:
            node.local_dir = pool_dir
        node.save()


def _resolve_node(pool: FederatedMemoryPool, name: str,
                  pool_dir: Path, create_if_missing: bool = True) -> str:
    if name not in pool.nodes:
        if create_if_missing:
            pool.register_node(name, local_dir=pool_dir)
        else:
            raise SystemExit(f"[ERROR] node '{name}' not registered")
    else:
        pool.nodes[name].local_dir = pool_dir
    return name


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------

def cmd_add(args):
    pool = _load_or_create_pool(Path(args.pool))
    _resolve_node(pool, args.node, Path(args.pool))
    rec = pool.nodes[args.node].retain(
        key=args.key, value=json.loads(args.value),
        truth_type=args.type, bank=args.bank,
    )
    proposal = pool.consensus.propose(rec)
    validation = pool.consensus.validate(args.key)
    _save_pool(pool, Path(args.pool))
    print(json.dumps({
        "ok": True, "key": args.key, "state": rec.state,
        "sha256": rec.sha256, "value_score": rec.value_score,
        "proposal": proposal, "validation": validation,
    }, ensure_ascii=False, indent=2))


def cmd_query(args):
    pool = _load_or_create_pool(Path(args.pool))
    if not pool.nodes:
        print(json.dumps({"ok": False, "reason": "no_nodes"}))
        return
    # 在所有节点里查
    results = []
    for name, node in pool.nodes.items():
        rec = node.recall(args.key)
        if rec is not None:
            results.append({
                "node": name, "key": rec.key, "value": rec.value,
                "state": rec.state, "sha256": rec.sha256,
                "hits": rec.hits, "value_score": rec.value_score,
            })
    print(json.dumps({"ok": True, "results": results}, ensure_ascii=False, indent=2))


def cmd_recall(args):
    pool = _load_or_create_pool(Path(args.pool))
    node = pool.nodes[args.node]
    rec = node.recall(args.key)
    if rec is None:
        print(json.dumps({"ok": False, "reason": "not_found"}))
        return
    _save_pool(pool, Path(args.pool))
    print(json.dumps({
        "ok": True, "key": args.key, "state": rec.state,
        "hits": rec.hits, "sha256": rec.sha256,
    }, ensure_ascii=False, indent=2))


def cmd_reflect(args):
    pool = _load_or_create_pool(Path(args.pool))
    node = pool.nodes[args.node]
    rec = node.reflect(args.key, delta_score=args.delta, note=args.note or "")
    if rec is None:
        print(json.dumps({"ok": False, "reason": "not_found"}))
        return
    _save_pool(pool, Path(args.pool))
    print(json.dumps({
        "ok": True, "key": args.key, "state": rec.state,
        "value_score": rec.value_score,
    }, ensure_ascii=False, indent=2))


def cmd_vote(args):
    pool = _load_or_create_pool(Path(args.pool))
    result = pool.consensus.vote(
        args.key, voter_node=args.voter, voter_did=args.did,
        sha_expected=args.sha, agree=not args.disagree,
    )
    _save_pool(pool, Path(args.pool))
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))


def cmd_confirm(args):
    pool = _load_or_create_pool(Path(args.pool))
    node = pool.nodes[args.node]
    result = pool.consensus.confirm(args.key, node)
    _save_pool(pool, Path(args.pool))
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))


def cmd_sync(args):
    pool = _load_or_create_pool(Path(args.pool))
    stats = pool.sync(args.source, args.target)
    _save_pool(pool, Path(args.pool))
    print(json.dumps({"ok": True, **stats}, ensure_ascii=False, indent=2))


def cmd_decay(args):
    pool = _load_or_create_pool(Path(args.pool))
    result = pool.apply_lifecycle_all(force_decay=args.force)
    _save_pool(pool, Path(args.pool))
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))


def cmd_softforget(args):
    pool = _load_or_create_pool(Path(args.pool))
    node = pool.nodes[args.node]
    ok = node.get_bank(args.bank).soft_forget(args.key)
    _save_pool(pool, Path(args.pool))
    print(json.dumps({"ok": ok, "key": args.key}, ensure_ascii=False, indent=2))


def cmd_verify(args):
    pool = _load_or_create_pool(Path(args.pool))
    results = {}
    for name, node in pool.nodes.items():
        for bank_name, bank in node.banks.items():
            v = verify_ledger_integrity(bank)
            results[f"{name}/{bank_name}"] = v
    print(json.dumps({"ok": True, "results": results}, ensure_ascii=False, indent=2))


def cmd_stats(args):
    pool = _load_or_create_pool(Path(args.pool))
    s = pool.stats()
    print(json.dumps({"ok": True, **s}, ensure_ascii=False, indent=2))


def cmd_submit_high_value(args):
    pool = _load_or_create_pool(Path(args.pool))
    _resolve_node(pool, args.proposer, Path(args.pool))
    _resolve_node(pool, args.voter, Path(args.pool))
    result = pool.submit_high_value(
        key=args.key, value=json.loads(args.value), truth_type=args.type,
        proposer=args.proposer, voter=args.voter, bank=args.bank,
    )
    _save_pool(pool, Path(args.pool))
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Demo：端到端演示
# ---------------------------------------------------------------------------

def cmd_demo(args):
    import tempfile
    with tempfile.TemporaryDirectory(prefix="fmp-demo-") as tmpdir:
        pool_dir = Path(tmpdir)
        pool = FederatedMemoryPool(did=DEFAULT_DID)
        pool.register_node("node-A", local_dir=pool_dir)
        pool.register_node("node-B", local_dir=pool_dir)

        print(f"\n{'='*68}")
        print(f"  Federated Memory Pool L2 · End-to-End Demo")
        print(f"  {ANCHOR} | {DEFAULT_DID} | {KERNEL_VERSION}")
        print(f"{'='*68}\n")

        # Step 1: 高价值记忆一键确认（node-A 提案，node-B 投票）
        print("[1/8] 高价值记忆一键跨节点确认 (五阶段全跑)")
        result = pool.submit_high_value(
            key="KERNEL.META-CONSTITUTION-L0",
            value={"title": "ZONGYUAN-ROOT自治基底宪法 V2.0", "level": "L0"},
            truth_type="meta_law",
            proposer="node-A", voter="node-B",
        )
        print(f"  propose → {result['propose']['status']}")
        print(f"  validate → {result['validate']['status']}")
        print(f"  vote → {result['vote']['status']} (agree_votes={result['vote']['agree_votes']}/{result['vote']['required']})")
        print(f"  archive → {result.get('archive',{}).get('status','N/A')}")
        print(f"  confirm → {result.get('confirm',{}).get('status','N/A')}\n")

        # Step 2: 低价值数据保留本地
        print("[2/8] 低价值数据仅存本地（分级共识 → 本地轻量化）")
        rec_data = pool.nodes["node-A"].retain(
            key="task.cache.temp-1234", value={"x": 1}, truth_type="data"
        )
        print(f"  key={rec_data.key} truth_type={rec_data.truth_type} "
              f"value_score={rec_data.value_score} (阈值 {HIGH_VALUE_THRESHOLD})")
        print(f"  → 同步时会被 skip（分级共识，避免全量同步）\n")

        # Step 3: 生命周期衰减
        print("[3/8] 生命周期衰减（force_decay 测试）")
        decay_result = pool.apply_lifecycle_all(force_decay=True)
        print(f"  node-A: {decay_result['node-A']}")
        print(f"  node-B: {decay_result['node-B']}")
        print(f"  (L0 meta_law 豁免衰减)\n")

        # Step 4: 增量同步（A → B）
        print("[4/8] 增量同步 node-A → node-B（仅高价值）")
        sync_stats = pool.sync("node-A", "node-B")
        print(f"  pushed={sync_stats['pushed']} skipped={sync_stats['skipped']} "
              f"conflict={sync_stats['conflict']} rejected={sync_stats['rejected']}\n")

        # Step 5: 冲突消解
        print("[5/8] 冲突消解（同键异值，高价值侧优先共识）")
        from .core import MemoryRecord as MR
        incoming = MR(
            key="KERNEL.META-CONSTITUTION-L0",
            value={"title": "篡改版本"},
            truth_type="data",  # 低价值伪造
            node="attacker",
            value_score=1.0,
        )
        winner, _ = pool.nodes["node-B"].resolve_conflict(
            "KERNEL.META-CONSTITUTION-L0", incoming
        )
        print(f"  winner_side={winner} (高价值侧胜出)\n")

        # Step 6: 账本完整性校验
        print("[6/8] Merkle-DAG 账本完整性校验")
        for bank_name in ["default"]:
            v = verify_ledger_integrity(pool.nodes["node-A"].get_bank(bank_name))
            print(f"  node-A/{bank_name}: tampered={v['tampered']} "
                  f"ledger_len={v['ledger_len']}")
            print(f"    merkle_root={v['merkle_root'][:16]}...")
        v = verify_ledger_integrity(pool.nodes["node-B"].get_bank("default"))
        print(f"  node-B/default: tampered={v['tampered']} "
              f"ledger_len={v['ledger_len']}")
        print(f"    merkle_root={v['merkle_root'][:16]}...\n")

        # Step 7: 持久化 + 重载验证
        print("[7/8] 持久化 + 重载验证")
        _save_pool(pool, pool_dir)
        files = list(pool_dir.glob("node-*.json"))
        for f in files:
            print(f"  {f.name} ({f.stat().st_size} bytes)")

        # 重新加载
        pool2 = FederatedMemoryPool(did=DEFAULT_DID)
        for f in files:
            pool2.load_node(f)
        s2 = pool2.stats()
        print(f"  重载后 records={s2['records']} confirmed={s2['confirmed']} "
              f"ledger={s2['ledger_entries']}\n")

        # Step 8: 联邦统计
        print("[8/8] 联邦统计")
        s = pool.stats()
        print(f"  nodes={s['nodes']} records={s['records']} "
              f"confirmed={s['confirmed']} high_value={s['high_value']}")
        print(f"  by_state={s['by_state']}")
        print(f"  by_truth_type={s['by_truth_type']}")
        print(f"  conflicts={s['conflicts']} soft_forgotten={s['soft_forgotten']}")
        print(f"  audit_log_len={s['audit_log_len']}")
        print(f"  ledger_entries={s['ledger_entries']}\n")

        print(f"{'='*68}")
        print("  Demo 完成 · L2 联邦记忆池五阶段治理 · 全生命周期已验证")
        print(f"{'='*68}\n")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="federated_memory_pool",
        description="Federated Memory Pool L2 · 五阶段治理 · 纯标准库",
    )
    parser.add_argument("cmd", help="Command to run")
    args_list, _ = parser.parse_known_args(argv)
    cmd = args_list.cmd

    sub = argparse.ArgumentParser()
    sub.add_argument("--pool", default="./pool", help="Pool 目录")
    sub.add_argument("--node", default="local")
    sub.add_argument("--bank", default="default")
    sub.add_argument("--did", default=DEFAULT_DID)
    sub.add_argument("--key")
    sub.add_argument("--value")
    sub.add_argument("--type", default="unknown")
    sub.add_argument("--sha")
    sub.add_argument("--voter")
    sub.add_argument("--proposer")
    sub.add_argument("--source")
    sub.add_argument("--target")
    sub.add_argument("--delta", type=float, default=0.5)
    sub.add_argument("--note")
    sub.add_argument("--force", action="store_true")
    sub.add_argument("--disagree", action="store_true")

    args = sub.parse_args(argv[1:] if argv else None)

    handlers = {
        "add": cmd_add, "query": cmd_query, "recall": cmd_recall,
        "reflect": cmd_reflect, "vote": cmd_vote, "confirm": cmd_confirm,
        "sync": cmd_sync, "decay": cmd_decay, "softforget": cmd_softforget,
        "verify": cmd_verify, "stats": cmd_stats,
        "submit-high-value": cmd_submit_high_value,
        "demo": cmd_demo,
    }
    if cmd not in handlers:
        print(f"[ERROR] Unknown command: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(sorted(handlers.keys()))}", file=sys.stderr)
        sys.exit(2)
    handlers[cmd](args)


if __name__ == "__main__":
    main()
