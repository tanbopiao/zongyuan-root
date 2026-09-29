# 火斗云智AIOS · 高效中台架构拓扑图

> 确权锚点: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 元极恒一全域自治体系  
> 架构原则: 业务先行,中台后建 | 能力沉淀,复用解耦 | 统一治理,可观测可演化

---

## 一、五层中台总体架构

```mermaid
graph TB
    subgraph 前台业务层["🖥️ 前台业务层（差异化逻辑）"]
        F1[短剧PV流水线]
        F2[飞书AI同事]
        F3[本地AIOS实例]
        F4[官网门户/控制台]
        F5[移动端H5]
    end

    subgraph 数据中台["📊 数据中台（统一数据口径）"]
        D1[数据接入ETL]
        D2[数仓分层 ODS/DWD/DWS/ADS]
        D3[指标统一管理]
        D4[数据服务API]
        D5[元数据与血缘]
        D6[数据权限脱敏]
    end

    subgraph 业务中台["🏢 业务中台（业务能力沉淀）"]
        B1[角色元规则库]
        B2[关键帧资产库]
        B3[分镜台账管理]
        B4[全域锁档归档]
        B5[短剧流水线编排]
        B6[质检异常台账]
    end

    subgraph 技术中台["⚙️ 技术中台（技术能力复用）"]
        T1[统一身份SSO]
        T2[AI能力网关]
        T3[文件素材中心]
        T4[消息推送网关]
        T5[任务调度工作流]
        T6[分布式锁幂等]
    end

    subgraph 基础设施层["🏗️ 基础设施层（算力存储网络）"]
        I1[容器编排 K8s/Docker]
        I2[统一配置中心]
        I3[日志监控告警 ELK/Prometheus]
        I4[对象存储 MinIO/COS]
        I5[消息队列 MQ/Kafka]
        I6[数据库 多源适配]
    end

    %% 前台消费中台
    F1 --> B5
    F1 --> B1
    F1 --> B2
    F2 --> T4
    F2 --> T1
    F3 --> T2
    F4 --> B4
    F5 --> T3

    %% 业务中台消费技术中台
    B1 --> T3
    B2 --> T3
    B4 --> T6
    B5 --> T5
    B5 --> T2
    B6 --> T5

    %% 数据中台消费所有层
    D1 --> I6
    D2 --> D1
    D3 --> D2
    D4 --> D3
    D5 --> D2
    D6 --> T1

    %% 技术中台消费基础设施
    T1 --> I2
    T2 --> I5
    T3 --> I4
    T4 --> I5
    T5 --> I5
    T6 --> I3

    style 前台业务层 fill:#e8f4fd,stroke:#2196f3
    style 数据中台 fill:#fff3e0,stroke:#ff9800
    style 业务中台 fill:#f3e5f5,stroke:#9c27b0
    style 技术中台 fill:#e8f5e9,stroke:#4caf50
    style 基础设施层 fill:#fce4ec,stroke:#e91e63
```

---

## 二、AI能力网关核心拓扑（技术中台核心）

```mermaid
graph LR
    subgraph 接入层["接入层"]
        A1[REST API]
        A2[WebSocket]
        A3[SDK调用]
    end

    subgraph 网关核心["AI能力网关"]
        G1[请求路由]
        G2[模型调度]
        G3[额度管控]
        G4[提示词模板]
        G5[潜空间锚点]
        G6[结果缓存]
    end

    subgraph 模型层["模型层"]
        M1[豆包系列]
        M2[Seedream图像]
        M3[Seedance视频]
        M4[本地Ollama]
        M5[第三方API]
    end

    subgraph 治理层["治理层"]
        V1[限流熔断]
        V2[调用审计]
        V3[质量评分]
        V4[成本统计]
    end

    A1 --> G1
    A2 --> G1
    A3 --> G1
    G1 --> G2
    G2 --> M1
    G2 --> M2
    G2 --> M3
    G2 --> M4
    G2 --> M5
    G2 --> G3
    G2 --> G4
    G2 --> G5
    G2 --> G6
    G1 --> V1
    G2 --> V2
    G2 --> V3
    G3 --> V4

    style 网关核心 fill:#fff3e0,stroke:#ff9800,stroke-width:3px
```

---

## 三、短剧生产流水线业务拓扑（业务中台核心）

