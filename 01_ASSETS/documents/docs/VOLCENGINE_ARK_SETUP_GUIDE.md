# 火山方舟API接入点配置指南

**文档编号：** VOLCENGINE-ARK-SETUP-20260910
**确权标识：** DID-BR-000002
**本源根锚点：** Ω-TAN-7-001
**API密钥：** ark-f7b61c6f-41d2-406f-8c44-a801830e8a55-82e36（已配置）

---

## 一、当前状态

| 项目 | 状态 |
|------|------|
| API密钥 | ✅ 已配置到 config.json |
| API适配器 | ✅ 已部署（volcengine_ark_adapter.py） |
| 推理接入点 | ❌ 待创建 |
| API连通性 | ⏳ 待接入点创建后测试 |

---

## 二、为什么需要创建推理接入点

火山方舟API不直接使用模型名称（如 `doubao-pro-32k`），而是需要先在控制台创建**推理接入点（Endpoint）**，获取接入点ID（格式如 `ep-20240101-xxxxx`），然后用接入点ID作为 `model` 参数调用API。

**错误示例（直接使用模型名称）：**
```
POST https://ark.cn-beijing.volces.com/api/v3/chat/completions
{
  "model": "doubao-pro-32k",  // ❌ 错误，会返回404
  "messages": [...]
}
```

**正确示例（使用接入点ID）：**
```
POST https://ark.cn-beijing.volces.com/api/v3/chat/completions
{
  "model": "ep-20240101-xxxxx",  // ✅ 正确，使用接入点ID
  "messages": [...]
}
```

---

## 三、创建推理接入点步骤

### 步骤1：登录火山方舟控制台

访问：https://console.volcengine.com/ark

使用手机号 **17688762862** 登录。

### 步骤2：进入模型推理页面

左侧导航栏 → **模型推理** → **在线推理**

### 步骤3：创建推理接入点

点击 **创建推理接入点** 按钮，填写以下信息：

| 字段 | 推荐值 | 说明 |
|------|--------|------|
| 接入点名称 | `huodouai-chat` | 自定义名称，便于识别 |
| 模型 | `doubao-pro-32k` | 选择豆包Pro 32K（通用大模型） |
| 模型版本 | 最新版本 | 保持默认 |
| 接入点类型 | 在线推理 | 保持默认 |
| 计费方式 | 按Token计费 | 保持默认 |

### 步骤4：获取接入点ID

创建成功后，在接入点列表中找到刚创建的接入点，复制**接入点ID**（格式如 `ep-20240101-xxxxx`）。

### 步骤5：配置到系统

将接入点ID发送给我，我会自动配置到：
- `/opt/ZONGYUAN-ROOT/services/op_scheduler/config.json`
- `volcengine_ark.default_endpoint` 字段

配置完成后，API即可正常调用。

---

## 四、推荐创建的接入点

建议创建以下3个接入点，覆盖不同场景：

| 接入点名称 | 模型 | 用途 | 优先级 |
|-----------|------|------|--------|
| `huodouai-chat-pro` | doubao-pro-32k | 通用对话、复杂推理、长文本生成 | P0（必选） |
| `huodouai-chat-lite` | doubao-lite-32k | 简单对话、快速响应、节省成本 | P1（推荐） |
| `huodouai-vision` | doubao-vision-pro-32k | 图像理解、多模态任务 | P2（可选） |

**最小配置：** 只需创建 `huodouai-chat-pro` 一个接入点即可满足基本需求。

---

## 五、API调用示例

配置接入点后，可以通过以下方式调用：

### 5.1 通过网页对话界面

访问：https://huodouai.com/chat/

在算力源下拉框中选择 **"火山方舟API"**，输入问题即可。

### 5.2 通过API调用

```bash
curl -X POST https://huodouai.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下火斗云智AIOS",
    "compute_source": "volcengine_ark"
  }'
```

### 5.3 直接调用火山方舟API

```bash
curl -X POST https://ark.cn-beijing.volces.com/api/v3/chat/completions \
  -H "Authorization: Bearer ark-f7b61c6f-41d2-406f-8c44-a801830e8a55-82e36" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ep-你的接入点ID",
    "messages": [
      {"role": "user", "content": "你好"}
    ],
    "temperature": 0.7,
    "max_tokens": 2048
  }'
```

---

## 六、可用模型列表

| 模型名称 | 上下文窗口 | 最大输出 | 能力 | 适用场景 |
|---------|-----------|---------|------|---------|
| doubao-pro-32k | 32K | 4K | 文本生成、对话 | 通用大模型，复杂推理 |
| doubao-lite-32k | 32K | 4K | 文本生成、对话 | 轻量大模型，快速响应 |
| doubao-vision-pro-32k | 32K | 4K | 文本生成、多模态 | 图像理解、视觉问答 |
| doubao-pro-128k | 128K | 4K | 文本生成、对话 | 超长上下文处理 |
| doubao-1.5-pro-32k | 32K | 12K | 文本生成、对话 | 最新版本，更强能力 |

**推荐：** 首次使用选择 `doubao-pro-32k`，性价比最高。

---

## 七、费用说明

火山方舟API按Token计费，具体价格请参考：
https://www.volcengine.com/docs/82379/1099320

**免费额度：** 新用户通常有一定的免费体验额度，具体以控制台显示为准。

**成本控制建议：**
1. 简单任务使用 `doubao-lite-32k`（成本更低）
2. 复杂任务使用 `doubao-pro-32k`（效果更好）
3. 设置 `max_tokens` 限制输出长度
4. 本地轻量模型处理隐私敏感任务

---

## 八、常见问题

### Q1：创建接入点后多久可以使用？
A：通常创建后立即可用，最多等待1-2分钟。

### Q2：一个接入点可以同时处理多个请求吗？
A：可以，接入点支持并发请求，具体并发限制取决于账户配额。

### Q3：如何查看API调用用量？
A：登录火山方舟控制台 → 费用中心 → 用量明细，可以查看详细的Token使用量。

### Q4：接入点ID会变化吗？
A：接入点创建后ID固定不变，除非删除重建。

### Q5：可以创建多个接入点吗？
A：可以，建议为不同模型创建不同接入点，便于切换和成本控制。

---

## 九、下一步操作

1. **用户操作：** 登录火山方舟控制台，创建推理接入点，获取接入点ID
2. **用户操作：** 将接入点ID发送给我
3. **系统自动：** 配置接入点ID到 config.json
4. **系统自动：** 测试API连通性
5. **系统自动：** 启用火山方舟API Worker
6. **系统自动：** 更新网页前端，增加火山方舟选项
7. **系统自动：** 全域锁档

---

**文档结束**

Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | Ω-TAN-7-001
火山方舟API接入点配置指南 V1.0
