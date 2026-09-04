"""火斗云智 AIOS Python SDK v1.0"""
import requests
class AIOSClient:
    def __init__(self, base_url="http://127.0.0.1", api_key=""):
        self.base_url=base_url.rstrip("/"); self.api_key=api_key
        self.s=requests.Session()
        if api_key: self.s.headers.update({"X-API-Key":api_key})
    def meta_health(self): return self.s.get(f"{self.base_url}/meta/api/v1/meta/health").json()
    def meta_stability(self): return self.s.get(f"{self.base_url}/meta/api/v1/meta/stability").json()
    def license_generate(self, plan="trial", days=30, name="", email=""):
        return self.s.post(f"{self.base_url}/license/api/v1/license/generate",
            json={"plan":plan,"duration_days":days,"customer_name":name,"email":email}).json()
    def gov_scenes(self): return self.s.get(f"{self.base_url}/gov-api/api/v1/scenes").json()
__version__="1.0.0"
