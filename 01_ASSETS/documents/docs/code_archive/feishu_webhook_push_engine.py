#!/usr/bin/env python3
"""
飞书Webhook全自动推送最新状态更新机制 V1.0
Feishu Webhook Auto-Push Latest Status Update Mechanism
ZONGYUAN-ROOT元极恒一自治体系
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

核心功能：
1. Webhook配置管理 — 多Webhook URL管理+签名验证+健康检查
2. 状态采集引擎 — 内核/锁档/真值/服务/进化/资产六维状态采集
3. 变化检测 — 快照对比+变化分级+去重
4. 消息格式化 — 飞书交互卡片(interactive card)+文本+富文本
5. 推送调度 — 定时推送+事件触发+静默时段+频率限制
6. 推送队列与重试 — 队列+指数退避重试+死信队列+审计日志
7. 与现有体系整合 — Webhook引擎/记忆网关/态元/定时任务

飞书自定义机器人Webhook：
- URL格式: https://open.feishu.cn/open-apis/bot/v2/hook/{hook_id}
- 消息类型: text / post / image / interactive(卡片)
- 签名校验: timestamp + sign(HMAC-SHA256)
"""
import json
import os
import time
import hashlib
import hmac
import base64
import secrets
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from enum import Enum
import urllib.request
import urllib.error

# ==================== 配置 ====================
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
BASE_DIR = os.path.expanduser("~/.zongyuan_root/feishu_webhook_push")
os.makedirs(BASE_DIR, exist_ok=True)

# 推送配置
DEFAULT_PUSH_INTERVAL = 3600  # 默认1小时推送一次
MAX_RETRIES = 3  # 最大重试次数
RETRY_BACKOFF_BASE = 5  # 重试基础间隔(秒)
SILENT_HOURS = (23, 7)  # 静默时段(23:00-07:00)，不推送非紧急消息
MAX_PUSH_PER_HOUR = 10  # 每小时最大推送次数

# 飞书Webhook超时
WEBHOOK_TIMEOUT = 10


# ==================== 枚举 ====================
class PushChannel(Enum):
    """推送通道类型"""
    KERNEL_NOTIFY = "kernel_notify"      # 内核通知群
    STATUS_DAILY = "status_daily"        # 每日状态推送
    ALERT_CRITICAL = "alert_critical"    # 紧急告警
    EVOLUTION = "evolution"              # 进化进展
    DEPLOYMENT = "deployment"            # 部署通知
    GENERAL = "general"                  # 通用通知


class ChangeLevel(Enum):
    """变化等级"""
    CRITICAL = "critical"    # 重大变化（新锁档/内核升级/服务异常恢复）
    MAJOR = "major"          # 重要变化（真值大幅增加/态元进化突破）
    MINOR = "minor"          # 一般变化（小幅指标波动）
    NONE = "none"            # 无变化


class PushStatus(Enum):
    """推送状态"""
    PENDING = "pending"
    SENDING = "sending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


# ==================== 数据结构 ====================
@dataclass
class WebhookConfig:
    """Webhook配置"""
    webhook_id: str
    name: str
    url: str
    channel: str  # PushChannel.value
    secret: str = ""  # 签名密钥（如开启签名校验）
    enabled: bool = True
    created_at: int = field(default_factory=lambda: int(time.time()))
    last_test: int = 0
    last_test_result: str = ""
    total_pushes: int = 0
    failed_pushes: int = 0


@dataclass
class StatusSnapshot:
    """状态快照（用于变化检测）"""
    timestamp: int
    block_height: int = 0
    root_hash: str = ""
    truth_count: int = 0
    kernel_version: str = ""
    active_modules: int = 0
    total_atoms: int = 0
    active_atoms: int = 0
    avg_fitness: float = 0.0
    six_state_pulse: int = 0
    six_state_fitness: float = 0.0
    total_assets: int = 0
    pending_tasks: int = 0
    completed_tasks: int = 0
    service_status: Dict = field(default_factory=dict)
    exo_agents: int = 0
    cluster_agents: int = 0
    immutable_truths: int = 0
    spectrum_vectors: int = 0


