"""三类接入适配器 —— 方案 §四 路径1-3 / Step2 选型

- ApiAdapter  业务 OpenAPI 拉取(低侵入, 推荐)
- CdcAdapter  CDC(Kafka/RabbitMQ)事件推送
- FileAdapter 文件/报表批量导入(离线 → 默认 stale 标签, 短 TTL)

隔离要求(Step2): 生产库只给只读账号; 适配器禁止使用写账号连接业务主库。
同一系统只保留一种主链路, 避免重复消费。
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """适配器统一输出: 业务记录(含业务主键/厂区/实体类型), 由 gateway 编排。"""

    name: str = "base"
    is_real_time: bool = True          # 离线适配器覆盖为 False

    @abstractmethod
    def fetch(self) -> list[dict]:
        """拉取一批业务记录; 每条至少含:
        {"entity_type", "business_key", "site_code", "source_system", "fields": {...}}
        """

    # 只读护栏(元公理): 适配器只读不写
    def write_back(self, *args, **kwargs):
        raise NotImplementedError(
            f"{self.name}: 适配器只读, 写回业务系统必须走独立审批工单流(方案 §五.1)")


class ApiAdapter(BaseAdapter):
    """路径1: 标准化业务 OpenAPI → 鉴权、结果转实体(Step2 定时轮询)。"""

    name = "api"
    is_real_time = True

    def __init__(self, endpoint: str, auth: dict | None = None,
                 entity_type: str = "work_order", source_system: str = "MES"):
        self.endpoint = endpoint
        self.auth = auth or {}
        self.entity_type = entity_type
        self.source_system = source_system
        self._stub_records: list[dict] = []      # 骨架: 生产替换为 HTTP 调用

    def fetch(self) -> list[dict]:
        # 骨架: 生产实现 = GET self.endpoint + 鉴权 → 结果转实体
        return list(self._stub_records)

    def inject_for_test(self, records: list[dict]) -> None:
        """仅自测注入(Step6 坏例构造), 生产不启用。"""
        self._stub_records.extend(records)


class CdcAdapter(BaseAdapter):
    """路径2: Debezium/Canal binlog → 消息队列 → 消费更新 EID 快照(实时)。"""

    name = "cdc"
    is_real_time = True

    def __init__(self, topic: str, entity_type: str = "equipment",
                 source_system: str = "MES"):
        self.topic = topic
        self.entity_type = entity_type
        self.source_system = source_system
        self._queue: list[dict] = []

    def fetch(self) -> list[dict]:
        # 骨架: 生产实现 = 消费 Kafka/RabbitMQ topic
        batch, self._queue = self._queue, []
        return batch

    def push_event(self, record: dict) -> None:
        """事件推送入口(工单开工/报警/质检结果 → RefSet 变更)。"""
        self._queue.append(record)


class FileAdapter(BaseAdapter):
    """路径3: 监听目录/飞书企业微信文件推送 → 解析清洗 → 批量注册(离线)。"""

    name = "file"
    is_real_time = False               # 离线快照默认打 stale 标签(方案 §四 路径3)

    def __init__(self, watch_dir: str, entity_type: str = "inventory",
                 source_system: str = "WMS"):
        self.watch_dir = watch_dir
        self.entity_type = entity_type
        self.source_system = source_system
        self._files: list[dict] = []

    def fetch(self) -> list[dict]:
        # 骨架: 生产实现 = 监听 CSV/Excel → 解析清洗为业务记录
        batch, self._files = self._files, []
        return batch

    def upload_for_test(self, records: list[dict]) -> None:
        self._files.extend(records)
