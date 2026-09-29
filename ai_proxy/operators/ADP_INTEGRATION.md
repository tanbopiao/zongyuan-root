# 腾讯云ADP RAG接入指南

## 接入步骤

### 1. 开通ADP服务
- 访问 https://adp.tencentcloud.com/
- 注册/登录腾讯云账号
- 开通智能体开发平台ADP

### 2. 获取API密钥
- 进入ADP控制台 → 右上角头像 → 企业管理 → 密钥管理
- 获取 SecretId 和 SecretKey
- 或使用独立站方式：capi.adp.tencent.com + ClientToken/SignKey

### 3. 创建知识库
- ADP控制台 → 知识库 → 创建知识库
- 上传剧本参考资料（神话故事、经典剧本、角色设定等）
- 等待知识库索引完成

### 4. 创建智能体
- ADP控制台 → 创建应用 → 选择Claw模式或工作流模式
- 挂载刚才创建的知识库
- 配置提示词："你是专业短剧编剧，基于知识库内容优化剧本"
- 发布智能体，获取 AgentId

### 5. 配置到我们的系统
在 /opt/ZONGYUAN-ROOT/ai_proxy/operators/adp_rag_operators.py 中配置：
```python
# 方式1：直接修改默认配置
self.secret_id = "你的SecretId"
self.secret_key = "你的SecretKey"
self.agent_id = "你的AgentId"

# 方式2：通过注册表配置传入
reg = get_registry({
    "adp_secret_id": "xxx",
    "adp_secret_key": "xxx",
    "adp_agent_id": "xxx"
})
```

### 6. 验证配置
```bash
curl -X POST http://127.0.0.1:8021/operators/status
# 检查 adp_rag 算子组
```

## 成本说明
- ADP RAG模型调用收费（embedding + rerank）
- 智能体调用按token计费
- 建议先小额测试，确认效果后再大规模使用

## 算子说明
- R1 knowledge_search: 知识库检索
- R2 enhance_script: 剧本增强（基于RAG结果优化）
- R3 get_status: 配置状态检查

## 剧本增强流程
1. 基础剧本生成（本地LLM）
2. ADP知识库检索相关参考资料
3. ADP智能体基于参考资料优化剧本
4. 返回增强后的剧本