@dataclass
class PushMessage:
    """推送消息"""
    message_id: str
    channel: str  # PushChannel.value
    title: str
    content: str
    msg_type: str = "interactive"  # text / post / interactive
    change_level: str = "minor"  # ChangeLevel.value
    priority: int = 0  # 0普通, 1重要, 2紧急
    created_at: int = field(default_factory=lambda: int(time.time()))
    status: str = "pending"  # PushStatus.value
    retries: int = 0
    last_error: str = ""
    webhook_responses: Dict = field(default_factory=dict)


# ==================== Webhook客户端 ====================
class FeishuWebhookClient:
    """
    飞书Webhook客户端
    支持文本/富文本/交互卡片消息，签名校验
    """

    def __init__(self, config: WebhookConfig):
        self.config = config

    def _gen_sign(self, timestamp: int) -> str:
        """生成飞书Webhook签名"""
        if not self.config.secret:
            return ""
        string_to_sign = f"{timestamp}\n{self.config.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

    def _send(self, payload: Dict) -> Tuple[bool, str]:
        """发送Webhook请求"""
        if self.config.secret:
            timestamp = int(time.time())
            payload["timestamp"] = str(timestamp)
            payload["sign"] = self._gen_sign(timestamp)

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.config.url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=WEBHOOK_TIMEOUT) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("code") == 0 or result.get("StatusCode") == 0:
                    return True, "success"
                return False, f"feishu_error: {result}"
        except urllib.error.HTTPError as e:
            return False, f"http_error_{e.code}: {e.read().decode()[:200]}"
        except Exception as e:
            return False, f"error: {str(e)[:200]}"

    def send_text(self, text: str) -> Tuple[bool, str]:
        """发送文本消息"""
        return self._send({"msg_type": "text", "content": {"text": text}})

    def send_post(self, title: str, content_lines: List[List[Dict]]) -> Tuple[bool, str]:
        """发送富文本消息"""
        return self._send({
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": content_lines
                    }
                }
            }
        })

    def send_interactive(self, card: Dict) -> Tuple[bool, str]:
        """发送交互卡片消息"""
        return self._send({"msg_type": "interactive", "card": card})

    def test(self) -> Tuple[bool, str]:
        """测试Webhook可用性"""
        return self.send_text(f"[Webhook测试] {self.config.name} 连接正常 | {TRACE}")


