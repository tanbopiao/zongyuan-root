#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 多账号统一入湖管线（P1）
功能：读取多豆包账号分工配置 → 逐个账号产出目录统一归档到魔搭 data_lake
      → 登记 shared_brain.db → 上报记忆网关 → 生成产能看板报告
复用：kunlun_ms_archive.py 的采集/上传/登记/上报函数
作者：元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

用法：
  export MODELSCOPE_TOKEN="ms-xxx"
  python3 kunlun_unified_pipeline.py --config workers_config.json          # 实跑
  python3 kunlun_unified_pipeline.py --config workers_config.json --dry-run # 只看计划
  python3 kunlun_unified_pipeline.py --dir <产出目录> --sub data_lake/xxx   # 单账号快捷
"""
import os
import sys
import json
import glob
import zipfile
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kunlun_ms_archive as K


def pack_dir_to_zip(src_dir, out_zip):
    """把目录打成一个 zip（保留相对结构），返回文件数"""
    n = 0
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for r, _, fns in os.walk(src_dir):
            for f in fns:
                p = os.path.join(r, f)
                if not os.path.isfile(p):
                    continue
                arc = os.path.relpath(p, os.path.dirname(src_dir.rstrip(os.sep)))
                try:
                    z.write(p, arc)
                    n += 1
                except Exception:
                    pass
    return n


def process_worker(w, api, dry_run):
    out = w.get("output_dir", "")
    sub = w.get("sub", "data_lake/worker")
    max_files = int(w.get("max_files_per_push", 100))
    pack_large = w.get("pack_large", True)

    if not out or not os.path.isdir(out):
        return {"account": w.get("account"), "role": w.get("role"), "status": "skip",
                "reason": "output_dir 未配置或不存在"}

    TEMP_MARKS = ("_ms_push", "_shared_brain", "__pycache__", "_pipeline_",
                  "_root_archive", "_runtime_", "_ms_datalake_push", "_test")
    files = [f for f in K.collect_files(out) if not any(m in f[1] for m in TEMP_MARKS)]
    if not files:
        return {"account": w.get("account"), "role": w.get("role"), "status": "skip",
                "reason": "产出目录无资产文件"}

    pushed = []
    if len(files) > max_files and pack_large:
        # 批量 → 打包 zip 上传
        zip_path = os.path.join(os.path.dirname(out.rstrip(os.sep)),
                                f"_pipeline_{w.get('account','worker')}.zip")
        n = pack_dir_to_zip(out, zip_path)
        if dry_run:
            status = "plan_pack"
            detail = f"打包 {n} 文件 → {sub}/{(os.path.basename(zip_path))}"
        else:
            try:
                K.api_upload_db  # 确保模块加载
                ok, fail = K.push_to_ms(api, K_ARG_REPO, sub, [(zip_path, os.path.basename(zip_path))])
                pushed = [os.path.basename(zip_path)] if ok else []
                status = "pack_ok" if ok else "pack_fail"
                detail = f"上传zip: {os.path.basename(zip_path)}"
                if os.path.exists(zip_path):
                    os.remove(zip_path)
            except Exception as e:
                status = "error"
                detail = str(e)[:120]
        return {"account": w.get("account"), "role": w.get("role"), "status": status,
                "detail": detail, "pushed": pushed}
    else:
        # 少量 → 逐文件上传
        if dry_run:
            status = "plan_files"
            detail = f"逐文件 {len(files)} 个 → {sub}/"
            return {"account": w.get("account"), "role": w.get("role"), "status": status,
                    "detail": detail, "pushed": []}
        ok, fail = K.push_to_ms(api, K_ARG_REPO, sub, files)
        entries = [{"name": os.path.basename(fp), "category": "资产",
                    "path": f"modelscope://{K_ARG_REPO}/{sub}/{rel}",
                    "sha256": K.sha256_of(fp)} for fp, rel in ok]
        added = 0
        if entries:
            added, max_id = K.update_shared_brain(entries)
        return {"account": w.get("account"), "role": w.get("role"), "status": "ok",
                "detail": f"逐文件 {len(ok)}/{len(files)} 成功, db新增 {added}", "pushed": [rel for _, rel in ok]}


def main():
    ap = argparse.ArgumentParser(description="多账号统一入湖管线")
    ap.add_argument("--config", help="workers 配置 json")
    ap.add_argument("--dir", help="单账号快捷：产出目录")
    ap.add_argument("--sub", help="单账号快捷：入库子目录")
    ap.add_argument("--dry-run", action="store_true", help="只输出计划，不实际推送")
    ap.add_argument("--repo", default="zongyuanroot/zongyuan-root-achievements")
    args = ap.parse_args()
    global K_ARG_REPO
    K_ARG_REPO = args.repo

    if not args.dry_run:
        token = K.get_token()
        from modelscope.hub.api import HubApi
        api = HubApi()
        api.login(token)
    else:
        api = None
        print("🧪 DRY-RUN 模式：仅输出计划，不推送\n")

    results = []
    if args.dir:
        w = {"account": "单账号快捷", "role": args.sub or "data_lake", "output_dir": args.dir,
             "sub": args.sub or "data_lake/manual", "pack_large": False, "max_files_per_push": 999}
        results.append(process_worker(w, api, args.dry_run))
    elif args.config:
        cfg = json.load(open(args.config, encoding="utf-8"))
        print(f"🔗 管线: {cfg.get('pipeline_name')} | {len(cfg['workers'])} 个账号 worker")
        for w in cfg["workers"]:
            results.append(process_worker(w, api, args.dry_run))
    else:
        print("❌ 需提供 --config 或 --dir"); sys.exit(1)

    # 看板
    print(f"\n{'═' * 60}")
    print(f"📊 多账号入湖管线看板  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═' * 60}")
    total = 0
    for r in results:
        print(f"  [{r['status']:<9}] {r['account']} ({r.get('role','')})")
        print(f"              {r.get('detail', r.get('reason',''))}")
        total += len(r.get("pushed", []))
    print(f"{'─' * 60}")
    print(f"  合计推送资产: {total} | 干跑: {bool(args.dry_run)} | 确权 {K.DID} {K.TRACE}")

    # 写报告
    if not args.dry_run:
        rd = cfg.get("report_dir", "kunlun-create-link/pipeline_reports") if args.config else "kunlun-create-link/pipeline_reports"
        os.makedirs(rd, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        rep = os.path.join(rd, f"pipeline_report_{ts}.md")
        lines = [f"# 多账号入湖管线报告 {ts}\n",
                 f"> 确权 {K.DID} · {K.TRACE}\n",
                 f"\n| 账号 | 角色 | 状态 | 说明 | 推送数 |\n|---|---|---|---|---|"]
        for r in results:
            lines.append(f"| {r['account']} | {r.get('role','')} | {r['status']} | {r.get('detail', r.get('reason',''))} | {len(r.get('pushed',[]))} |")
        lines.append(f"\n**合计推送: {total}**")
        open(rep, "w", encoding="utf-8").write("\n".join(lines))
        print(f"\n📄 报告: {rep}")


if __name__ == "__main__":
    main()
