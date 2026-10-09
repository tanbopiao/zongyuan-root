#!/usr/bin/env python3
"""
kernel_load_meta_protocol.py
Ω-OP-SCHED 内核启动阶段加载 meta_homo_protocol.lock.json
自动校验配置完整性、校验身份锚点，加载公理与校验规则，注入内核全局上下文。
溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 本源根 Ω-TAN-7-001
"""
import json
import hashlib
from pathlib import Path

# -------------------------- 内核常量锚点（固化，不可修改） --------------------------
DID_ANCHOR = "DID-BR-000002"
ROOT_OMEGA_ANCHOR = "Ω-TAN-7-001"
PROTO_LOCK_FILE = Path("./kernel/config/meta_homo_protocol.lock.json")


class MetaHomoProtocolLoader:
    def __init__(self):
        self.protocol_config = None
        self.config_sha256 = None
        self.load_success = False

    def calc_file_hash(self, file_path: Path) -> str:
        """计算配置文件SHA256哈希，用于防篡改校验"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def load_protocol(self):
        """加载并校验同源协议固化配置"""
        if not PROTO_LOCK_FILE.exists():
            raise FileNotFoundError(f"【内核致命错误】协议固化配置不存在：{PROTO_LOCK_FILE}")

        # 读取配置文件
        with open(PROTO_LOCK_FILE, "r", encoding="utf-8") as fp:
            self.protocol_config = json.load(fp)

        # 计算文件哈希
        self.config_sha256 = self.calc_file_hash(PROTO_LOCK_FILE)

        # 第一层锚点校验：DID、本源根必须和内核常量完全匹配
        cfg_did = self.protocol_config.get("DID")
        cfg_root_omega = self.protocol_config.get("root_omega")
        if cfg_did != DID_ANCHOR or cfg_root_omega != ROOT_OMEGA_ANCHOR:
            raise RuntimeError(f"【内核同源校验失败】配置锚点不匹配！\n"
                               f"内核锚点: DID={DID_ANCHOR}, root={ROOT_OMEGA_ANCHOR}\n"
                               f"文件锚点: DID={cfg_did}, root={cfg_root_omega}")

        # 第二层基础字段完整性校验
        mandatory_fields = ["snap_id", "proto_version", "status", "axioms", "identity", "double_verify"]
        for field in mandatory_fields:
            if field not in self.protocol_config:
                raise RuntimeError(f"【内核协议损坏】缺失必要字段：{field}")

        self.load_success = True
        print(f"✅ [元极恒一内核] 同源协议加载完成")
        print(f"✅ 文件SHA256: {self.config_sha256}")
        print(f"✅ 协议版本: {self.protocol_config['proto_version']}")
        print(f"✅ 协议状态: {self.protocol_config['status']}")
        return self.protocol_config

    def get_verify_rule(self):
        """对外暴露双层校验规则，供给调度引擎与Worker调用"""
        if not self.load_success:
            raise RuntimeError("协议尚未加载，无法获取校验规则")
        return self.protocol_config["double_verify"]

    def get_task_mandatory_fields(self):
        """获取任务报文强制字段，用于任务合法性校验"""
        return self.protocol_config["task_schema"]["mandatory_fields"]


# ====================== 内核启动入口 ======================
if __name__ == "__main__":
    kernel_proto_loader = MetaHomoProtocolLoader()
    try:
        proto_cfg = kernel_proto_loader.load_protocol()
        # 将协议全局注入Ω-OP-SCHED调度内核上下文
        GLOBAL_KERNEL_PROTO = proto_cfg
    except Exception as e:
        print(f"❌ 内核启动失败：{e}")
        exit(1)
