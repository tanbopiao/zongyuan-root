"""真值分类分级查询API"""
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Truth Classification API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TRUTH_FILE = "/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json"

def load_truths():
    with open(TRUTH_FILE) as f:
        return json.load(f).get("truths", [])

@app.get("/api/v1/truth/stats")
def stats():
    truths = load_truths()
    from collections import Counter
    return {
        "total": len(truths),
        "by_type": dict(Counter(t.get("type","unknown") for t in truths)),
        "by_level": dict(Counter(t.get("level","unknown") for t in truths)),
        "by_status": dict(Counter(t.get("status","unknown") for t in truths)),
        "by_category": dict(Counter(t.get("category","unknown") for t in truths))
    }

@app.get("/api/v1/truth/filter")
def filter_truths(type: str = None, level: str = None, category: str = None, status: str = None):
    truths = load_truths()
    if type: truths = [t for t in truths if t.get("type") == type]
    if level: truths = [t for t in truths if t.get("level","").startswith(level)]
    if category: truths = [t for t in truths if t.get("category") == category]
    if status: truths = [t for t in truths if t.get("status") == status]
    return {"total": len(truths), "truths": truths[:50]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
