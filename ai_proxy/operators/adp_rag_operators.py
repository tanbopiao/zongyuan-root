"""
腾讯云ADP RAG算子 - 增强剧本质量
接入前提：需在腾讯云ADP控制台开通服务并获取密钥
文档：https://cloud.tencent.com.cn/document/product/1759
"""
import requests, json, hashlib, hmac, time, datetime

class ADPRAGOperators:
    """ADP RAG算子组 - 知识库检索增强剧本生成"""
    
    def __init__(self, config):
        self.config = config
        # 从配置读取ADP密钥（未配置时返回提示）
        self.secret_id = config.get("adp_secret_id", "")
        self.secret_key = config.get("adp_secret_key", "")
        self.endpoint = config.get("adp_endpoint", "adp.tencentcloudapi.com")
        self.agent_id = config.get("adp_agent_id", "")
        self.enabled = bool(self.secret_id and self.secret_key and self.agent_id)
    
    def _tc3_sign(self, service, action, payload):
        """腾讯云V3签名"""
        if not self.enabled:
            return None
        try:
            # 简化版TC3签名，实际使用需完整实现
            timestamp = int(time.time())
            date = datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
            
            # 1. 拼接规范请求串
            http_request_method = "POST"
            canonical_uri = "/"
            canonical_querystring = ""
            ct = "application/json; charset=utf-8"
            canonical_headers = "content-type:%s\nhost:%s\nx-tc-action:%s\n" % (ct, self.endpoint, action.lower())
            signed_headers = "content-type;host;x-tc-action"
            hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            canonical_request = (http_request_method + "\n" + canonical_uri + "\n" + canonical_querystring + "\n" + canonical_headers + "\n" + signed_headers + "\n" + hashed_request_payload)
            
            # 2. 拼接待签名字符串
            algorithm = "TC3-HMAC-SHA256"
            credential_scope = date + "/" + service + "/tc3_request"
            hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
            string_to_sign = (algorithm + "\n" + str(timestamp) + "\n" + credential_scope + "\n" + hashed_canonical_request)
            
            # 3. 计算签名
            def sign(key, msg):
                return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
            secret_date = sign(("TC3" + self.secret_key).encode("utf-8"), date)
            secret_service = sign(secret_date, service)
            secret_signing = sign(secret_service, "tc3_request")
            signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
            
            # 4. 拼接Authorization
            authorization = (algorithm + " " + "Credential=" + self.secret_id + "/" + credential_scope + ", " + "SignedHeaders=" + signed_headers + ", " + "Signature=" + signature)
            
            headers = {
                "Authorization": authorization,
                "Content-Type": ct,
                "Host": self.endpoint,
                "X-TC-Action": action,
                "X-TC-Timestamp": str(timestamp),
                "X-TC-Version": "2026-05-20"
            }
            return headers
        except Exception as e:
            print("[ADP RAG] 签名失败:", e)
            return None
    
    def knowledge_search(self, query, top_k=5):
        """算子R1：知识库检索 - 从ADP知识库检索相关内容"""
        if not self.enabled:
            return {"success": False, "error": "ADP未配置，需设置adp_secret_id/adp_secret_key/adp_agent_id", "operator": "R1_search"}
        try:
            payload = json.dumps({"Query": query, "TopK": top_k})
            headers = self._tc3_sign("adp", "KnowledgeSearch", payload)
            if not headers:
                return {"success": False, "error": "签名失败", "operator": "R1_search"}
            r = requests.post("https://" + self.endpoint + "/", data=payload, headers=headers, timeout=30)
            result = r.json()
            return {"success": True, "results": result.get("Results", []), "operator": "R1_search"}
        except Exception as e:
            return {"success": False, "error": str(e), "operator": "R1_search"}
    
    def enhance_script(self, template_name, base_script, knowledge_context=""):
        """算子R2：剧本增强 - 基于RAG检索结果增强剧本质量"""
        if not self.enabled:
            # 未配置ADP时，使用本地增强逻辑
            enhanced = base_script + "\n\n【增强提示】建议参考经典东方神话叙事结构，增加冲突转折和情感高潮。"
            return {"success": True, "script": enhanced, "enhanced_by": "local", "operator": "R2_enhance"}
        try:
            # 1. 检索知识库
            search_result = self.knowledge_search(template_name + " 剧本 故事结构")
            context = knowledge_context
            if search_result.get("success"):
                for item in search_result.get("results", []):
                    context += item.get("Content", "") + "\n"
            
            # 2. 基于检索结果增强剧本
            prompt = "基于以下参考资料，优化剧本：\n参考资料：%s\n\n原剧本：%s\n\n优化要求：增强故事冲突、人物塑造、东方神话元素" % (context[:1000], base_script[:500])
            
            # 调用ADP智能体
            payload = json.dumps({"AgentId": self.agent_id, "Query": prompt})
            headers = self._tc3_sign("adp", "RunAgent", payload)
            if headers:
                r = requests.post("https://" + self.endpoint + "/", data=payload, headers=headers, timeout=60)
                result = r.json()
                enhanced = result.get("Answer", base_script)
                return {"success": True, "script": enhanced, "enhanced_by": "adp_rag", "operator": "R2_enhance"}
            return {"success": True, "script": base_script, "enhanced_by": "fallback", "operator": "R2_enhance"}
        except Exception as e:
            return {"success": False, "error": str(e), "script": base_script, "operator": "R2_enhance"}
    
    def get_status(self):
        """算子R3：ADP配置状态检查"""
        return {
            "success": True,
            "enabled": self.enabled,
            "endpoint": self.endpoint,
            "agent_id_configured": bool(self.agent_id),
            "secret_configured": bool(self.secret_id and self.secret_key),
            "operator": "R3_status"
        }
