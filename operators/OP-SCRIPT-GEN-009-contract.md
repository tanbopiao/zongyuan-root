# OP-SCRIPT-GEN-009｜剧本生成算子

> 算子编号：OP-SCRIPT-GEN-009
> 归属体系：昆仑洞天 IP 内容生产
> 状态：契约定稿 v1.0

---

## 一、真值契约

### 目标
读取世界观设定 + 角色库 + 大纲，自动生成分镜剧本（含场景描述、动作、对白、镜头建议），输出可直接喂给 OP-BATCH-GEN-004 的 storyboard.json。

### 执行流程
```
Step1  读取世界观设定（worldview.md）、角色库（characters.md）、单集大纲（episode_outline.md）
Step2  按情绪逻辑编排：铺垫→发展→爆点→转折→收尾
Step3  为每个节拍生成：
        - 场景描述（地点、时间、氛围）
        - 角色动作
        - 对白（如有）
        - 镜头建议（景别、角度、运镜）
        - 关键帧提示词（用于OP-BATCH-GEN-004）
Step4  输出 storyboard.json（OP-BATCH-GEN-004 的输入格式）
Step5  同时输出剧本可读版 script.md（人类阅读）
Step6  写入 /scripts/EP{xx}/ 目录
Step7  输出回执
```

### 输入
```json
{
  "op_name": "OP-SCRIPT-GEN-009",
  "worldview_path": "/config/worldview.md",
  "characters_path": "/config/characters.md",
  "episode_outline": "EP10-第一塔试炼：玄女入塔，面对心象试炼",
  "ep_number": 10,
  "target_shots": 6
}
```

### 输出
```
scripts/EP10/
├── script.md          ← 人类可读剧本
├── storyboard.json    ← 机器可读，喂给OP-BATCH-GEN-004
└── log.json           ← 生成日志
```

### 禁止项
- ❌ 禁止生成违背世界观设定的剧情
- ❌ 禁止添加非角色库中的人物
- ❌ 禁止生成西方化场景（严格东方纯粹性）
- ❌ 关键帧提示词必须包含 9:16、玄黑/古金/青玉/朱红色系

---

## 二、测试用例

| 编号 | 场景 | 预期 |
|---|---|---|
| TC-01 | EP10大纲输入 | 输出6个分镜，storyboard.json格式合法 |
| TC-02 | 世界观文件缺失 | 报错，不生成空剧本 |
| TC-03 | 角色库中不存在的人物 | 拒绝生成，提示角色未定义 |
| TC-04 | 提示词含西方铠甲 | 自动过滤，替换为东方元素 |
| TC-05 | storyboard.json可被OP-BATCH-GEN-004直接读取 | 格式校验通过 |