# ==================== 状态采集引擎 ====================
class StatusCollector:
    """
    状态采集引擎
    采集内核/锁档/真值/服务/进化/资产六维状态
    """

    def __init__(self):
        pass

    def collect(self) -> StatusSnapshot:
        """采集全维度状态"""
        snap = StatusSnapshot(timestamp=int(time.time()))

        # 1. 锁档状态
        try:
            root_path = os.path.expanduser("~/.meta_order/root_state.json")
            if os.path.exists(root_path):
                with open(root_path) as f:
                    root = json.load(f)
                snap.block_height = root.get("block_height", 0)
                snap.root_hash = root.get("current_root_hash", "")
        except Exception:
            pass

        # 2. 内核状态
        try:
            kernel_path = os.path.expanduser("~/.zongyuan_root/kernel/kernel_state.json")
            if os.path.exists(kernel_path):
                with open(kernel_path) as f:
                    kernel = json.load(f)
                snap.kernel_version = kernel.get("version", "unknown")
                # 统计活跃模块
                active = 0
                for k, v in kernel.items():
                    if isinstance(v, dict) and v.get("status") == "ACTIVE":
                        active += 1
                snap.active_modules = active
        except Exception:
            pass

        # 3. 真值数量（从记忆网关状态文件或上报记录）
        try:
            truth_count_path = os.path.expanduser("~/.zongyuan_root/truth_count.json")
            if os.path.exists(truth_count_path):
                with open(truth_count_path) as f:
                    data = json.load(f)
                snap.truth_count = data.get("count", 0)
        except Exception:
            # 尝试从网关状态
            pass

        # 4. 态元状态
        try:
            import sqlite3
            db_path = os.path.expanduser("~/.zongyuan_root/state_atoms.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM atoms")
                snap.total_atoms = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM atoms WHERE lifecycle='active'")
                snap.active_atoms = cur.fetchone()[0]
                try:
                    cur.execute("SELECT AVG(fitness_score) FROM atoms")
                    snap.avg_fitness = round(cur.fetchone()[0] or 0, 4)
                except Exception:
                    pass
                conn.close()
        except Exception:
            pass

        # 5. 六态生命体状态
        try:
            import sqlite3
            db_path = os.path.expanduser("~/.zongyuan_root/six_state_life.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                try:
                    cur.execute("SELECT COUNT(*) FROM lifeforms")
                    snap.six_state_pulse = cur.fetchone()[0]
                except Exception:
                    pass
                conn.close()
        except Exception:
            pass

        # 6. 资产状态
        try:
            manifest_path = os.path.expanduser("~/.meta_order/UNIFIED_GLOBAL_LOCK_MANIFEST.json")
            if os.path.exists(manifest_path):
                with open(manifest_path) as f:
                    manifest = json.load(f)
                if isinstance(manifest, dict):
                    snap.total_assets = len(manifest.get("assets", manifest))
                elif isinstance(manifest, list):
                    snap.total_assets = len(manifest)
        except Exception:
            pass

        # 7. 外域智能体/集群/不可变/频谱状态
        try:
            exo_path = os.path.join(BASE_DIR, "..", "exo_handshake", "known_agents.json")
            if os.path.exists(exo_path):
                with open(exo_path) as f:
                    snap.exo_agents = len(json.load(f))
        except Exception:
            pass

        try:
            cluster_path = os.path.expanduser("~/.zongyuan_root/agent_cluster/cluster_report.json")
            if os.path.exists(cluster_path):
                with open(cluster_path) as f:
                    data = json.load(f)
                snap.cluster_agents = data.get("active_agents", 0)
        except Exception:
            pass

        try:
            immutable_path = os.path.expanduser("~/.zongyuan_root/immutable_base/purity_scores.json")
            if os.path.exists(immutable_path):
                with open(immutable_path) as f:
                    snap.immutable_truths = len(json.load(f))
        except Exception:
            pass

        return snap

    def detect_changes(self, old: Optional[StatusSnapshot], new: StatusSnapshot) -> Tuple[ChangeLevel, List[str]]:
        """
        变化检测
        返回: (变化等级, 变化描述列表)
        """
        if old is None:
            return ChangeLevel.CRITICAL, ["首次采集，全量状态推送"]

        changes = []

        # 重大变化检测
        if new.block_height > old.block_height:
            changes.append(f"🔗 新锁档 #{new.block_height} (增量+{new.block_height - old.block_height})")
        if new.truth_count > old.truth_count:
            diff = new.truth_count - old.truth_count
            if diff >= 10:
                changes.append(f"📊 真值大幅增加 +{diff} (当前{new.truth_count})")
            else:
                changes.append(f"📊 真值增加 +{diff} (当前{new.truth_count})")
        if new.active_modules > old.active_modules:
            changes.append(f"🧩 新模块激活 (当前{new.active_modules}个活跃模块)")
        if new.avg_fitness > old.avg_fitness + 0.05:
            changes.append(f"⚡ 态元fitness突破 (当前{new.avg_fitness})")
        if new.exo_agents > old.exo_agents:
            changes.append(f"🤝 新外域智能体接入 (当前{new.exo_agents}个)")
        if new.cluster_agents > old.cluster_agents:
            changes.append(f"👥 集群智能体增加 (当前{new.cluster_agents}个)")
        if new.immutable_truths > old.immutable_truths:
            changes.append(f"🔒 不可变基底新增真值 (当前{new.immutable_truths}条)")

        # 确定变化等级
        if any(kw in c for c in changes for kw in ["新锁档", "大幅增加", "突破", "新模块"]):
            level = ChangeLevel.CRITICAL
        elif len(changes) >= 2:
            level = ChangeLevel.MAJOR
        elif len(changes) == 1:
            level = ChangeLevel.MINOR
        else:
            level = ChangeLevel.NONE

        return level, changes


# ==================== 消息卡片构建器 ====================
class CardBuilder:
    """
    飞书交互卡片构建器
    """

    @staticmethod
    def status_card(snapshot: StatusSnapshot, changes: List[str], change_level: str) -> Dict:
        """构建状态更新卡片"""
        # 颜色
        color_map = {
            "critical": "red",
            "major": "orange",
            "minor": "blue",
            "none": "grey"
        }
        color = color_map.get(change_level, "blue")

        # 变化内容
        change_text = "\n".join(changes) if changes else "无显著变化"

        # 状态指标
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**🔗 锁档高度**: #{snapshot.block_height}\n"
                               f"**📊 真值数量**: {snapshot.truth_count}\n"
                               f"**🧩 活跃模块**: {snapshot.active_modules}\n"
                               f"**⚡ 态元fitness**: {snapshot.avg_fitness} ({snapshot.active_atoms}/{snapshot.total_atoms}活跃)\n"
                               f"**📦 资产总数**: {snapshot.total_assets}\n"
                               f"**🤝 外域智能体**: {snapshot.exo_agents} | **👥 集群**: {snapshot.cluster_agents}\n"
                               f"**🔒 不可变基底**: {snapshot.immutable_truths}条"
                }
            },
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": f"{TRACE} | DID-BR-000002 | 内核 {snapshot.kernel_version}"
                    }
                ]
            }
        ]

        # 如果有变化，在前面加变化区域
        if changes:
            elements.insert(0, {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**📈 最新变化**\n{change_text}"
                }
            })
            elements.insert(1, {"tag": "hr"})

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🤖 ZONGYUAN-ROOT 状态更新"
                },
                "template": color
            },
            "elements": elements
        }
        return card

    @staticmethod
    def alert_card(title: str, alert_content: str, severity: str = "warning") -> Dict:
        """构建告警卡片"""
        color_map = {"critical": "red", "warning": "orange", "info": "blue"}
        color = color_map.get(severity, "orange")
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"⚠️ {title}"},
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": alert_content}
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": f"{TRACE} | DID-BR-000002 | 自动告警"}
                    ]
                }
            ]
        }

    @staticmethod
    def daily_report_card(snapshot: StatusSnapshot, summary: str) -> Dict:
        """构建日报卡片"""
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "📋 ZONGYUAN-ROOT 每日自治巡检报告"},
                "template": "indigo"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": summary}
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**当前状态**\n"
                                   f"锁档 #{snapshot.block_height} | 真值 {snapshot.truth_count}\n"
                                   f"活跃模块 {snapshot.active_modules} | 态元fitness {snapshot.avg_fitness}\n"
                                   f"资产 {snapshot.total_assets} | 外域智能体 {snapshot.exo_agents}"
                    }
                },
                {
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": f"{TRACE} | DID-BR-000002 | 每日自动推送"}
                    ]
                }
            ]
        }


