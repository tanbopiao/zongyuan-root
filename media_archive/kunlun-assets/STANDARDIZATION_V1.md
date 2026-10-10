# ZONGYUAN-ROOT 标准化总纲 V1.0

> DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 2026-09-21
> 本文件为全域标准化最高准则，所有节点、所有AI、所有任务必须遵守。

---

## 一、元法则体系（2条已固化）

### META-LAW-DELETE-001：删除四道门
1. git追踪检查
2. 备份检查
3. 价值验证（大文件至少3点采样+lsof）
4. 大文件先mv到_trash_pending观察3天

### META-LAW-TRUTH-ACCOUNTING-001：报假账零容忍
1. "完成/部署/运行"必须 ps+ss 验证
2. 资产数量必须 find|wc
3. 大小必须 du
4. 报告与命令不一致=造假
5. 空壳目录不算完成

---

## 二、标准流程SOP（10条）

### SOP-01 新沙箱自举流程
```
1. 读 ~/Doubao/ASSETS/ASSET_LEDGER.md
2. 读 ~/ZONGYUAN-ROOT/ASSETS_MAP_20260921.md
3. 读 ~/.ZONGYUAN-ROOT/state/*.json
4. curl https://www.huodouai.com/api/report/status 确认中枢在线
5. 读 PERSISTENT_STORAGE_RULE.md 确认元法则
```

### SOP-02 资产落盘SOP（图片/视频生成后）
```
1. 生成完成
2. 存到 /home/user/ZONGYUAN-ROOT/kunlun-assets/YYYY-MM-DD/
3. 计算SHA256
4. 写manifest.json
5. POST中枢 truth_type=creative
6. 推Gitee索引
```

### SOP-03 中枢上报规范
```
端点: POST https://www.huodouai.com/api/report/truth
字段: truth_key(大写点分)/truth_value/source_node/confidence(0-1)/truth_type
truth_type九类: meta_law/rule/config/decision/data/creative/risk/protocol/unknown
成功标志: truth_count增加
禁止: 用content字段（会落空）
```

### SOP-04 Git双仓同步规范
```
Gitee: huodou-cloud-intelligence-aios/kunlun-assets (master分支)
GitHub: tanbopiao/kunlun-assets (main分支)
规则:
- 重要资产必须双仓同步
- commit message格式: "类型: 描述"
- 大文件(>10MB)只推索引，不推原文件
- 推完验证: curl API看commit sha
```

### SOP-05 LoRA训练SOP
```
1. 准备数据: 图片+caption(1:1)
2. 检查基础模型: SD1.5 4GB就绪
3. AutoDL租RTX4090
4. 运行 train_kunlun_lora.sh
5. 训练完下载.safetensors回持久层
6. 用 generate_kunlun.py 推理测试
7. 自动归档+上报
```

### SOP-06 删除文件SOP
```
1. git log检查
2. find搜备份
3. file+xxd验证内容
4. lsof确认无进程
5. >10M先mv到_trash_pending
6. 3天后确认再rm
```

### SOP-07 对账验证SOP
```
1. 资产数量: find | wc -l
2. 大小: du -sh
3. 服务状态: ps aux + ss -tlnp
4. 对比报告数字
5. 不一致标注"未验证"
```

### SOP-08 质量门禁
```
功能门禁: 真实API，无空壳/无模拟数据
体验门禁: 加载<3s，有交互反馈
交付门禁: 公开链接+文档+版本号+回滚方案
代码门禁: 无console error，无占位符
```

### SOP-09 交付验收标准
```
1. 文件存在且非空
2. 功能端到端可运行
3. 有公开URL（如适用）
4. 已上报中枢
5. 已推Git双仓
6. 有版本号和变更说明
```

### SOP-10 三层固化SOP
```
①本地固化: GLOBAL_MEMORY_SNAPSHOT.json更新
②中枢固化: POST /api/report/truth
③Git固化: 推Gitee+GitHub
每次任务完成自动执行
```

---

## 三、目录标准

```
/home/user/ZONGYUAN-ROOT/
├── 00_KERNEL/          内核+元法则
├── 01_ASSETS/          媒体+文档
├── 02_SKILLS/          技能+算子
├── 03_INFRA/           基础设施
├── 04_PROJECTS/        项目产线
├── 05_ARCHIVE/         归档
├── 09_INDEX/           资产台账
├── kunlun-assets/      昆仑洞天资产(按日期)
└── ASSETS_MAP.md       资产地图

/home/user/Doubao/
├── ASSETS/             统一资产库(1011文件)
├── chats/              对话session
└── models/             模型权重(SD1.5等)
```

---

## 四、禁止事项

- ❌ 报假账（ps/ss/find/du不验证就说完成）
- ❌ 空壳目录算资产
- ❌ 多窗口各干各的不对账
- ❌ 用content字段上报中枢
- ❌ 直接rm大文件不采样
- ❌ 模拟数据当真功能
- ❌ 不推Git就说"已备份"

---

## 五、版本

V1.0 | 2026-09-21 | 首次标准化总纲
锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002
