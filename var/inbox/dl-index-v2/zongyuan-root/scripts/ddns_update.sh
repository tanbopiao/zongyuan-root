#!/bin/bash
# ZONGYUAN-ROOT DDNS 自动更新（腾讯云 DNSPod 官方 SDK）
# 动态 IP → DNS A 记录自动创建/更新：Describe → (无)Create / (有)Modify / (同)NOOP
# 密钥经受限文件 var/network/ddns.conf（600）读取；零明文入锁档/账本
# 只操作白名单子域（DOMAINS）的 A 记录；审计 var/network/ddns-audit.jsonl
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
CONF="$ROOT/var/network/ddns.conf"
IP="${1:-}"
[ -z "$IP" ] && IP=$(python3 -c "import json;print(json.load(open('$ROOT/var/network/ip-state.json'))['current_ip'])" 2>/dev/null || echo "")
[ -z "$IP" ] && { echo "[ddns] BLOCK: 无法获取当前IP"; exit 1; }

[ -f "$CONF" ] || { echo "[ddns] BLOCK: $CONF 不存在（先配置 600 密钥文件）"; exit 2; }
# shellcheck disable=SC1090
source "$CONF"
[ -n "${DDNS_SECRET_ID:-}" ] && [ -n "${DDNS_SECRET_KEY:-}" ] || { echo "[ddns] BLOCK: SecretId/SecretKey 未配置"; exit 2; }

python3 - "$ROOT" "$IP" "$DOMAINS" "$DDNS_SECRET_ID" "$DDNS_SECRET_KEY" <<'EOF'
import json, sys, time
from pathlib import Path
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.dnspod.v20210323 import dnspod_client, models

ROOT, IP, DOMAINS, SID, SKEY = sys.argv[1:6]
AUDIT = Path(ROOT)/'var/network'/'ddns-audit.jsonl'
cred = credential.Credential(SID, SKEY)
hp = HttpProfile(); hp.endpoint = "dnspod.tencentcloudapi.com"
cp = ClientProfile(); cp.httpProfile = hp
client = dnspod_client.DnspodClient(cred, "", cp)
TS_H = time.strftime('%Y-%m-%dT%H:%M:%S%z')
results = []

for d in DOMAINS.split(','):
    sub = d.split('.')[0]; main = '.'.join(d.split('.')[1:])
    try:
        q = models.DescribeRecordListRequest()
        q.Domain = main; q.SubDomain = sub; q.RecordType = "A"
        recs = client.DescribeRecordList(q).RecordList or []
        rid = recs[0].RecordId if recs else None
        old = recs[0].Value if recs else None
        if rid is None:
            req = models.CreateRecordRequest()
            req.Domain = main; req.SubDomain = sub; req.RecordType = "A"
            req.RecordLine = "默认"; req.Value = IP
            client.CreateRecord(req)
            action = "CREATE"
        else:
            if old == IP:
                results.append({"domain": d, "action": "NOOP", "value": IP, "ok": True})
                print(f"[ddns] {d}: NOOP（已是最新 IP）")
                continue
            req = models.ModifyRecordRequest()
            req.Domain = main; req.SubDomain = sub; req.RecordType = "A"
            req.RecordLine = "默认"; req.Value = IP; req.RecordId = rid
            client.ModifyRecord(req)
            action = "MODIFY"
        results.append({"domain": d, "action": action, "value": IP, "ok": True, "old": old})
        print(f"[ddns] {d}: {action} A → {IP}" + (f"（原 {old}）" if action=="MODIFY" else ""))
    except Exception as e:
        results.append({"domain": d, "action": "FAIL", "error": str(e)[:160], "ok": False})
        print(f"[ddns] {d}: FAIL -> {e}")

with open(AUDIT, 'a', encoding='utf-8') as f:
    f.write(json.dumps({"ts": TS_H, "ip": IP, "results": results}, ensure_ascii=False) + "\n")
print(f"[ddns] 审计已写: {AUDIT}")
sys.exit(0 if all(r["ok"] for r in results) else 3)
EOF