```mermaid
graph LR
    S[剧本生成] --> F[分镜脚本]
    F --> K[关键帧生成]
    K --> V[视频生成]
    V --> A[配音合成]
    A --> M[合并输出]
    M --> Q[质检归档]

    subgraph 中台支撑["中台能力支撑"]
        B1[角色元规则库]
        B2[关键帧资产库]
        B3[分镜台账]
        B4[锁档归档]
        T2[AI能力网关]
        T5[任务调度]
    end

    S -.-> T2
    F -.-> B3
    K -.-> B1
    K -.-> B2
    K -.-> T2
    V -.-> T2
    A -.-> T2
    Q -.-> B4
    S -.-> T5
    F -.-> T5
    K -.-> T5
    V -.-> T5

    style 中台支撑 fill:#e8f5e9,stroke:#4caf50
```

---

## 四、全域治理与可观测拓扑

```mermaid
graph TB
    subgraph 治理体系["全域治理体系"]
        G1[API网关 限流熔断]
        G2[版本管控 语义化版本]
        G3[全链路追踪 TraceID]
        G4[权限审计 应用鉴权]
        G5[变更管控 评审发布]
    end

    subgraph 可观测["可观测体系"]
        O1[指标监控 Prometheus]
        O2[日志聚合 ELK]
        O3[链路追踪 Jaeger]
        O4[告警通知 飞书/短信]
        O5[仪表盘 Grafana]
    end

    subgraph 数据来源["数据来源"]
        D1[14个业务服务]
        D2[4个管控服务]
        D3[Nginx网关]
        D4[系统资源]
    end

    D1 --> G1
    D2 --> G1
    D3 --> G1
    G1 --> O1
    G1 --> O2
    G3 --> O3
    G4 --> O2
    O1 --> O5
    O2 --> O5
    O3 --> O5
    O1 --> O4
    O2 --> O4

    style 治理体系 fill:#fce4ec,stroke:#e91e63
    style 可观测 fill:#e8f4fd,stroke:#2196f3
```

---

## 五、星型协同中台调度拓扑（同源协议）

```mermaid
graph TB
    subgraph 中枢主窗口["中枢主窗口（道）· 云内核统一管控中心"]
        H[中枢调度器 :9000]
        GW[统一接入网关 :8889]
        VCE[版本管控引擎 :8890]
        CFG[配置中心 :8891]
    end

    subgraph 专业窗口边缘节点["专业窗口（边缘节点）"]
        W1[火斗云智中台
认知中台]
        W2[昆仑洞天短剧母机
短剧生产]
        W3[政务专业窗口
政务AI]
        W4[云运维专业窗口
部署运维]
        W5[本地内核专业窗口
内核开发]
    end

    subgraph 业务服务节点["业务服务节点（10个）"]
        S1[dashboard]
        S2[feishu_bridge]
        S3[three_dim]
        S4[autonomy]
        S5[midplatform_healing]
        S6[deep_healing]
        S7[website_healing]
        S8[learning]
        S9[operator_collab]
        S10[feishu_scan]
    end

    W1 -->|注册/心跳/任务| GW
    W2 -->|注册/心跳/任务| GW
    W3 -->|注册/心跳/任务| GW
    W4 -->|注册/心跳/任务| GW
    W5 -->|注册/心跳/任务| GW
    S1 -->|注册/心跳| GW
    S2 -->|注册/心跳| GW
    S3 -->|注册/心跳| GW
    S4 -->|注册/心跳| GW
    S5 -->|注册/心跳| GW
    S6 -->|注册/心跳| GW
    S7 -->|注册/心跳| GW
    S8 -->|注册/心跳| GW
    S9 -->|注册/心跳| GW
    S10 -->|注册/心跳| GW

    GW --> H
    H --> VCE
    H --> CFG
    H -->|事件总线| W1
    H -->|任务下发| W2

    style 中枢主窗口 fill:#fff3e0,stroke:#ff9800,stroke-width:3px
    style 专业窗口边缘节点 fill:#e8f5e9,stroke:#4caf50
    style 业务服务节点 fill:#e8f4fd,stroke:#2196f3
```

---

## 架构说明

### 设计原则

1. **业务先行,中台后建**: 从业务中提炼公共能力,不先建中台再做业务
2. **能力沉淀,复用解耦**: 重复逻辑下沉中台,前台只做差异化
3. **统一治理,可观测可演化**: 全链路追踪+版本管控+变更评审
4. **单一数据源**: 禁止多副本,保证全局数据一致
5. **领域边界清晰**: 严格评审,业务特有逻辑不下沉中台,防止中台臃肿

### 当前已落地

- ✅ 技术中台: AI能力网关/配置中心/统一接入网关
- ✅ 业务中台: 角色元规则库/全域锁档归档/短剧流水线编排
- ✅ 治理体系: API网关/版本管控/权限审计
- ✅ 星型协同: 中枢调度器+11服务注册+同源协议全链路
- ⏳ 待建设: 数据中台/SSO/文件素材中心/可观测体系

Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS中台架构拓扑 | 五层架构 | 5张拓扑图 | DID-BR-000002