#!/bin/bash
K=/www/wwwroot/huodouai.com/zhongshu/kernel-evolve/zongyuan-kernel
DB=/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db
TS=$(date '+%Y-%m-%d %H:%M:%S')
cd $K || exit 1
python3 - "$DB" "$K/truths/truths_public_latest.json" <<'PY'
import sqlite3,sys,json,time
db,out=sys.argv[1],sys.argv[2]
c=sqlite3.connect(db)
rows=c.execute("SELECT seq,key,ts,scope FROM truth ORDER BY seq DESC LIMIT 800").fetchall()
recs=[{"seq":s,"key":k,"ts":t,"scope":g} for s,k,t,g in rows]
json.dump({"exported_at":time.strftime('%Y-%m-%d %H:%M:%S'),"count":len(recs),"records":recs},open(out,"w"),ensure_ascii=False)
print("truth_snapshot",len(recs))
PY
SEQ=$(python3 -c "import sqlite3;print(sqlite3.connect('$DB').execute('SELECT MAX(seq) FROM truth').fetchone()[0])")
MK=$(curl -s -m8 http://127.0.0.1:9001/api/status 2>/dev/null | python3 -c "import json,sys;print(json.load(sys.stdin).get('merkle_root',''))" 2>/dev/null)
REF=$K/truths/refined_truths.json
LAST=""
[ -f $REF ] && LAST=$(python3 -c "import json;d=json.load(open('$REF'));r=d.get('records',[]);print(r[-1].get('seq','') if r else '')" 2>/dev/null)
if [ "$LAST" != "$SEQ" ]; then
  python3 - "$REF" "$TS" "$SEQ" "$MK" <<'PY'
import json,sys
ref,ts,seq,mk=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
try: d=json.load(open(ref))
except: d={"kernel":"refined_truths","records":[]}
d.setdefault("records",[]).append({"ts":ts,"seq":int(seq),"merkle_root":mk,"note":"云端自治进化引擎提炼"})
json.dump(d,open(ref,"w"),ensure_ascii=False,indent=0)
print("refine_seq",seq)
PY
fi
TO=$(ls -t $K/index/ASSET-TOPOLOGY-*.json 2>/dev/null | head -1)
if [ -n "$TO" ]; then
  python3 - "$TO" "$SEQ" "$TS" <<'PY'
import json,sys
p,seq,ts=sys.argv[1],sys.argv[2],sys.argv[3]
d=json.load(open(p))
for dom in d.get("domains",[]):
    if dom.get("domain")=="truths":
        for a in dom.get("assets",[]):
            if a.get("id")=="A-TRUTH-001": a["count"]=int(seq)
d["scan_time"]=ts
json.dump(d,open(p,"w"),ensure_ascii=False,indent=0)
print("topology_updated")
PY
fi
if git status --porcelain 2>/dev/null | grep -q .; then
  git add -A
  git -c user.name="zongyuangen" -c user.email="zongyuangen@zongyuan-root" commit -qm "cloud-evolve: kernel auto evolution $(date '+%Y-%m-%d %H:%M:%S')" 2>/dev/null
  git push origin main >/dev/null 2>&1 && echo "CLOUD_EVOLVE_PUSH seq=$SEQ" || echo "CLOUD_EVOLVE_PUSH_FAIL"
else
  echo "CLOUD_EVOLVE_NOCHANGE"
fi
