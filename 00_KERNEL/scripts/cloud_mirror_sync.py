#!/usr/bin/env python3
"""cloud_mirror_sync.py v1.0 — 云端三大件增量镜像定时同步
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω

流程: 行级保护快照 → 三路增量 rsync(无--delete) → dry-run 复核 →
      HASH-LEDGER/audit 行级合并(本地行并回) → 成功留痕 / 失败告警
告警: 本地 var/inbox/alerts.jsonl 必写; 配置凭据件时同步上报中枢 risk 真值。
零人工介入, 仅供定时任务调用; 不做任何 git 提交(锁档由人工/自动上报流程接管)。
用法: python3 00_KERNEL/scripts/cloud_mirror_sync.py [--dry-run-only]
"""
import os, sys, json, time, subprocess, argparse, urllib.request, urllib.error

DID = "DID-BR-000002"
NODE = "NODE-DEV-CODEARTS-001"
CENTRAL = "https://www.huodouai.com"
CRED = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".cred", "capture_token")
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RSH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zrrsh.sh")
HOST = "root@123.207.202.158"
LOG = os.path.join(PRJ, "logs", "cloud_mirror_sync.log")
ALERTS = os.path.join(PRJ, "var", "inbox", "alerts.jsonl")
LEDGER = os.path.join(PRJ, "HASH-LEDGER.csv")
AUDIT = os.path.join(PRJ, "var", "inbox", "audit.jsonl")

ROUTES = [
    {"name": "zongyuan_root", "src": "/opt/ZONGYUAN-ROOT/", "dst": PRJ + "/", "opts": ["--exclude=.git"]},
    {"name": "zongyuan_yuanji", "src": "/root/zongyuan-yuanji/", "dst": PRJ + "/00_KERNEL/shared_brain/zongyuan-yuanji/", "opts": []},
    {"name": "zhongshu", "src": "/www/wwwroot/huodouai.com/zhongshu/", "dst": PRJ + "/00_KERNEL/shared_brain/zhongshu/", "opts": []},
]

def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())

def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (now(), msg))

def rsync(route, dry=False, timeout=3600):
    cmd = ["rsync", "-a"] + route["opts"]
    if dry:
        cmd += ["--dry-run", "--itemize-changes"]
    else:
        cmd += ["--stats"]
    cmd += ["-e", RSH, HOST + ":" + route["src"], route["dst"]]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0:
        raise RuntimeError("rsync %s rc=%d: %s" % (route["name"], p.returncode, out[-400:]))
    if dry:
        changed = [l for l in out.splitlines()
                   if len(l) > 11 and l[0] in "><ch.fdL" and not l.startswith("created ")]
        return len(changed)
    return out

def lineset(path):
    if not os.path.exists(path):
        return set(), []
    ls = open(path, encoding="utf-8", errors="replace").read().splitlines()
    return set(l for l in ls if l.strip()), ls

def merge_lines(path, pre_lines):
    """行级合并: 同步后把本地原有而云端版缺失的行并回(并集, 不删云端行)。"""
    cur = open(path, encoding="utf-8", errors="replace").read().splitlines() if os.path.exists(path) else []
    cur_set = set(cur)
    missing = [l for l in pre_lines if l.strip() and l not in cur_set]
    if missing:
        with open(path, "a", encoding="utf-8", errors="replace") as f:
            if cur and not cur[-1] == "":
                f.write("\n")
            f.write("\n".join(missing) + "\n")
    return len(missing)

def alert_risk(err):
    rec = {"ts": now(), "node": NODE, "did": DID, "channel": "cloud_mirror_sync",
           "truth_type": "risk", "error": str(err)[:500]}
    os.makedirs(os.path.dirname(ALERTS), exist_ok=True)
    with open(ALERTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if os.path.exists(CRED):
        token = open(CRED).read().strip()
        payload = json.dumps({
            "key": "RISK.CLOUD-MIRROR-SYNC.%s" % now()[:10].replace("-", ""),
            "truth_value": "云端镜像增量同步失败: %s" % str(err)[:300],
            "source_node": NODE, "confidence": 1.0, "truth_type": "risk"}, ensure_ascii=False).encode()
        try:
            req = urllib.request.Request(CENTRAL + "/api/report/truth", data=payload, method="POST",
                headers={"Content-Type": "application/json", "X-DID": DID, "X-Capture-Token": token})
            urllib.request.urlopen(req, timeout=15).read()
            rec["central_reported"] = True
        except Exception as e:
            rec["central_reported"] = False
            rec["central_error"] = str(e)[:200]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run-only", action="store_true")
    a = ap.parse_args()

    pre_ledger, ledger_lines = lineset(LEDGER)
    pre_audit, audit_lines = lineset(AUDIT)
    summary = {"ts": now(), "routes": {}, "ledger_rows_restored": 0, "audit_rows_restored": 0,
               "status": "ok"}

    try:
        for r in ROUTES:
            if not os.path.isfile(RSH):
                raise RuntimeError("missing rsh wrapper: %s" % RSH)
            pre_delta = rsync(r, dry=True)
            if a.dry_run_only:
                summary["routes"][r["name"]] = {"dry_run_pending_delta": pre_delta, "mode": "dry-run-only"}
                continue
            rsync(r, dry=False)
            post_delta = rsync(r, dry=True)
            summary["routes"][r["name"]] = {"pre_delta": pre_delta, "post_delta": post_delta,
                                            "verified": post_delta <= pre_delta + 20}
            if post_delta > pre_delta + 20:
                raise RuntimeError("%s 复核漂移超界: pre=%d post=%d" % (r["name"], pre_delta, post_delta))
        if not a.dry_run_only:
            summary["ledger_rows_restored"] = merge_lines(LEDGER, ledger_lines)
            summary["audit_rows_restored"] = merge_lines(AUDIT, audit_lines)
    except Exception as e:
        summary["status"] = "fail"
        summary["error"] = str(e)[:500]
        alert_risk(e)
        log("FAIL " + json.dumps(summary, ensure_ascii=False))
        print(json.dumps(summary, ensure_ascii=False))
        sys.exit(1)

    log("OK " + json.dumps(summary, ensure_ascii=False))
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == "__main__":
    main()
