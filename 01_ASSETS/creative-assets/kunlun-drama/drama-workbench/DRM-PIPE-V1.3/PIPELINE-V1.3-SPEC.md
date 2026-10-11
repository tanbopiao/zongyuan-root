# DRM-PIPE V1.3 · 接口规范（PIPELINE-V1.3-SPEC）

> 供"一键量产引擎"代理按本文件消费模板包与硬约束校验器。
> DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 本目录不修改/不发布任何页面 HTML，仅产出文件。

## 0. 根路径

```
ROOT = /home/user/Doubao/chats/1128121028098/drama-workbench/DRM-PIPE-V1.3/
```

## 1. 模板包（5 件，只读消费）

| 件 | 绝对路径 | 用途 |
|---|---|---|
| 分镜表模板 | `ROOT/分镜表模板.json` | 量产分镜表的 JSON 骨架（含 validation 校验字段） |
| 分镜表模板 | `ROOT/分镜表模板.md` | 人读字段表/节拍规范 |
| 关键帧提示词模板 | `ROOT/关键帧提示词模板.md` | 风格锁定块 + 长兵器铁律块原文 + 人体结构禁止块（不可省略前置约束） |
| 配音台词模板 | `ROOT/配音台词模板.md` | 单条台词结构 + 角色口吻表 |
| 素材包目录规范 | `ROOT/素材包目录规范.md` | ZIP 结构 / 命名规则 / manifest 格式 |

## 2. 硬约束校验器

```
ROOT = /home/user/Doubao/chats/1128121028098/drama-workbench/DRM-PIPE-V1.3/drama_validator.py
```

- 纯 Python 标准库，零第三方依赖，UTF-8，中文注释。
- Python 3，可直接 `import drama_validator` 调用三个函数，也可走 CLI。

### 2.1 编程接口（供引擎内嵌调用）

```python
import drama_validator as dv

# (1) 单条关键帧提示词校验 → {"status":"pass|warn|fail","issues":[...]}
r1 = dv.validate_keyframe_prompt(text)

# (2) 长兵器三级判定 → {"level":"pass|warn|fail|NA","wielded":bool,"issues":[...]}
r2 = dv.validate_long_weapon(prompt, has_weapon=None)   # has_weapon 传分镜表 hasWeapon 元数据更准

# (3) 整集分镜表校验 → {"status":...,"shots":[...],"summary":{...}}
r3 = dv.validate_episode(storyboard_dict)
```

返回约定：
- `status/level` 取值 `pass / warn / fail`（长兵器另含 `NA`=无长兵器）。
- `issues[i] = {"level":"fail"|"warn", "msg":str}`。
- **人体结构红线命中恒为 `fail`，不降级为 `warn`**；否定式保护语（"绝不狰狞雄性化/不血腥"）自动豁免。

### 2.2 CLI（供引擎壳调用）

```bash
python3 drama_validator.py --check-file <file>
```

- 自动识别：`.json` 且含 `shots` → 按整集分镜表校验；`.txt/.md` 含 `【KF-…】` → 逐条关键帧校验。
- stdout：逐条 `PASS/WARN/FAIL` + 汇总（镜级/条级计数）。
- 退出码：含 fail → `1`；否则 `0`；文件/解析错误 → `2`。引擎应据退出码决定打回重绘。

## 3. 引擎标准输入 / 输出

| 环节 | 输入 | 输出 |
|---|---|---|
| 分镜生成 | 大纲文本（`S01: …` 逐行） | `分镜表_EPXX.json`（字段兼容 `id/shot_id`、`desc/description`、`kfPrompt/keyframe_prompt`、`duration`、`transition`、`hasWeapon`） |
| 关键帧 | 分镜表 JSON | `关键帧提示词集_EPXX.txt`（每 `【KF-NNN】` 一段） |
| 校验闸门 | 上述 JSON / TXT | 校验结论（fail>0 则打回，禁止打包归档） |
| 配音 | 分镜表 | `配音台词脚本_EPXX.txt` |
| 打包 | 上述全部 | 按《素材包目录规范.md》ZIP + manifest（含 `validatorSummary`） |

## 4. 硬约束（校验器强制，引擎不得绕过）

1. 人体结构禁止（面部雄性化/狰狞、神女残魂恐怖鬼魅、血腥）= **fail 级 reject**。
2. 时长每镜 5–15s；转场仅硬切/闪白/快切；禁慢淡入淡出/溶解/渐隐渐显。
3. 每帧必含 `9:16竖屏` 与 `右下角Ω₀⊂⊙∞⊂Ω`；缺锁定项 = warn。
4. 手持长兵器（矛/枪/戟/棍/戈/长刀）必附结构铁律四条关键短语：`几何连续` / `安全空域` / `双手握持` / `光效不覆盖实体`。
5. 未知存在/凶兽只露局部不露全貌；角色跨镜形态不得漂移冲突。

## 5. 本次实跑样例（引擎可读的参考实现）

| 文件 | 路径 |
|---|---|
| 新样例分镜表 JSON | `ROOT/分镜表_样例.json`（8 镜，全 PASS） |
| 新样例分镜表 MD | `ROOT/分镜表_样例.md` |
| 新样例关键帧集 | `ROOT/关键帧提示词集_样例.txt`（8 条，全 PASS） |
| keyframe_generator 报告 | `ROOT/keyframe_lock_report_EP02灵纹重燃_20261002.json` |
| 真实校验统计 | `ROOT/校验报告.md` |
