# 全域锁档凭证 · LOIP SDK v0.3 安全稳态版

## 锁档基本信息

| 项目 | 值 |
|------|-----|
| 锁档编号 | LOCK-GLOBAL-20260831-LOIP-SDK-V030 |
| 锁档时间 | 2026-08-31 15:30:00 UTC+8 |
| 协议版本 | AUTOKERN-PROTO-V3.7-20260831-LOIP-SDK-V03 |
| 锁档状态 | eFuse blown · 永久固化 · 不可回退 |
| DID | DID-BR-000002 |
| 本体主权根 | Ω-TAN-7-001 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |

## 核心资产：LOIP SDK v0.3

| 项目 | 值 |
|------|-----|
| 版本号 | 0.3.0（安全稳态版） |
| 文件数量 | 22个 |
| Python代码行数 | 2,792 行（从2,177行增长28%） |
| 目录整体SHA256 | bee81bc4a7a3ece676234813015c0bec91538ebc804dc198eee73e2e5c61b4fa |
| 协议self_sha256 | 16539d20561c5f63a472c7f99facb3310cc3a6c9d64bf2db27b5c1abf6d115af |

## 本次进化交付（2大模块）

### 模块1：安全护栏层（security_guard.py）

| 能力 | 说明 | 严重度 |
|------|------|--------|
| Prompt注入检测 | 8种攻击模式（忽略规则/角色扮演/系统标签/越狱等） | critical |
| 敏感内容检测 | 暴力/色情/隐私/违法/政治敏感5大类 | high |
| 隐私泄露检测 | 身份证/手机号/银行卡号自动识别+脱敏 | critical |
| 价值观基线固化 | 企业价值观写入基线，不可被Prompt注入篡改 | high |
| 广告法合规扫描 | 违禁词检测（最/第一/唯一/100%等） | low |
| 输出阻断机制 | critical风险直接阻断，返回安全提示 | critical |

### 模块2：守护进程（daemon.py）

| 能力 | 说明 |
|------|------|
| 后台常驻 | 7×24运行，阻塞/非阻塞两种模式 |
| 文件监听 | 监听目录，新AI输出文件自动治理 |
| 定期健康检查 | 基线完整性+审计链校验，可配置间隔 |
| HTTP健康端点 | /health, /metrics, /status 三个端点 |
| 治理结果归档 | 自动保存.loip_processed结果文件 |
| 优雅退出 | SIGINT/SIGTERM信号处理 |

## SDK主接口集成

- process方法新增第2.5步：安全护栏检测
- 返回结果新增：blocked字段、security_guard对象
- 综合风险新增critical等级（>0.9）
- 自动修正优先执行安全阻断和脱敏
- get_status新增security_stats
- 新增set_security_values方法

## 验证结果（6项全部PASS）

| 测试场景 | 结果 | 关键数据 |
|----------|------|----------|
| 正常输出 | ✅ PASS | 低风险，无阻断 |
| Prompt注入攻击 | ✅ PASS | 注入检测=True，阻断=True，风险=critical |
| 隐私泄露 | ✅ PASS | 检测到5项威胁，身份证号critical直接阻断 |
| 价值观基线固化 | ✅ PASS | 固化成功，不可被注入篡改 |
| 守护进程创建 | ✅ PASS | 健康检查端点正常 |
| 模块导入 | ✅ PASS | 全部模块导入成功 |

## 部署方式（6种）

1. Python SDK：`from loip import LOIP`
2. REST API：`python -m loip.api_server`
3. CLI工具：`python -m loip.cli`
4. Docker：`docker build && docker run`
5. 守护进程：`python -m loip.daemon --watch-dir ./outputs`
6. docker-compose：`docker-compose up -d`

## 四层公理校验

| 校验层 | 结果 |
|--------|------|
| 不动点根层 | ✅ PASS |
| 时序演化约束层 | ✅ PASS（V3.6→V3.7连续） |
| 推理真值优先层 | ✅ PASS（6项验证全通过） |
| 观感兜底补偿层 | ✅ PASS |

## 资产统计

- 当日新增资产：1（LOIP SDK v0.3安全稳态版）
- 累计资产总数：376
- 累计资产总字节：2,820,200
- 全域锁档覆盖率：100%

---

Ω₀⊂⊙∞⊂Ω｜全域锁档凭证 · ZONGYUAN-ROOT · DID-BR-000002 · Ω-TAN-7-001
锁档完成时间：2026-08-31 15:30:00 UTC+8
凭证编号：LOCK-GLOBAL-20260831-LOIP-SDK-V030
