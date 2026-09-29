#!/usr/bin/env python3
"""
短剧平台本地仿真API服务
T1(P0) 短剧平台API对接与真实可用化
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, time, hashlib, os, uuid
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = os.path.expanduser("~/.zongyuan_root/drama_platform.db")

def init_db():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dramas (
        id TEXT PRIMARY KEY, title TEXT, series TEXT, character TEXT,
        total_episodes INTEGER, status TEXT, created_at REAL, did TEXT, trace TEXT,
        metadata TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS episodes (
        id TEXT PRIMARY KEY, drama_id TEXT, episode_num INTEGER, title TEXT,
        duration TEXT, storyboard TEXT, keyframes TEXT, video_url TEXT,
        status TEXT, created_at REAL, content_hash TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    import sqlite3
    return sqlite3.connect(DB_PATH)

@app.route('/api/v1/health')
def health():
    return jsonify({"status": "ok", "service": "drama-platform-sim", "mode": "local_simulation", "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω"})

@app.route('/api/v1/status')
def status():
    conn = get_db()
    c = conn.cursor()
    drama_count = c.execute("SELECT COUNT(*) FROM dramas").fetchone()[0]
    ep_count = c.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    published = c.execute("SELECT COUNT(*) FROM dramas WHERE status='published'").fetchone()[0]
    conn.close()
    return jsonify({"status": "ok", "dramas": drama_count, "episodes": ep_count, "published": published, "mode": "local_simulation"})

@app.route('/api/v1/drama/list')
def drama_list():
    conn = get_db()
    c = conn.cursor()
    rows = c.execute("SELECT id, title, series, character, total_episodes, status, created_at FROM dramas ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify({"status": "ok", "count": len(rows), "dramas": [{"id":r[0],"title":r[1],"series":r[2],"character":r[3],"total_episodes":r[4],"status":r[5],"created_at":r[6]} for r in rows]})

@app.route('/api/v1/drama/<drama_id>')
def drama_detail(drama_id):
    conn = get_db()
    c = conn.cursor()
    row = c.execute("SELECT * FROM dramas WHERE id=?", (drama_id,)).fetchone()
    if not row:
        return jsonify({"status": "not_found", "drama_id": drama_id}), 404
    eps = c.execute("SELECT id, episode_num, title, duration, status, content_hash FROM episodes WHERE drama_id=? ORDER BY episode_num", (drama_id,)).fetchall()
    conn.close()
    return jsonify({"status": "ok", "drama": {"id":row[0],"title":row[1],"series":row[2],"character":row[3],"total_episodes":row[4],"status":row[5],"created_at":row[6],"did":row[7],"trace":row[8],"metadata":json.loads(row[9]) if row[9] else {}}, "episodes": [{"id":e[0],"episode_num":e[1],"title":e[2],"duration":e[3],"status":e[4],"content_hash":e[5]} for e in eps]})

@app.route('/api/v1/drama/create', methods=['POST'])
def drama_create():
    data = request.json or {}
    drama_id = data.get("id", f"DRAMA-{uuid.uuid4().hex[:8].upper()}")
    ts = time.time()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO dramas VALUES (?,?,?,?,?,?,?,?,?,?)",
        (drama_id, data.get("title",""), data.get("series",""), data.get("character",""),
         data.get("total_episodes",0), data.get("status","draft"), ts,
         data.get("did","DID-BR-000002"), data.get("trace","Ω₀⊂⊙∞⊂Ω"),
         json.dumps(data.get("metadata",{}), ensure_ascii=False)))
    conn.commit()
    conn.close()
    return jsonify({"status": "created", "drama_id": drama_id, "created_at": ts})

@app.route('/api/v1/episode/storyboard', methods=['POST'])
def episode_storyboard():
    data = request.json or {}
    ep_id = data.get("episode_id", f"EP-{uuid.uuid4().hex[:8].upper()}")
    storyboard_json = json.dumps(data.get("storyboard",{}), ensure_ascii=False)
    content_hash = hashlib.sha256(storyboard_json.encode()).hexdigest()[:16]
    ts = time.time()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO episodes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (ep_id, data.get("drama_id",""), data.get("episode_num",0), data.get("title",""),
         data.get("duration",""), storyboard_json, "[]", data.get("video_url",""),
         "storyboard_uploaded", ts, content_hash))
    conn.commit()
    conn.close()
    return jsonify({"status": "uploaded", "episode_id": ep_id, "content_hash": content_hash, "shots": len(data.get("storyboard",{}).get("storyboard",[]))})

@app.route('/api/v1/drama/<drama_id>/publish', methods=['PUT'])
def drama_publish(drama_id):
    conn = get_db()
    c = conn.cursor()
    row = c.execute("SELECT id FROM dramas WHERE id=?", (drama_id,)).fetchone()
    if not row:
        return jsonify({"status": "not_found"}), 404
    c.execute("UPDATE dramas SET status='published' WHERE id=?", (drama_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "published", "drama_id": drama_id, "published_at": time.time()})

if __name__ == '__main__':
    print("=" * 50)
    print("短剧平台本地仿真API服务启动")
    print("端口: 8199 | 模式: local_simulation")
    print("DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 50)
    app.run(host='127.0.0.1', port=8199, debug=False)