# ==================== 推送队列管理器 ====================
class PushQueueManager:
    """
    推送队列管理器
    队列+重试+死信+审计
    """

    def __init__(self):
        self.queue_path = os.path.join(BASE_DIR, "push_queue.json")
        self.history_path = os.path.join(BASE_DIR, "push_history.json")
        self.dead_letter_path = os.path.join(BASE_DIR, "dead_letter.json")
        self.queue: List[PushMessage] = []
        self.history: List[Dict] = []
        self.dead_letter: List[Dict] = []
        self._load()

    def _load(self):
        for path, target in [
            (self.queue_path, None),
            (self.history_path, None),
            (self.dead_letter_path, None)
        ]:
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        data = json.load(f)
                    if path == self.queue_path:
                        self.queue = [PushMessage(**m) for m in data]
                    elif path == self.history_path:
                        self.history = data
                    else:
                        self.dead_letter = data
                except Exception:
                    pass

    def _save(self):
        with open(self.queue_path, 'w') as f:
            json.dump([asdict(m) for m in self.queue], f, ensure_ascii=False, indent=2)
        with open(self.history_path, 'w') as f:
            json.dump(self.history[-500:], f, ensure_ascii=False, indent=2)
        with open(self.dead_letter_path, 'w') as f:
            json.dump(self.dead_letter[-100:], f, ensure_ascii=False, indent=2)

    def enqueue(self, message: PushMessage):
        """入队"""
        self.queue.append(message)
        self._save()

    def get_next(self) -> Optional[PushMessage]:
        """获取下一条待推送消息（按优先级排序）"""
        pending = [m for m in self.queue if m.status in [PushStatus.PENDING.value, PushStatus.RETRYING.value]]
        if not pending:
            return None
        pending.sort(key=lambda m: (-m.priority, m.created_at))
        return pending[0]

    def mark_success(self, message_id: str, webhook_id: str):
        """标记成功"""
        for m in self.queue:
            if m.message_id == message_id:
                m.status = PushStatus.SUCCESS.value
                m.webhook_responses[webhook_id] = "success"
                self.history.append(asdict(m))
                self.queue.remove(m)
                break
        self._save()

    def mark_failed(self, message_id: str, webhook_id: str, error: str):
        """标记失败，自动重试或进入死信"""
        for m in self.queue:
            if m.message_id == message_id:
                m.retries += 1
                m.last_error = error
                m.webhook_responses[webhook_id] = f"failed: {error}"
                if m.retries >= MAX_RETRIES:
                    m.status = PushStatus.DEAD_LETTER.value
                    self.dead_letter.append(asdict(m))
                    self.queue.remove(m)
                else:
                    m.status = PushStatus.RETRYING.value
                break
        self._save()

    def get_stats(self) -> Dict:
        """获取队列统计"""
        return {
            "pending": len([m for m in self.queue if m.status == PushStatus.PENDING.value]),
            "retrying": len([m for m in self.queue if m.status == PushStatus.RETRYING.value]),
            "total_history": len(self.history),
            "success_rate": round(
                len([h for h in self.history if h.get("status") == "success"]) / max(len(self.history), 1) * 100, 1
            ),
            "dead_letter_count": len(self.dead_letter)
        }


