# ZONGYUAN-ROOT API 文档

> 自动生成时间: 2026-08-30T07:11:24.277538
> 模块数: 12

---

## 目录

1. [守护进程管理器](#守护进程管理器)
2. [自进化循环](#自进化循环)
3. [横向扩展引擎](#横向扩展引擎)
4. [负载均衡器](#负载均衡器)
5. [Function Call层](#Function-Call层)
6. [RAG引擎](#RAG引擎)
7. [Merkle树](#Merkle树)
8. [备份管理器](#备份管理器)
9. [配额监控](#配额监控)
10. [资产聚合](#资产聚合)
11. [图像暗印](#图像暗印)
12. [配置中心](#配置中心)

---

## 守护进程管理器

M3-1: Ω-Brainμ 内核守护进程管理器
支持 start/stop/status/restart，7×24运行，自动重启，PID管理
容器环境通用方案：nohup + PID文件 + 健康检查

### 类

#### Path
PurePath subclass that can make system calls.

    Path represents a filesystem path but unlike PurePath, also offers
    methods to do system calls on path objects. Depending on your system,
    inst
方法: absolute, as_posix, as_uri, chmod, exists, expanduser, glob, group, hardlink_to, is_absolute

#### datetime
datetime(year, month, day[, hour[, minute[, second[, microsecond[,tzinfo]]]]])

The year, month and day arguments are required. tzinfo may be None, or an
instance of a tzinfo subclass. The remaining a

### 函数

#### `daemon_loop()`
守护循环：监控服务状态，异常自动重启（供nohup后台运行）

#### `get_pid()`

#### `is_healthy()`
健康检查：尝试连接服务端口

#### `log(msg)`

#### `restart()`
重启

#### `start()`
启动守护进程

#### `status()`
查看状态

#### `stop()`
停止守护进程

---

## 自进化循环

M3-2: 事件驱动自进化循环（内常驻）
监听三类事件：定时触发、文件变更、手动指令
自动执行：真值提炼→架构推演→内核写入→全域锁档→监测校验→归档输出→横向扩展（7阶段）

### 类

#### Empty
Exception raised by Queue.get(block=0)/get_nowait().

#### EvolutionLoop
事件驱动自进化循环
方法: check_file_changes, emit_event, event_processor, execute_evolution_cycle, file_watcher_thread, process_event, scheduler_thread, start, stop, trigger_manual_cycle

#### Path
PurePath subclass that can make system calls.

    Path represents a filesystem path but unlike PurePath, also offers
    methods to do system calls on path objects. Depending on your system,
    inst
方法: absolute, as_posix, as_uri, chmod, exists, expanduser, glob, group, hardlink_to, is_absolute

#### Queue
Create a queue object with a given maximum size.

    If maxsize is <= 0, the queue size is infinite.
方法: empty, full, get, get_nowait, join, put, put_nowait, qsize, task_done

#### datetime
datetime(year, month, day[, hour[, minute[, second[, microsecond[,tzinfo]]]]])

The year, month and day arguments are required. tzinfo may be None, or an
instance of a tzinfo subclass. The remaining a

#### timedelta
Difference between two datetime values.

timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)

All arguments are optional and default to 0.
Arguments may be intege

---

## 横向扩展引擎

横向功能最大化扩展执行器（真实执行版）
纳入Ω-Brainμ自治内核，合并到定时进化任务
七维扩展：工具×场景×生态×行业×输出×角色×商业
修复：伪执行→真实执行，系数计算bug，状态区分已完成/规划中

### 类

#### HorizontalExpansionEngine
横向功能扩展执行引擎（真实执行版）
方法: execute_daily_expansion, get_expansion_status, get_today_tasks

#### Path
PurePath subclass that can make system calls.

    Path represents a filesystem path but unlike PurePath, also offers
    methods to do system calls on path objects. Depending on your system,
    inst
方法: absolute, as_posix, as_uri, chmod, exists, expanduser, glob, group, hardlink_to, is_absolute

#### datetime
datetime(year, month, day[, hour[, minute[, second[, microsecond[,tzinfo]]]]])

The year, month and day arguments are required. tzinfo may be None, or an
instance of a tzinfo subclass. The remaining a

---

## 负载均衡器

M3-5: 多实例部署+负载均衡器
支持多Ω-Brainμ实例管理、健康检查、轮询/加权路由、故障自动切换

### 类

#### Instance
Ω-Brainμ 实例
方法: to_dict

#### LoadBalancer
负载均衡器
方法: add_instance, check_health, get_healthy_instances, get_status, health_check_all, health_check_loop, remove_instance, round_robin, route_request, start

#### Path
PurePath subclass that can make system calls.

    Path represents a filesystem path but unlike PurePath, also offers
    methods to do system calls on path objects. Depending on your system,
    inst
方法: absolute, as_posix, as_uri, chmod, exists, expanduser, glob, group, hardlink_to, is_absolute

#### datetime
datetime(year, month, day[, hour[, minute[, second[, microsecond[,tzinfo]]]]])

The year, month and day arguments are required. tzinfo may be None, or an
instance of a tzinfo subclass. The remaining a

---

## Function Call层

P1-4: Function Call 接入层
将8个工具接入豆包模型的Function Call机制，实现工具自动调用闭环

### 类

#### Path
PurePath subclass that can make system calls.

    Path represents a filesystem path but unlike PurePath, also offers
    methods to do system calls on path objects. Depending on your system,
    inst
方法: absolute, as_posix, as_uri, chmod, exists, expanduser, glob, group, hardlink_to, is_absolute

### 函数

#### `create_backup() -> dict`

#### `execute_evolution_cycle(trigger: str = 'function_call') -> dict`

#### `execute_function(name: str, arguments: dict) -> dict`
执行指定工具函数

#### `get_asset_status(domain: str = None) -> dict`

#### `get_function_definitions() -> List[dict]`
获取OpenAI格式的function definitions

#### `get_quota_status() -> dict`

#### `get_tools_schema() -> List[dict]`
获取所有工具的Function Call Schema（供模型调用）

#### `handle_model_response(response: dict) -> dict`
处理模型返回的function_call，自动执行并返回结果
    模型响应格式: {"function_call": {"name": "...", "arguments": "{...}"}}

#### `horizontal_expansion(phase: str = 'auto') -> dict`

#### `lock_asset(path: str) -> dict`

#### `query_truth_base(keyword: str) -> dict`

#### `register_tool(name: str, description: str, parameters: dict)`
装饰器：注册工具到Function Call

#### `system_health_check() -> dict`

---

## RAG引擎

M3-3: 豆包知识库RAG接入模块
支持知识库创建、文档上传、语义检索，与Ω-Brainμ真值基座联动
配置API Key后可直接使用，未配置时使用本地向量库降级

### 类

#### Path
PurePath subclass that can make system calls.

    Path represents a filesystem path but unlike PurePath, also offers
    methods to do system calls on path objects. Depending on your system,
    inst
方法: absolute, as_posix, as_uri, chmod, exists, expanduser, glob, group, hardlink_to, is_absolute

#### RAGEngine
豆包知识库RAG引擎
方法: configure, get_status, index_truth_base, search, upload_document

---

## Merkle树

P2-2: 标准Merkle树实现
支持SPV验证、Merkle证明、根哈希计算

### 类

#### MerkleTree
标准Merkle树（二叉）
方法: get_proof, to_dict, verify_proof

### 函数

#### `build_merkle_from_files(directory: str) -> scripts.merkle_tree.MerkleTree`
从目录文件构建Merkle树

---

## 备份管理器

P1-8: 备份与灾难恢复脚本
定期备份ZONGYUAN-ROOT到本地备份目录，支持恢复

### 类

#### Path
PurePath subclass that can make system calls.

    Path represents a filesystem path but unlike PurePath, also offers
    methods to do system calls on path objects. Depending on your system,
    inst
方法: absolute, as_posix, as_uri, chmod, exists, expanduser, glob, group, hardlink_to, is_absolute

#### datetime
datetime(year, month, day[, hour[, minute[, second[, microsecond[,tzinfo]]]]])

The year, month and day arguments are required. tzinfo may be None, or an
instance of a tzinfo subclass. The remaining a

### 函数

#### `create_backup() -> dict`
创建全量备份

#### `list_backups() -> list`
列出所有备份

#### `restore_backup(backup_id: str) -> dict`
从备份恢复

---

## 配额监控

P1-9: 配额监控增强版
真实追踪API调用配额，自动降级

### 类

#### Path
PurePath subclass that can make system calls.

    Path represents a filesystem path but unlike PurePath, also offers
    methods to do system calls on path objects. Depending on your system,
    inst
方法: absolute, as_posix, as_uri, chmod, exists, expanduser, glob, group, hardlink_to, is_absolute

#### datetime
datetime(year, month, day[, hour[, minute[, second[, microsecond[,tzinfo]]]]])

The year, month and day arguments are required. tzinfo may be None, or an
instance of a tzinfo subclass. The remaining a

#### timedelta
Difference between two datetime values.

timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)

All arguments are optional and default to 0.
Arguments may be intege

### 函数

#### `get_status() -> dict`
获取配额状态

#### `get_weekly_usage() -> list`
获取近7天使用量

#### `record_api_call(api_name: str, tokens_used: int = 0, cost: float = 0)`
记录一次API调用

---

## 资产聚合

P1-10: 资产健康度聚合分析脚本
真实调用Base data-query，生成聚合报告

### 类

#### Path
PurePath subclass that can make system calls.

    Path represents a filesystem path but unlike PurePath, also offers
    methods to do system calls on path objects. Depending on your system,
    inst
方法: absolute, as_posix, as_uri, chmod, exists, expanduser, glob, group, hardlink_to, is_absolute

#### datetime
datetime(year, month, day[, hour[, minute[, second[, microsecond[,tzinfo]]]]])

The year, month and day arguments are required. tzinfo may be None, or an
instance of a tzinfo subclass. The remaining a

#### timedelta
Difference between two datetime values.

timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)

All arguments are optional and default to 0.
Arguments may be intege

### 函数

#### `aggregate_by_domain() -> dict`
维度一：按体系域分组统计

#### `aggregate_by_type() -> dict`
维度二：按资产类型分组统计

#### `aggregate_lock_status() -> dict`
维度三：按锁档状态统计

#### `aggregate_quality() -> dict`
维度四：质量评分统计

#### `aggregate_trend() -> dict`
维度五：创建时间趋势

#### `generate_full_report() -> dict`
生成完整聚合分析报告

#### `run_lark_cli(args: list) -> dict`
执行lark-cli命令

---

## 图像暗印

P1-11: 视觉资产暗印镌刻工具
在图像右下角隐秘镌刻溯源符号 Ω₀⊂⊙∞⊂Ω

### 类

#### Path
PurePath subclass that can make system calls.

    Path represents a filesystem path but unlike PurePath, also offers
    methods to do system calls on path objects. Depending on your system,
    inst
方法: absolute, as_posix, as_uri, chmod, exists, expanduser, glob, group, hardlink_to, is_absolute

### 函数

#### `batch_watermark(directory: str) -> list`
批量处理目录下所有图片

#### `embed_watermark(image_path: str, output_path: str = None, opacity: int = 40) -> dict`
在图像右下角镌刻溯源暗印
    opacity: 透明度(0-255)，默认40（隐秘但可验证）

#### `verify_watermark(image_path: str) -> dict`
验证图像是否包含暗印（简化版：检查文件元数据）

---

## 配置中心

P2-6: 统一配置中心
集中管理所有配置，消除硬编码

### 类

#### ConfigCenter
统一配置中心
方法: get, get_all, save, set

#### Path
PurePath subclass that can make system calls.

    Path represents a filesystem path but unlike PurePath, also offers
    methods to do system calls on path objects. Depending on your system,
    inst
方法: absolute, as_posix, as_uri, chmod, exists, expanduser, glob, group, hardlink_to, is_absolute

### 函数

#### `get_config() -> config.config_center.ConfigCenter`

---

