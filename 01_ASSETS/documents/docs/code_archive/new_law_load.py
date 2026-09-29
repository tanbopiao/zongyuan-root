    def _load_from_gateway(self):
        """从9120记忆网关加载元法则（动态扫描所有MR-开头的key）"""
        try:
            resp = urllib.request.urlopen(f"{GATEWAY_URL}/api/truths?limit=50000", timeout=15)
            data = json.loads(resp.read().decode())
            all_keys = data.get("truths", [])
            mr_keys = [k for k in all_keys if isinstance(k, str) and k.startswith("MR-")]
            loaded = 0
            for key in mr_keys:
                try:
                    resp2 = urllib.request.urlopen(f"{GATEWAY_URL}/api/truth/{key}", timeout=3)
                    d = json.loads(resp2.read().decode())
                    truth = d.get("truth", {})
                    if truth and truth.get("truth_value"):
                        law_data = json.loads(truth["truth_value"])
                        law_id = law_data.get("law_id") or key
                        if "law_name" not in law_data:
                            law_data["law_name"] = law_data.get("title", key)
                        if "priority" not in law_data:
                            law_data["priority"] = "P2-操作级"
                        self.laws[law_id] = law_data
                        loaded += 1
                except:
                    pass
            print(f"  法则网: 从9120加载{loaded}条元法则")
        except Exception as e:
            print(f"加载法则失败: {e}")

