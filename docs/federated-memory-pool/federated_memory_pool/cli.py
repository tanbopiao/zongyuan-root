# -*- coding: utf-8 -*-
"""federated_memory_pool 联邦记忆池 ｜ 命令行入口"""
import argparse
import json
import sys

from .core import (FederatedMemoryPool, MemoryRecord, sha256, ANCHOR, DID)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="federated-memory-pool",
        description="ZONGYUAN-ROOT 联邦记忆池 CLI ｜ 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="写入记忆真值")
    p_add.add_argument("--key", required=True)
    p_add.add_argument("--value", required=True)
    p_add.add_argument("--type", default="data", choices=[
        "meta_law", "rule", "config", "decision", "data",
        "creative", "risk", "protocol", "unknown"])
    p_add.add_argument("--node", default="local")
    p_add.add_argument("--pool", default="./pool")

    p_q = sub.add_parser("query", help="按 key 查询")
    p_q.add_argument("--key", required=True)
    p_q.add_argument("--node", default="local")
    p_q.add_argument("--pool", default="./pool")

    p_s = sub.add_parser("search", help="关键词搜索")
    p_s.add_argument("--kw", required=True)
    p_s.add_argument("--pool", default="./pool")

    p_sync = sub.add_parser("sync", help="跨节点增量同步")
    p_sync.add_argument("--source", required=True)
    p_sync.add_argument("--targets", nargs="+", required=True)
    p_sync.add_argument("--pool", default="./pool")

    p_v = sub.add_parser("verify", help="哈希完整性校验")
    p_v.add_argument("--node", default="local")
    p_v.add_argument("--pool", default="./pool")

    p_stats = sub.add_parser("stats", help="联邦池统计")
    p_stats.add_argument("--pool", default="./pool")

    args = parser.parse_args(argv)
    pool = FederatedMemoryPool(args.pool)

    if args.cmd == "add":
        node = pool.register_node(args.node)
        rec = MemoryRecord(key=args.key, value=args.value, truth_type=args.type)
        h = node.add(rec)
        print(json.dumps({"ok": True, "key": args.key, "hash": h,
                          "node": args.node}, ensure_ascii=False))
    elif args.cmd == "query":
        node = pool.register_node(args.node)
        rec = node.query(args.key)
        if rec is None:
            print(json.dumps({"ok": False, "reason": "not_found"}))
            sys.exit(1)
        print(json.dumps(rec.to_dict(), ensure_ascii=False))
    elif args.cmd == "search":
        pool.discover()
        all_hits = []
        for name, node in pool.nodes.items():
            hits = node.search(args.kw)
            for r in hits:
                all_hits.append({"node": name, **r.to_dict()})
        print(json.dumps({"ok": True, "count": len(all_hits),
                          "results": all_hits}, ensure_ascii=False))
    elif args.cmd == "sync":
        for name in [args.source] + args.targets:
            pool.register_node(name)
        report = pool.sync(args.source, args.targets)
        print(json.dumps({"ok": True, **report}, ensure_ascii=False))
    elif args.cmd == "verify":
        node = pool.register_node(args.node)
        result = node.verify()
        bad = [k for k, ok in result.items() if not ok]
        print(json.dumps({"ok": len(bad) == 0, "checked": len(result),
                          "tampered": bad}, ensure_ascii=False))
    elif args.cmd == "stats":
        pool.discover()
        print(json.dumps({"ok": True, **pool.merge_stats()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
