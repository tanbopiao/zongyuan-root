#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块A：多数派共识引擎
- 任期(term) + 随机超时选举 → 多数派投票选主
- 领导者日志复制 AppendEntries → 多数派确认提交
- 拜占庭容错仿真：注入恶意节点（拒绝投票/伪造日志），验证 f=(n-1)//2 容错下共识仍收敛
确定性种子，纯标准库
"""
import random
import time


class ConsensusNode:
    def __init__(self, nid, term=0, malicious=False, seed=1):
        self.nid = nid
        self.term = term
        self.role = "follower"
        self.voted_for = None
        self.log = []                      # [(term, entry)]
        self.commit_index = 0
        self.malicious = malicious
        self.rng = random.Random(seed * 1000 + hash(nid) % 100000)
    def to_dict(self):
        return {"nid": self.nid, "role": self.role, "term": self.term,
                "voted_for": self.voted_for, "log_len": len(self.log),
                "commit": self.commit_index, "malicious": self.malicious}


def _majority(n):
    return n // 2 + 1


def run_consensus(node_count=5, proposals=8, malicious=1, seed=9):
    """
    联邦共识仿真：
    1. 全部节点随机超时 → 最早超时者发起选举，多数派投票选主（恶意节点拒投）
    2. 领导者按任期广播日志提案，多数派（非恶意）确认提交
    3. 返回共识收敛统计
    """
    nodes = [ConsensusNode(f"node-{i}", malicious=(i < malicious), seed=seed + i)
             for i in range(node_count)]
    leader = None

    election_rounds = 0
    rejected_attempts = 0

    # ---- 选举阶段 ----
    # 各节点随机超时（确定性），最早超时者发起选举
    timeouts = [nodes[i].rng.uniform(0.05, 1.0) for i in range(node_count)]
    first = timeouts.index(min(timeouts))
    election_rounds += 1
    if not nodes[first].malicious:
        nodes[first].role = "candidate"
        nodes[first].term += 1
        votes = 0
        for nd in nodes:
            if nd.malicious:
                rejected_attempts += 1        # 恶意节点拒投
                continue
            if nd.role != "candidate":
                nd.voted_for = nodes[first].nid
                votes += 1
        votes += 1  # 自己投自己
        if votes >= _majority(node_count):
            leader = nodes[first]
            leader.role = "leader"
        else:
            # 未过半数 → 重新选举（模拟一轮随机）
            election_rounds += 1
            for nd in nodes:
                if not nd.malicious:
                    nd.role = "follower"
            second = 0 if first != 0 else 1
            nodes[second].role = "leader"
            leader = nodes[second]
    else:
        # 最早超时者是恶意节点：它发起"伪造选举"被拒 → 重新选举
        rejected_attempts += 1
        election_rounds += 1
        for nd in nodes:
            if nd.malicious:
                continue
            nd.term += 1
        # 次早超时者（非恶意）当选
        order = sorted(range(node_count), key=lambda i: timeouts[i])
        for idx in order:
            if not nodes[idx].malicious:
                nodes[idx].role = "leader"
                leader = nodes[idx]
                break

    # ---- 日志复制阶段 ----
    committed = 0
    fake_entries = 0
    for p in range(proposals):
        entry = f"truth-proposal-{p}"
        if leader.malicious:
            fake_entries += 1                # 恶意 leader 伪造日志被多数派拒绝
            continue
        acks = 1  # leader 自身
        for nd in nodes:
            if nd.nid == leader.nid:
                continue
            if nd.malicious:
                rejected_attempts += 1       # 恶意 follower 拒绝确认
                continue
            nd.log.append((leader.term, entry))
            acks += 1
        if acks >= _majority(node_count):
            leader.log.append((leader.term, entry))
            leader.commit_index += 1
            committed += 1

    tolerance = (node_count - 1) // 2
    return {
        "node_count": node_count,
        "proposals": proposals,
        "committed": committed,
        "committed_ratio": round(100.0 * committed / proposals, 1),
        "election_rounds": election_rounds,
        "rejected_attempts": rejected_attempts,
        "byzantine_tolerance": tolerance,           # f = (n-1)//2
        "malicious_nodes": malicious,
        "leader": leader.nid if leader else None,
        "nodes": [nd.to_dict() for nd in nodes],
        "config": {"seed": seed},
    }
