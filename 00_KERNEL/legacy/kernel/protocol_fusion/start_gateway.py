#!/usr/bin/env python3
"""
协议融合引擎启动脚本
"""
import sys
import os
import logging

# 添加父目录到路径（kernel目录）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol_fusion import UnifiedAPIGateway, ProtocolRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    host = os.environ.get("PROTOCOL_GATEWAY_HOST", "0.0.0.0")
    port = int(os.environ.get("PROTOCOL_GATEWAY_PORT", "8900"))

    logger.info("=" * 60)
    logger.info("ZONGYUAN-ROOT 协议融合引擎启动")
    logger.info(f"版本: 1.0.0 | 协议标准: ZR-PROTO-V1.0")
    logger.info(f"监听: {host}:{port}")
    logger.info("=" * 60)

    # 创建网关
    gateway = UnifiedAPIGateway(host=host, port=port)

    # 注册默认服务
    gateway.register_default_services()
    logger.info(f"已注册 {len(gateway.registry.list_services())} 个服务")
    logger.info(f"已注册 {len(gateway.registry.list_adapters())} 个适配器")

    # 启动网关
    logger.info("网关启动完成，等待请求...")
    gateway.start()


if __name__ == "__main__":
    main()
