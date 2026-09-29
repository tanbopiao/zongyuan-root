#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT HRM Minimal System V1.2 (Port 8040)
人力资源管理系统·完整功能版
DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
功能:
  - 简历上传(PDF/文本) + OCR解析(结构化提取)
  - 企业/岗位管理(CRUD)
  - 简历-岗位智能匹配(技能/经验/学历加权打分)
  - 数据持久化(JSON文件)
  - 健康检查 + 统计
"""
import json, os, re, time, uuid, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8040
START_TS = time.time()
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DATA_FILE = os.path.join(DATA_DIR, 'hrm_data.json')
LOCK = threading.Lock()

DEFAULT_DATA = {"resumes": [], "companies": [], "jobs": [], "matches": [], "ocr_jobs": []}

def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return json.loads(json.dumps(DEFAULT_DATA))

def save_data(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_resume_text(text):
    """简历文本结构化解析：姓名/电话/邮箱/技能/学历/经验"""
    r = {"name": "", "phone": "", "email": "", "skills": [], "education": "", "experience_years": 0}
    # 姓名：常见在首行或"姓名：xxx"
    m = re.search(r'姓名[:：]\s*([\u4e00-\u9fa5]{2,4})', text)
    if m: r['name'] = m.group(1)
    elif text.strip(): r['name'] = text.strip().split('\n')[0][:8]
    m = re.search(r'(1[3-9]\d{9})', text)
    if m: r['phone'] = m.group(1)
    m = re.search(r'([\w.+-]+@[\w-]+\.[\w.]+)', text)
    if m: r['email'] = m.group(1)
    # 技能关键词库
    skill_keywords = ['python', 'java', 'sql', 'linux', 'docker', 'k8s', 'kubernetes', '算法', '机器学习',
                      '深度学习', 'pytorch', 'tensorflow', '数据分析', '产品设计', '项目管理', 'java',
                      'golang', '前端', 'react', 'vue', 'spring', '微服务', 'ai', '大模型', 'prompt', '测试',
                      '运维', '自动化', 'c++', 'c#', 'php', 'mysql', 'redis', 'kafka', 'hadoop', 'spark',
                      'flink', 'nlp', 'cv', '推荐系统', '风控', 'gis', 'unity', 'flutter', 'ios', 'android']
    for kw in skill_keywords:
        if kw.lower() in text.lower() and kw not in r['skills']:
            r['skills'].append(kw)
    m = re.search(r'(本科|硕士|博士|大专|高中)', text)
    if m: r['education'] = m.group(1)
    m = re.search(r'(\d+)\s*年(?:以上)?(?:工作)?经验', text)
    if m: r['experience_years'] = int(m.group(1))
    else:
        years = re.findall(r'(\d{4})年', text)
        if len(years) >= 2:
            r['experience_years'] = max(0, int(years[-1]) - int(years[0]))
    return r

def extract_text_from_pdf(data):
    """PDF文本提取（轻量，无重型依赖）：尝试PyPDF2/pypdf，失败回退字节扫描"""
    try:
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        import io
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or '' for page in reader.pages)
    except Exception:
        # 回退：扫描文本层字节
        try:
            return data.decode('utf-8', errors='ignore')
        except Exception:
            return ""

def match_score(resume, job):
    """简历-岗位匹配打分：技能60% + 学历20% + 经验20%"""
    score = 0
    job_req = job.get('required_skills', [])
    if job_req:
        hit = sum(1 for s in job_req if s.lower() in [x.lower() for x in resume.get('skills', [])])
        score += 60 * hit / max(len(job_req), 1)
    edu_map = {'博士': 20, '硕士': 18, '本科': 15, '大专': 10, '高中': 5, '': 8}
    min_edu = job.get('min_education', '')
    r_edu = resume.get('education', '')
    if min_edu:
        score += min(20, edu_map.get(r_edu, 8) + 5) if edu_map.get(r_edu, 0) >= edu_map.get(min_edu, 0) else edu_map.get(r_edu, 8) * 0.5
    else:
        score += edu_map.get(r_edu, 8)
    exp_req = job.get('min_experience', 0)
    score += min(20, 20 * resume.get('experience_years', 0) / max(exp_req, 1)) if exp_req else min(20, resume.get('experience_years', 0) * 3)
    return round(min(100, score), 1)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        try:
            ln = int(self.headers.get('Content-Length', 0))
            return self.rfile.read(ln) if ln else b''
        except Exception:
            return b''

    def do_GET(self):
        p = self.path.split('?')[0]
        data = load_data()
        if p in ('/health', '/healthz'):
            self._send(200, {"status": "healthy", "service": "hrm", "port": PORT,
                             "version": "V1.2", "uptime": round(time.time()-START_TS, 1),
                             "stats": {k: len(v) for k, v in data.items()},
                             "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω"})
        elif p == '/api/stats':
            self._send(200, {"stats": {k: len(v) for k, v in data.items()}})
        elif p == '/api/resumes':
            self._send(200, {"resumes": data['resumes']})
        elif p == '/api/resumes/search':
            q = (self.path.split('?')[1] or '') if '?' in self.path else ''
            qs = dict(kv.split('=') for kv in q.split('&') if '=' in kv)
            kw = qs.get('q', '').lower()
            res = [r for r in data['resumes'] if kw in r.get('name', '').lower() or any(kw in s.lower() for s in r.get('skills', []))]
            self._send(200, {"resumes": res, "count": len(res)})
        elif p == '/api/companies':
            self._send(200, {"companies": data['companies']})
        elif p == '/api/jobs':
            self._send(200, {"jobs": data['jobs']})
        elif p == '/api/matches':
            self._send(200, {"matches": data['matches']})
        elif p == '/api/matches/recommend':
            # 推荐：对每份简历算最高分岗位
            recs = []
            for r in data['resumes']:
                best = max([(match_score(r, j), j) for j in data['jobs']], default=(0, None), key=lambda x: x[0])
                if best[1] and best[0] > 0:
                    recs.append({"resume_id": r['id'], "resume_name": r.get('name', ''),
                                 "job_id": best[1]['id'], "job_title": best[1].get('title', ''),
                                 "score": best[0]})
            self._send(200, {"recommendations": recs, "count": len(recs)})
        elif p == '/api/ocr/jobs':
            self._send(200, {"ocr_jobs": data['ocr_jobs']})
        else:
            self._send(404, {"status": "not_found"})

    def do_POST(self):
        p = self.path.split('?')[0]
        data = load_data()
        ctype = self.headers.get('Content-Type', '')
        body = self._read_body()

        if p in ('/api/resumes/upload', '/api/upload', '/api/pdf/upload'):
            # 文件上传（PDF或文本）
            filename = ''
            text = ''
            if 'multipart/form-data' in ctype:
                # 简易multipart解析
                import email
                import io
                try:
                    msg = email.message_from_bytes(b'Content-Type: ' + ctype.encode() + b'\r\nMIME-Version: 1.0\r\n\r\n' + body)
                    for part in msg.walk():
                        if part.get_content_disposition() == 'form-data':
                            name = part.get_param('name', header='content-disposition')
                            fname = part.get_filename()
                            if fname:
                                filename = fname
                                raw = part.get_payload(decode=True) or b''
                                text = extract_text_from_pdf(raw) if fname.lower().endswith('.pdf') else raw.decode('utf-8', errors='ignore')
                except Exception as e:
                    text = f"multipart parse error: {e}"
            else:
                try:
                    j = json.loads(body or b'{}')
                    filename = j.get('filename', 'unknown.txt')
                    text = j.get('text', '')
                except Exception:
                    text = body.decode('utf-8', errors='ignore')
            rid = uuid.uuid4().hex[:12]
            parsed = parse_resume_text(text)
            parsed.update({"id": rid, "filename": filename, "status": "parsed",
                           "ts": time.strftime('%Y-%m-%d %H:%M:%S')})
            with LOCK:
                data['resumes'].append(parsed)
                save_data(data)
            self._send(200, {"status": "ok", "resume_id": rid, "parsed": parsed,
                             "ocr_endpoint": True, "raw_text_len": len(text)})
        elif p == '/api/resumes':
            try:
                j = json.loads(body or b'{}')
            except Exception:
                j = {}
            j.update({"id": uuid.uuid4().hex[:12], "ts": time.strftime('%Y-%m-%d %H:%M:%S')})
            with LOCK:
                data['resumes'].append(j)
                save_data(data)
            self._send(200, {"status": "ok", "resume_id": j['id'], "count": len(data['resumes'])})
        elif p == '/api/companies':
            try:
                j = json.loads(body or b'{}')
            except Exception:
                j = {}
            j.update({"id": uuid.uuid4().hex[:12]})
            with LOCK:
                data['companies'].append(j)
                save_data(data)
            self._send(200, {"status": "ok", "company_id": j['id'], "count": len(data['companies'])})
        elif p == '/api/jobs':
            try:
                j = json.loads(body or b'{}')
            except Exception:
                j = {}
            j.update({"id": uuid.uuid4().hex[:12]})
            with LOCK:
                data['jobs'].append(j)
                save_data(data)
            # 自动对全部简历匹配
            with LOCK:
                data['matches'] = [{"resume_id": r['id'], "job_id": j['id'], "score": match_score(r, j)}
                                   for r in data['resumes']]
                save_data(data)
            self._send(200, {"status": "ok", "job_id": j['id'], "count": len(data['jobs'])})
        elif p == '/api/matches/run':
            with LOCK:
                data['matches'] = [{"resume_id": r['id'], "job_id": jj['id'], "score": match_score(r, jj)}
                                   for r in data['resumes'] for jj in data['jobs']]
                save_data(data)
            self._send(200, {"status": "ok", "match_count": len(data['matches'])})
        else:
            self._send(404, {"status": "not_found"})

    def do_DELETE(self):
        p = self.path.split('?')[0]
        data = load_data()
        m = re.match(r'/api/(\w+)/(\w+)', p)
        if m:
            kind, rid = m.group(1), m.group(2)
            if kind in data and any(x.get('id') == rid for x in data[kind]):
                with LOCK:
                    data[kind] = [x for x in data[kind] if x.get('id') != rid]
                    save_data(data)
                self._send(200, {"status": "deleted", "kind": kind, "id": rid})
                return
        self._send(404, {"status": "not_found"})

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"[hrm-v1.2] starting on :{PORT} {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
