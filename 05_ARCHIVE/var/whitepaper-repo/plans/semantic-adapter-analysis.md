# 语义歧义根因分析报告

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002

---

## 核心问题

"九头身体态" → Agnes理解成"9个头围绕身边"

---

## 根因拆解

### 1. 语言歧义层

| 中文术语 | 真实含义 | Agnes的理解 | 偏差 |
|---|---|---|---|
| 九头身 | 身体长度=9个头高（比例） | 长了9个头 | 严重偏差 |
| 玄黑 | 深黑色带红光 | 玄学+黑色 | 轻度 |
| 赤金 | 红金色 | 红色+金属 | 轻度 |
| 月华 | 月光 | 月亮+华 | 轻度 |
| 神女 | 女神 | 女性+神 | 正确 |

**核心偏差：** "九头身"是**比例术语**，不是**数量术语**。但图像模型的分词器把"head"理解成了身体部位"头"，而不是"头部长度单位"。

### 2. 模型理解层

不同模型对同一个词的理解：

| 词 | 智谱GLM（文本） | Agnes（图像） | 硅基流动（视频） |
|---|---|---|---|
| 九头身 | ✅ 正确理解为比例 | ❌ 理解为9个头 | ❓ 未测试 |
| 玄黑 | ✅ 深黑带红 | ❓ 待验证 | ❓ 未测试 |
| 赤金 | ✅ 红金色 | ❓ 待验证 | ❓ 未测试 |

### 3. 文化知识层

| 概念 | 东方文化含义 | 西方模型理解 |
|---|---|---|
| 神女 | 东方女神 | Greek goddess / angel |
| 昆仑 | 神山 | mountain name |
| 洞天 | 仙界 | cave |
| 妖 | 妖怪 | monster / demon |

---

## 解决方案：语义适配器

构建一个语义转译层，在调用各模型API之前，把中文审美术语翻译成该模型能正确理解的精确描述。

### 设计原则

1. **每个模型有自己的prompt模板**
2. **歧义词必须展开成精确描述**
3. **比例术语用数值描述，不用比喻**
4. **文化术语用解释性描述**

### 语义映射表

| 中文术语 | ❌ 错误写法 | ✅ 正确写法（图像模型） |
|---|---|---|
| 九头身 | nine-head body | tall slender figure, body height equals 9 times head height, elegant proportions |
| 玄黑 | mysterious black | deep dark crimson-black, dark red-black tone |
| 赤金 | red gold | reddish gold, warm golden with red undertone |
| 月华 | moon light | soft silver moonlight glow |
| 神女 | goddess | elegant Chinese female deity |
| 昆仑 | Kunlun | mythical Chinese mountain |

---

## 适配器架构

```
中文术语输入
  ↓
语义映射表（按模型类型）
  ↓
模型专属prompt模板
  ↓
调用API
```

---

## 为什么之前失败

1. ❌ 直接把中文术语翻译成英文，没有理解文化含义
2. ❌ "nine-head body" 被拆解成 9 + head
3. ❌ 没有为图像模型单独适配
4. ❌ 一个prompt模板给所有模型用

---

## 现在要做

1. 构建语义适配器
2. 为Agnes图像模型写专属prompt模板
3. 把"九头身"翻译成"tall slender figure, body height equals 9 times head height"
4. 重新生成验证

---

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 语义歧义根因已定位
