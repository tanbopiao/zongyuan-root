#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geo_stability.py — Agent SSH 受控网关 · GEO 晶格稳态校验算子 (模块3, Phase2)
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

规则版秩序扰动打分 (预留 ML 升级位):
  基准 100 分, 按仿真扰动逐项扣分 -> stability_score [0,100]
  stability_score < threshold -> 驳回 (不碰真机)

扣分项 (可经 whitelist.json "geo" 覆盖):
  外部系统路径写(hard)      -100  (直接触底, 必驳回)
  仿真被跳过(unsimulatable) -20
  外部/tmp写(soft)          -10
  文件删除 每个             -5  (封顶-50, 单删除项即可压到阈值下)
  文件修改 每个             -2  (封顶-20)
  文件创建 每个             -1  (封顶-15)
  磁盘增量 >50MB/-20, >10MB/-10
  网络扰动(出站)            -15
  残留进程 每个             -25
  仿真超时                  -25
  仿真 rc != 0              -10
"""
import json

DEFAULT_GEO = {
    "threshold": 60.0,
    "weight_hard_write": -100.0,
    "weight_sim_skipped": -20.0,
    "weight_soft_write": -10.0,
    "weight_deleted": -5.0, "deleted_cap": -50.0,
    "weight_modified": -2.0, "modified_cap": -20.0,
    "weight_created": -1.0, "created_cap": -15.0,
    "disk_mb_high": -20.0, "disk_mb_mid": -10.0,
    "weight_net": -15.0,
    "weight_residual_proc": -25.0,
    "weight_timeout": -25.0,
    "weight_sim_fail": -10.0,
}


def score(sim_result, geo_cfg=None, command_decision="mutate"):
    """
    输入: simulate() 输出 + 可选 geo 配置
    返回: {"stability_score": float, "threshold": float, "verdict": "pass"|"reject",
           "breakdown": [{factor, delta}...], "drift_reasons": [...]}
    """
    cfg = dict(DEFAULT_GEO)
    if geo_cfg:
        cfg.update(geo_cfg)

    score_now = 100.0
    breakdown = []
    drift = []

    def cut(factor, delta):
        nonlocal score_now
        score_now += delta
        breakdown.append({"factor": factor, "delta": delta})

    hard = sim_result.get("external_write_hard") or []
    soft = sim_result.get("external_write_soft") or []

    if hard:
        cut("external_system_write:%s" % ",".join(hard[:3]), cfg["weight_hard_write"])
        drift.append("system_path_write")
    if not sim_result.get("simulated", True):
        cut("sim_skipped_unsimulatable", cfg["weight_sim_skipped"])
        drift.append("sim_skipped")
        if soft:
            cut("external_tmp_write:%s" % ",".join(soft[:3]), cfg["weight_soft_write"])
            drift.append("tmp_path_write")
    else:
        counts = sim_result.get("files", {}).get("counts", {})
        n_del = counts.get("deleted", 0)
        n_mod = counts.get("modified", 0)
        n_cre = counts.get("created", 0)
        if n_del:
            d = max(cfg["weight_deleted"] * n_del, cfg["deleted_cap"])
            cut("files_deleted:%d" % n_del, d)
            drift.append("file_delete")
        if n_mod:
            d = max(cfg["weight_modified"] * n_mod, cfg["modified_cap"])
            cut("files_modified:%d" % n_mod, d)
        if n_cre:
            d = max(cfg["weight_created"] * n_cre, cfg["created_cap"])
            cut("files_created:%d" % n_cre, d)

        disk_kb = sim_result.get("disk_delta_kb", 0)
        if disk_kb > 50 * 1024:
            cut("disk_growth:%dKB" % disk_kb, cfg["disk_mb_high"])
            drift.append("disk_growth")
        elif disk_kb > 10 * 1024:
            cut("disk_growth:%dKB" % disk_kb, cfg["disk_mb_mid"])

        if sim_result.get("net_probe"):
            cut("network_egress", cfg["weight_net"])
            drift.append("network_egress")
        resid = sim_result.get("residual_procs", 0)
        if resid:
            cut("residual_procs:%d" % resid, cfg["weight_residual_proc"] * resid)
            drift.append("residual_process")
        if sim_result.get("timed_out"):
            cut("sim_timeout", cfg["weight_timeout"])
            drift.append("sim_timeout")
        rc = sim_result.get("rc")
        if rc not in (0, None):
            cut("sim_rc:%s" % rc, cfg["weight_sim_fail"])

    score_now = max(0.0, min(100.0, score_now))
    threshold = cfg["threshold"]
    verdict = "pass" if score_now >= threshold else "reject"
    if verdict == "reject":
        drift.append("below_threshold")

    return {"stability_score": round(score_now, 1), "threshold": threshold,
            "verdict": verdict, "breakdown": breakdown,
            "drift_reasons": drift, "scorer": "GEO-RULE-V1"}


if __name__ == "__main__":
    # 自测: 恰好在阈值边缘的两个样例
    clean = {"simulated": True, "rc": 0, "timed_out": False,
             "files": {"counts": {"created": 1, "modified": 0, "deleted": 0}},
             "disk_delta_kb": 4, "net_probe": False, "residual_procs": 0,
             "external_write_hard": [], "external_write_soft": []}
    bad = dict(clean, files={"counts": {"created": 0, "modified": 0, "deleted": 12}},
               residual_procs=1, net_probe=True)
    print(json.dumps({"clean": score(clean), "bad": score(bad)},
                     ensure_ascii=False, indent=2))
