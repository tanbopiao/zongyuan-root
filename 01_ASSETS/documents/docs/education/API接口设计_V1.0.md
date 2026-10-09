# 本源智能普惠教育体系 API 接口设计 V1.0

> 基础路径：`/api/v1`
> 认证方式：API Key（Header: `X-API-Key`）
> 数据格式：JSON（UTF-8）
> 响应统一格式：`{ "code": 0, "message": "success", "data": {...} }`

---

## 一、系统状态接口

### 1.1 获取系统状态
`GET /system/status`

**响应示例**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "system_name": "本源智能普惠教育全自动闭环体系",
    "version": "V1.0",
    "status": "running",
    "did": "DID-BR-000002",
    "uptime": "0:02:35",
    "modules": {
      "knowledge_graph": { "total_entities": 80, "total_relations": 110 },
      "content_engine": { "textbooks": 18, "lesson_plans": 9, "exercises": 63 },
      "adaptive_learning": { "total_learners": 100 },
      "teacher_training": { "total_teachers": 20 },
      "evolution": { "total_cycles": 3 }
    }
  }
}
```

### 1.2 触发自治演化周期
`POST /system/evolve`

**请求体**：
```json
{
  "cycles": 1,
  "mechanisms": ["knowledge_update", "course_iteration", "question_bank"]
}
```

**响应**：返回演化周期结果，包含七大机制执行详情。

---

## 二、知识图谱接口

### 2.1 获取图谱统计
`GET /knowledge/stats`

### 2.2 按域获取知识点
`GET /knowledge/domains/{domain}`

**路径参数**：`domain` — 知识域名称（AI基础理论/机器学习基础/大模型架构/智能体理论/编程实践/数据科学/AI伦理安全/多模态应用/硬件机器人/跨学科融合）

**查询参数**：
- `stage`：学段过滤（小学/初中/高中/中职）
- `page`：页码，默认1
- `page_size`：每页数量，默认20

### 2.3 按学段获取知识点
`GET /knowledge/stages/{stage}`

### 2.4 获取知识点详情
`GET /knowledge/entities/{entity_id}`

**响应**：包含实体属性、前置知识、相关知识。

### 2.5 搜索知识点
`GET /knowledge/search?q={keyword}`

### 2.6 触发知识图谱更新
`POST /knowledge/update`

**请求体**（可选）：
```json
{
  "new_knowledge": [
    { "name": "新知识点", "domain": "大模型架构", "mastery": "理解", "stages": ["高中"] }
  ]
}
```

---

## 三、内容生产接口

### 3.1 生成教材章节
`POST /content/textbook`

**请求体**：
```json
{
  "entity_id": "KP-xxxx",
  "stage": "初中",
  "sections": ["concept", "principle", "case", "practice", "summary"]
}
```

**响应**：返回完整教材章节（5节结构化内容 + 关键要点 + 难度标定 + 合规校验结果）。

### 3.2 生成教案
`POST /content/lesson-plan`

**请求体**：
```json
{
  "chapter_id": "CH-xxxx",
  "duration_minutes": 45
}
```

### 3.3 生成习题
`POST /content/exercises`

**请求体**：
```json
{
  "entity_id": "KP-xxxx",
  "stage": "初中",
  "count": 5,
  "types": ["choice", "fill", "short", "practice"]
}
```

### 3.4 生成实训模板（中职）
`POST /content/training`

**请求体**：
```json
{
  "entity_id": "KP-xxxx",
  "stage": "中职"
}
```

### 3.5 批量生成教学内容
`POST /content/batch`

**请求体**：
```json
{
  "stage": "初中",
  "domains": ["AI基础理论", "AI伦理安全"],
  "max_chapters": 10
}
```

### 3.6 获取已生成内容列表
`GET /content/list?type={textbook|lesson_plan|exercise|training}&stage={stage}&page={page}`

---

## 四、自适应学习接口

### 4.1 创建学习者
`POST /learners`

**请求体**：
```json
{
  "name": "张三",
  "stage": "初中",
  "grade": "初一"
}
```

**响应**：返回学习者ID和初始化画像。

### 4.2 获取学习者画像
`GET /learners/{learner_id}`

### 4.3 生成入学测评
`POST /learners/{learner_id}/placement-test`

**请求体**：`{ "num_questions": 10 }`

### 4.4 提交测评结果
`POST /learners/{learner_id}/test-result`

**请求体**：
```json
{
  "test_id": "TEST-xxxx",
  "answers": [
    { "kp_id": "KP-xxxx", "correct": true },
    { "kp_id": "KP-yyyy", "correct": false }
  ]
}
```

### 4.5 生成个性化学习路径
`GET /learners/{learner_id}/learning-path`

### 4.6 推荐学习内容
`GET /learners/{learner_id}/recommendations`

### 4.7 记录学习活动
`POST /learners/{learner_id}/activity`

**请求体**：
```json
{
  "kp_id": "KP-xxxx",
  "activity_type": "视频学习",
  "duration_minutes": 30,
  "score": 80
}
```

### 4.8 生成学习报告
`GET /learners/{learner_id}/report`

### 4.9 获取班级/群体统计
`GET /learners/class-stats?learner_ids={id1,id2,...}`

---

## 五、师资培育接口

### 5.1 创建教师
`POST /teachers`

**请求体**：
```json
{
  "name": "李老师",
  "subject": "信息科技",
  "school_type": "城区"
}
```

### 5.2 获取教师画像
`GET /teachers/{teacher_id}`

### 5.3 生成培训路径
`GET /teachers/{teacher_id}/training-path`

### 5.4 完成培训课程
`POST /teachers/{teacher_id}/complete-training`

**请求体**：
```json
{
  "course": "AI基础认知",
  "score": 85
}
```

### 5.5 组建教研小组
`POST /teachers/research-group`

**请求体**：
```json
{
  "subject": "数学",
  "teacher_ids": ["TCH-xxxx", "TCH-yyyy"]
}
```

### 5.6 生成教学案例
`POST /teachers/{teacher_id}/teaching-case`

**请求体**：`{ "topic": "AI辅助数学教学" }`

### 5.7 获取培训统计
`GET /teachers/stats`

---

## 六、评估反馈接口

### 6.1 学习效果评估
`POST /evaluation/learning-effect`

**请求体**（可选）：`{ "learner_ids": ["LRN-xxxx"] }`

### 6.2 内容质量评估
`POST /evaluation/content-quality`

**请求体**（可选）：
```json
{
  "content_items": [
    { "type": "textbook", "title": "第X章 人工智能定义" }
  ]
}
```

### 6.3 体系运行评估
`POST /evaluation/system-operation`

### 6.4 生成改进方案
`POST /evaluation/improvement-plan`

**响应**：返回3套备选方案，每套含三维稳态评分（利益/风险/成本）和推荐方案。

### 6.5 获取评估总览
`GET /evaluation/summary`

---

## 七、演化引擎接口

### 7.1 触发单机制演化
`POST /evolution/{mechanism}`

**可用机制**：
- `knowledge_update` — 知识自动更新
- `course_iteration` — 课程自动迭代
- `question_bank` — 题库自动扩充
- `method_optimization` — 教学方法优化
- `resource_balancing` — 资源自动均衡
- `risk_control` — 风险自动防控
- `system_upgrade` — 体系自动升级

### 7.2 运行完整演化周期
`POST /evolution/full-cycle`

### 7.3 获取演化状态
`GET /evolution/status`

### 7.4 获取演化日志
`GET /evolution/log?page={page}&page_size={size}`

---

## 八、归档与确权接口

### 8.1 获取ROOT根库归档列表
`GET /archive/root?type={type}&page={page}`

### 8.2 获取资产哈希确权信息
`GET /archive/{asset_id}/hash`

### 8.3 导出全量数据
`GET /archive/export`

**响应**：返回所有数据文件的下载链接。

---

## 九、错误码

| 错误码 | 含义 |
|--------|------|
| 0 | 成功 |
| 40001 | 参数错误 |
| 40101 | 未授权 / API Key无效 |
| 40401 | 资源不存在 |
| 40901 | 资源冲突 |
| 50001 | 系统内部错误 |
| 50301 | 服务暂不可用 |

---

## 十、调用限制

- 免费额度：1000次/天
- QPS限制：10次/秒
- 单次批量生成上限：50条
- 数据保留：永久归档（ROOT根库不可篡改）

---

**接口版本**：V1.0
**最后更新**：2026-09-13
**确权标识**：DID-BR-000002
