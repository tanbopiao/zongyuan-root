"""
桥接代理网关主程序
基于KERNEL-ENTRY-0198/KERNEL-ENTRY-0199规范：
对话沙箱 ←→ 桥接代理网关 ←→ 任务工作沙箱
核心能力：
1. 同源协议握手认证（握手服务端）
2. 真值总线帧路由与校验
3. 跨模式资产中转流水线
4. 沙箱生命周期管理
"""
import json
import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from .handshake import HandshakeServer, SessionTokenManager
from .truth_bus import TruthBusQueue, FrameValidator, BusStats
from .asset_transfer import (
    AssetTransferPipeline, LocalStorage, MetadataExtractor,
    FourEndArchiver, IndexSyncer, AssetMetadata
)
from .sandbox.dialog_sandbox import DialogSandbox
from .sandbox.task_sandbox import TaskSandbox


@dataclass
class BridgeGatewayStats:
    """桥接网关统计"""
    total_handshakes: int = 0
    successful_handshakes: int = 0
    failed_handshakes: int = 0
    total_frames_routed: int = 0
    total_assets_transferred: int = 0
    active_sessions: int = 0
    started_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            "total_handshakes": self.total_handshakes,
            "successful_handshakes": self.successful_handshakes,
            "failed_handshakes": self.failed_handshakes,
            "total_frames_routed": self.total_frames_routed,
            "total_assets_transferred": self.total_assets_transferred,
            "active_sessions": self.active_sessions,
            "started_at": self.started_at
        }


