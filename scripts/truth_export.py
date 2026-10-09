import sqlite3, json, sys, argparse, datetime, re
p = argparse.ArgumentParser(); p.add_argument('--last', type=int, default=0); p.add_argument('--limit', type=int, default=50000); p.add_argument('--slim', action='store_true')
a = p.parse_args()
db = sqlite3.connect('/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db')
rows = db.execute('SELECT seq, key, value, ts, sha, event_id FROM truth WHERE seq > ? ORDER BY seq LIMIT ?', (a.last, a.limit)).fetchall()
def to_epoch(ts):
    try:
        m = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', ts or '')
        if not m: return 0
        return datetime.datetime.strptime(m.group(1), '%Y-%m-%dT%H:%M:%S').replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8))).timestamp()
    except: return 0
out = []
for seq, key, value, ts, sha, eid in rows:
    rec = {'id': seq + 1000000, 'seq': seq, 'truth_key': key, 'category': 'cloudhub', 'node_id': 'tencent-cloud-zhongshu',
           'created_at': to_epoch(ts), 'version': 1, 'truth_value_preview': (value or '')[:200], 'truth_hash': sha}
    if not a.slim: rec['value'] = value
    out.append(rec)
for r in out:
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + '\n')
sys.stderr.write(f'exported {len(out)} rows after seq {a.last}')