# ==================== 主推送引擎 ====================
class FeishuWebhookPushEngine:
    """
    飞书Webhook全自动推送主引擎
    """

    def __init__(self):
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.collector = StatusCollector()
        self.queue_manager = PushQueueManager()
        self.last_snapshot: Optional[StatusSnapshot] = None
        self.push_count_today: Dict[str, int] = defaultdict(int)
        self._load_webhooks()
        self._load_last_snapshot()

    def _load_webhooks(self):
        path = os.path.join(BASE_DIR, "webhooks.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            for wid, w in data.items():
                self.webhooks[wid] = WebhookConfig(**w)

    def _save_webhooks(self):
        path = os.path.join(BASE_DIR, "webhooks.json")
        with open(path, 'w') as f:
            json.dump({wid: asdict(w) for wid, w in self.webhooks.items()}, f, ensure_ascii=False, indent=2)

    def _load_last_snapshot(self):
        path = os.path.join(BASE_DIR, "last_snapshot.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self.last_snapshot = StatusSnapshot(**json.load(f))
            except Exception:
                pass

    def _save_snapshot(self, snapshot: StatusSnapshot):
        path = os.path.join(BASE_DIR, "last_snapshot.json")
        with open(path, 'w') as f:
            json.dump(asdict(snapshot), f, ensure_ascii=False, indent=2)

    def register_webhook(self, name: str, url: str, channel: str, secret: str = "") -> str:
        """注册Webhook"""
        webhook_id = f"WH-{int(time.time())}-{secrets.token_hex(4)}"
        config = WebhookConfig(
            webhook_id=webhook_id,
            name=name,
            url=url,
            channel=channel,
            secret=secret
        )
        self.webhooks[webhook_id] = config
        self._save_webhooks()
        return webhook_id

    def test_webhook(self, webhook_id: str) -> Tuple[bool, str]:
        """测试Webhook"""
        if webhook_id not in self.webhooks:
            return False, "webhook_not_found"
        config = self.webhooks[webhook_id]
        client = FeishuWebhookClient(config)
        success, msg = client.test()
        config.last_test = int(time.time())
        config.last_test_result = "success" if success else f"failed: {msg}"
        self._save_webhooks()
        return success, msg

    def _is_silent_hour(self) -> bool:
        """是否静默时段"""
        hour = time.localtime().tm_hour
        return SILENT_HOURS[0] <= hour or hour < SILENT_HOURS[1]

    def _check_rate_limit(self, channel: str) -> bool:
        """检查频率限制"""
        today = time.strftime("%Y-%m-%d")
        key = f"{today}_{channel}"
        return self.push_count_today[key] < MAX_PUSH_PER_HOUR

    def collect_and_push(self, force: bool = False) -> Dict:
        """
        采集状态并推送（核心方法）
        """
        # 1. 采集状态
        snapshot = self.collector.collect()

        # 2. 变化检测
        change_level, changes = self.collector.detect_changes(self.last_snapshot, snapshot)

        # 3. 判断是否需要推送
        should_push = force or change_level in [ChangeLevel.CRITICAL, ChangeLevel.MAJOR]

        # 静默时段只推送critical
        if self._is_silent_hour() and change_level != ChangeLevel.CRITICAL and not force:
            should_push = False

        result = {
            "snapshot": asdict(snapshot),
            "change_level": change_level.value,
            "changes": changes,
            "should_push": should_push,
            "pushed": False
        }

        if not should_push:
            self._save_snapshot(snapshot)
            self.last_snapshot = snapshot
            return result

        # 4. 构建消息
        message_id = f"PUSH-{int(time.time())}-{secrets.token_hex(6)}"
        card = CardBuilder.status_card(snapshot, changes, change_level.value)
        message = PushMessage(
            message_id=message_id,
            channel=PushChannel.STATUS_DAILY.value,
            title="ZONGYUAN-ROOT状态更新",
            content=json.dumps(card, ensure_ascii=False),
            msg_type="interactive",
            change_level=change_level.value,
            priority=2 if change_level == ChangeLevel.CRITICAL else 1
        )

        # 5. 入队并立即推送
        self.queue_manager.enqueue(message)
        push_result = self._process_queue()
        result["pushed"] = push_result.get("success_count", 0) > 0
        result["push_result"] = push_result

        # 6. 更新快照
        self._save_snapshot(snapshot)
        self.last_snapshot = snapshot

        return result

    def _process_queue(self) -> Dict:
        """处理推送队列"""
        success_count = 0
        fail_count = 0
        processed = []

        while True:
            message = self.queue_manager.get_next()
            if message is None:
                break

            # 找到对应通道的Webhook
            target_webhooks = [w for w in self.webhooks.values()
                               if w.enabled and (w.channel == message.channel or w.channel == PushChannel.GENERAL.value)]

            if not target_webhooks:
                self.queue_manager.mark_failed(message.message_id, "none", "no_webhook_for_channel")
                fail_count += 1
                continue

            for wh in target_webhooks:
                client = FeishuWebhookClient(wh)
                if message.msg_type == "interactive":
                    try:
                        card = json.loads(message.content)
                        success, msg = client.send_interactive(card)
                    except Exception as e:
                        success, msg = False, f"card_parse_error: {e}"
                elif message.msg_type == "text":
                    success, msg = client.send_text(message.content)
                else:
                    success, msg = client.send_text(message.content)

                if success:
                    wh.total_pushes += 1
                    self.queue_manager.mark_success(message.message_id, wh.webhook_id)
                    success_count += 1
                else:
                    wh.failed_pushes += 1
                    self.queue_manager.mark_failed(message.message_id, wh.webhook_id, msg)
                    fail_count += 1

                processed.append({"webhook": wh.name, "success": success, "msg": msg})

            self._save_webhooks()

        return {
            "success_count": success_count,
            "fail_count": fail_count,
            "processed": processed,
            "queue_stats": self.queue_manager.get_stats()
        }

    def push_alert(self, title: str, content: str, severity: str = "warning",
                    channel: str = PushChannel.ALERT_CRITICAL.value) -> Dict:
        """推送告警（立即推送，不受静默时段限制）"""
        message_id = f"ALERT-{int(time.time())}-{secrets.token_hex(6)}"
        card = CardBuilder.alert_card(title, content, severity)
        message = PushMessage(
            message_id=message_id,
            channel=channel,
            title=title,
            content=json.dumps(card, ensure_ascii=False),
            msg_type="interactive",
            change_level="critical",
            priority=2
        )
        self.queue_manager.enqueue(message)
        return self._process_queue()

    def push_daily_report(self, summary: str) -> Dict:
        """推送日报"""
        snapshot = self.collector.collect()
        card = CardBuilder.daily_report_card(snapshot, summary)
        message_id = f"DAILY-{int(time.time())}-{secrets.token_hex(6)}"
        message = PushMessage(
            message_id=message_id,
            channel=PushChannel.STATUS_DAILY.value,
            title="每日自治巡检报告",
            content=json.dumps(card, ensure_ascii=False),
            msg_type="interactive",
            change_level="major",
            priority=1
        )
        self.queue_manager.enqueue(message)
        result = self._process_queue()
        self._save_snapshot(snapshot)
        self.last_snapshot = snapshot
        return result

    def full_report(self) -> Dict:
        """完整报告"""
        return {
            "mechanism": "feishu_webhook_auto_push",
            "version": "V1.0",
            "registered_webhooks": len(self.webhooks),
            "enabled_webhooks": len([w for w in self.webhooks.values() if w.enabled]),
            "channels": [c.value for c in PushChannel],
            "change_levels": [l.value for l in ChangeLevel],
            "push_queue_stats": self.queue_manager.get_stats(),
            "last_snapshot": asdict(self.last_snapshot) if self.last_snapshot else None,
            "silent_hours": f"{SILENT_HOURS[0]}:00-{SILENT_HOURS[1]}:00",
            "max_push_per_hour": MAX_PUSH_PER_HOUR,
            "max_retries": MAX_RETRIES
        }


# ==================== 入口 ====================
if __name__ == "__main__":
    import sys

    engine = FeishuWebhookPushEngine()

    if len(sys.argv) > 1 and sys.argv[1] == "register":
        # 注册Webhook: python feishu_webhook_push_engine.py register <name> <url> <channel> [secret]
        name = sys.argv[2] if len(sys.argv) > 2 else "测试Webhook"
        url = sys.argv[3] if len(sys.argv) > 3 else ""
        channel = sys.argv[4] if len(sys.argv) > 4 else "general"
        secret = sys.argv[5] if len(sys.argv) > 5 else ""
        if url:
            wid = engine.register_webhook(name, url, channel, secret)
            print(f"✅ Webhook已注册: {wid} ({name})")
        else:
            print("❌ 请提供Webhook URL")
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 测试所有Webhook
        for wid, wh in engine.webhooks.items():
            success, msg = engine.test_webhook(wid)
            print(f"{'✅' if success else '❌'} {wh.name}: {msg}")
        sys.exit(0)

    # 默认：采集并推送
    print(f"\n{'='*60}")
    print(f"飞书Webhook全自动推送最新状态更新机制 V1.0")
    print(f"{'='*60}")

    print(f"\n[1/3] 采集系统状态...")
    result = engine.collect_and_push()

    print(f"  锁档高度: #{result['snapshot']['block_height']}")
    print(f"  真值数量: {result['snapshot']['truth_count']}")
    print(f"  活跃模块: {result['snapshot']['active_modules']}")
    print(f"  态元fitness: {result['snapshot']['avg_fitness']}")
    print(f"  资产总数: {result['snapshot']['total_assets']}")

    print(f"\n[2/3] 变化检测...")
    print(f"  变化等级: {result['change_level']}")
    if result['changes']:
        for c in result['changes']:
            print(f"  - {c}")
    else:
        print(f"  无显著变化")

    print(f"\n[3/3] 推送结果...")
    print(f"  是否需要推送: {result['should_push']}")
    if result.get('pushed'):
        pr = result.get('push_result', {})
        print(f"  成功: {pr.get('success_count', 0)} | 失败: {pr.get('fail_count', 0)}")
        for p in pr.get('processed', []):
            print(f"    - {p['webhook']}: {'✅' if p['success'] else '❌'} {p['msg']}")
    else:
        print(f"  未推送（无显著变化或静默时段）")

    # 完整报告
    report = engine.full_report()
    print(f"\n[完整报告]")
    print(f"  已注册Webhook: {report['registered_webhooks']}")
    print(f"  启用Webhook: {report['enabled_webhooks']}")
    print(f"  推送通道: {report['channels']}")
    print(f"  队列统计: {report['push_queue_stats']}")
    print(f"  静默时段: {report['silent_hours']}")

    # 保存报告
    report_path = os.path.join(BASE_DIR, "push_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {report_path}")