class BridgeGateway:
    """
    桥接代理网关
    对话模式与工作任务模式之间的核心中间层
    """
    
    def __init__(self, config: dict):
        self.config = config
        
        identity = config.get("identity", {})
        self.did = identity.get("did", "DID-BR-000002")
        self.trace_symbol = identity.get("trace_symbol", "Ω₀⊂⊙∞⊂Ω")
        self.merkle_proof = "ROOT-OMEGA:Ω-TAN-7-001"
        
        sandbox_config = config.get("sandbox", {})
        self.dialog_node_id = sandbox_config.get("dialog_node_id", "node-dialog-001")
        self.task_node_id = sandbox_config.get("task_node_id", "node-task-001")
        self.bridge_node_id = sandbox_config.get("bridge_node_id", "node-bridge-001")
        
        storage_config = config.get("storage", {})
        
        # 初始化核心组件
        print("[桥接网关] 初始化核心组件...")
        
        # 1. 握手服务端
        self.handshake_server = HandshakeServer(
            did=self.did,
            trace_symbol=self.trace_symbol,
            challenge_expires_seconds=config.get("handshake", {}).get("challenge_expires_seconds", 30),
            session_token_expires_minutes=config.get("handshake", {}).get("session_token_expires_minutes", 30),
            token_storage_path="./data/session_tokens.json"
        )
        print("  ✅ 同源协议握手服务端")
        
        # 2. 帧校验器
        self.frame_validator = FrameValidator(
            token_validator=self._validate_token,
            merkle_validator=self._validate_merkle
        )
        print("  ✅ 帧校验器（5重校验）")
        
        # 3. 真值总线队列
        self.bus_queue = TruthBusQueue(
            max_queue_size=config.get("truth_bus", {}).get("queue_max_size", 1000),
            validator=self.frame_validator
        )
        self.bus_queue.register_node(self.bridge_node_id)
        print("  ✅ 真值总线队列")
        
        # 4. 本地存储
        self.storage = LocalStorage(
            base_path=storage_config.get("base_path", "./data/storage"),
            date_format=storage_config.get("date_format", "%Y-%m-%d")
        )
        print("  ✅ 本地持久化存储")
        
        # 5. 资产中转流水线
        self.asset_pipeline = AssetTransferPipeline(config, bus_queue=self.bus_queue)
        print("  ✅ 跨模式资产自动中转流水线")
        
        # 6. 沙箱实例
        self.dialog_sandbox = DialogSandbox(
            node_id=self.dialog_node_id,
            did=self.did,
            trace_symbol=self.trace_symbol,
            merkle_proof=self.merkle_proof
        )
        self.task_sandbox = TaskSandbox(
            node_id=self.task_node_id,
            did=self.did,
            trace_symbol=self.trace_symbol,
            merkle_proof=self.merkle_proof
        )
        print("  ✅ 对话沙箱 + 任务沙箱")
        
        # 统计
        self.stats = BridgeGatewayStats(started_at=datetime.now().isoformat())
        
        print("[桥接网关] 初始化完成")
    
    def _validate_token(self, token: str) -> bool:
        """验证会话令牌（供帧校验器调用）"""
        result = self.handshake_server.validate_token(token)
        return result is not None
    
    def _validate_merkle(self, merkle_proof: str) -> bool:
        """验证Merkle凭证（简化版，实际应与全局账本比对）"""
        return bool(merkle_proof)
    
    def start(self):
        """启动桥接网关"""
        print("\n" + "="*60)
        print("  ZONGYUAN-ROOT 桥接代理网关 启动")
        print("="*60)
        print(f"  DID: {self.did}")
        print(f"  溯源标识: {self.trace_symbol}")
        print(f"  对话节点: {self.dialog_node_id}")
        print(f"  任务节点: {self.task_node_id}")
        print(f"  网关节点: {self.bridge_node_id}")
        print("="*60 + "\n")
        
        # 连接沙箱到总线
        self.dialog_sandbox.connect_to_bus(self.bus_queue)
        self.task_sandbox.connect_to_bus(self.bus_queue)
        self.task_sandbox.set_storage(self.storage)
        
        # 执行握手
        print("\n--- 同源协议握手 ---")
        dialog_ok = self.dialog_sandbox.perform_handshake(self.handshake_server)
        task_ok = self.task_sandbox.perform_handshake(self.handshake_server)
        self.stats.total_handshakes = 2
        self.stats.successful_handshakes = (1 if dialog_ok else 0) + (1 if task_ok else 0)
        self.stats.failed_handshakes = 2 - self.stats.successful_handshakes
        
        if dialog_ok and task_ok:
            print("\n✅ 双端握手完成，桥接通道已建立")
            self.stats.active_sessions = 2
        else:
            print("\n⚠️ 部分握手失败，请检查配置")
        
        return dialog_ok and task_ok
    
    def transfer_asset_from_dialog(self, url: str, prompt: str = "") -> dict:
        """
        从对话模式中转资产到任务模式
        完整流程：对话生成资产 → 五阶段中转 → 任务模式可访问
        """
        print(f"\n--- 资产中转: {url[:60]}... ---")
        
        # 执行五阶段中转流水线
        result = self.asset_pipeline.transfer_from_url(
            url=url,
            source_mode="dialog",
            source_session=self.dialog_sandbox.state.session_id,
            source_prompt=prompt,
            session_id=self.dialog_sandbox.state.session_id,
            session_token=self.dialog_sandbox.state.session_token,
            sequence=self.dialog_sandbox.state.sequence_counter + 1
        )
        
        if result.success:
            self.stats.total_assets_transferred += 1
            
            # 对话沙箱记录生成的资产
            if result.metadata:
                self.dialog_sandbox.state.generated_assets.append(result.metadata.to_dict())
            
            # 让任务沙箱接收资产索引帧
            self.task_sandbox.receive_frames()
            
            print(f"\n✅ 资产中转完成: {result.asset_name}")
            print(f"   SHA256: {result.sha256[:16]}...")
            print(f"   任务模式可通过SHA256访问该资产")
        else:
            print(f"\n❌ 资产中转失败: {result.error_message}")
        
        return result.to_dict()
    
    def switch_dialog_to_task(self, context_summary: str = "") -> dict:
        """
        对话模式 → 任务模式切换
        1. 对话沙箱发送上下文帧
        2. 对话沙箱发送资产索引帧
        3. 任务沙箱接收并处理
        4. 任务沙箱发送状态快照
        """
        print("\n--- 模式切换: 对话 → 任务 ---")
        
        # 1. 对话沙箱发送上下文帧
        self.dialog_sandbox.send_context_frame(
            target_node=self.task_node_id,
            summary=context_summary or "对话模式切换到任务模式"
        )
        
        # 2. 对话沙箱发送资产索引帧（如果有已生成的资产）
        if self.dialog_sandbox.state.generated_assets:
            self.dialog_sandbox.send_asset_index_frame(
                target_node=self.task_node_id,
                assets=self.dialog_sandbox.state.generated_assets
            )
        
        # 3. 任务沙箱接收帧
        received = self.task_sandbox.receive_frames()
        print(f"  任务沙箱收到 {len(received)} 个帧")
        
        # 4. 任务沙箱发送状态快照
        self.task_sandbox.send_state_snapshot(target_node=self.dialog_node_id)
        
        # 5. 对话沙箱接收状态快照
        dialog_received = self.dialog_sandbox.receive_frames()
        print(f"  对话沙箱收到 {len(dialog_received)} 个帧")
        
        self.stats.total_frames_routed += len(received) + len(dialog_received)
        
        return {
            "success": True,
            "frames_to_task": len(received),
            "frames_to_dialog": len(dialog_received),
            "task_state": self.task_sandbox.get_state_snapshot()
        }
    
    def get_status(self) -> dict:
        """获取网关状态"""
        return {
            "gateway": {
                "did": self.did,
                "trace_symbol": self.trace_symbol,
                "bridge_node_id": self.bridge_node_id,
                "started_at": self.stats.started_at
            },
            "stats": self.stats.to_dict(),
            "bus_stats": self.bus_queue.get_stats().to_dict(),
            "dialog_sandbox": self.dialog_sandbox.get_state_snapshot(),
            "task_sandbox": self.task_sandbox.get_state_snapshot(),
            "storage_stats": self.storage.get_storage_stats()
        }
    
    def print_status(self):
        """打印网关状态"""
        status = self.get_status()
        print("\n" + "="*60)
        print("  桥接网关状态")
        print("="*60)
        print(f"  握手: {status['stats']['successful_handshakes']}/{status['stats']['total_handshakes']} 成功")
        print(f"  路由帧: {status['stats']['total_frames_routed']}")
        print(f"  中转资产: {status['stats']['total_assets_transferred']}")
        print(f"  总线队列: {status['bus_stats']['queue_size']} 待处理")
        print(f"  对话沙箱: {status['dialog_sandbox']['generated_assets_count']} 个资产, {status['dialog_sandbox']['dialog_history_count']} 条消息")
        print(f"  任务沙箱: {status['task_sandbox']['received_assets_count']} 个资产, {status['task_sandbox']['task_count']} 个任务")
        print(f"  本地存储: {status['storage_stats']['total_files']} 个文件, {status['storage_stats']['total_size']} 字节")
        print("="*60 + "\n")
