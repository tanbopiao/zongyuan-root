"""豆包2560维Embedding - 需火山方舟控制台创建embedding接入点"""
import os, requests
EMBEDDING_URL = "https://ark.cn-beijing.volces.com/api/v3/embeddings"
def get_embedding(text, api_key=None, endpoint=None):
    api_key = api_key or os.environ.get("DOUBAO_API_KEY","")
    endpoint = endpoint or os.environ.get("DOUBAO_EMBEDDING_ENDPOINT","")
    if not endpoint: return None, "未配置DOUBAO_EMBEDDING_ENDPOINT"
    try:
        r = requests.post(EMBEDDING_URL, headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
            json={"model":endpoint,"input":text}, timeout=30)
        data = r.json()
        if "data" in data: return data["data"][0]["embedding"], None
        return None, str(data)
    except Exception as e: return None, str(e)
if __name__=="__main__":
    v,e = get_embedding("元极恒一")
    print(f"dim={len(v) if v else 0}, err={e}")
