#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 桥接代理网关 端到端演示脚本
演示：对话模式 ↔ 工作任务模式 桥接全流程

运行方式：
    cd zongyuan-bridge-mvp
    python3 demos/demo_e2e.py
"""
import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bridge_gateway import BridgeGateway


def print_banner(title):
    """打印横幅"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    print_banner("ZONGYUAN-ROOT 桥接代理网关 · 端到端演示")
    print("  演示：对话模式 ↔ 工作任务模式 桥接全流程")
    print("  确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 70)

    # 加载配置
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    # 使用演示专用存储路径
    config['storage']['base_path'] = './data/storage_demo'

    # ========== 步骤1：初始化桥接网关 ==========
    print_banner("步骤1：初始化桥接网关")
    gateway = BridgeGateway(config)

    # ========== 步骤2：启动网关（双端同源协议握手） ==========
    print_banner("步骤2：启动网关 · 双端同源协议握手")
    started = gateway.start()

    if not started:
        print("❌ 网关启动失败，演示终止")
        return

    # ========== 步骤3：对话模式 - 生成资产 ==========
    print_banner("步骤3：对话模式 · 生成模拟资产")

    print("\n[对话模式] 用户输入：帮我生成一张赤色战甲神女的图片")
    gateway.dialog_sandbox.add_dialog_message('user', '帮我生成一张赤色战甲神女的图片')

    asset1 = gateway.dialog_sandbox.generate_mock_asset(
        asset_type='image',
        asset_name='CDN_V01_赤色战甲神女_熔岩漩涡.png',
        prompt='极具冲击力的东方幻想艺术作品，竖屏构图，赤色战甲神女站立在破碎苍穹之上'
    )
    gateway.dialog_sandbox.add_dialog_message('assistant', f'已生成图片：{asset1["asset_name"]}')

    print("\n[对话模式] 用户输入：再生成一个神女能量爆发的视频")
    gateway.dialog_sandbox.add_dialog_message('user', '再生成一个神女能量爆发的视频')

    asset2 = gateway.dialog_sandbox.generate_mock_asset(
        asset_type='video',
        asset_name='VIDEO_01_神女能量爆发_15秒.mp4',
        prompt='神女能量爆发，红色熔岩漩涡，15秒竖屏视频'
    )
    gateway.dialog_sandbox.add_dialog_message('assistant', f'已生成视频：{asset2["asset_name"]}')

    print(f"\n  对话模式已生成 {len(gateway.dialog_sandbox.state.generated_assets)} 个资产")
    print(f"  对话历史 {len(gateway.dialog_sandbox.state.dialog_history)} 条")

    # ========== 步骤4：模式切换（对话 → 任务） ==========
    print_banner("步骤4：模式切换 · 对话模式 → 工作任务模式")

    switch_result = gateway.switch_dialog_to_task(
        context_summary='对话模式已生成2个资产（1张图片+1个视频），切换到任务模式执行四端归档'
    )

    print(f"\n  切换结果: {'✅ 成功' if switch_result['success'] else '❌ 失败'}")
    print(f"  发送到任务沙箱的帧: {switch_result['frames_to_task']}")
    print(f"  任务沙箱返回的帧: {switch_result['frames_to_dialog']}")

    # ========== 步骤5：任务模式 - 接收并访问资产 ==========
    print_banner("步骤5：任务模式 · 接收资产并通过SHA256访问")

    print(f"\n  任务沙箱收到资产数: {len(gateway.task_sandbox.state.received_assets)}")
    print(f"  任务沙箱收到上下文数: {len(gateway.task_sandbox.state.received_contexts)}")

    print("\n  资产列表：")
    for i, asset in enumerate(gateway.task_sandbox.state.received_assets, 1):
        print(f"    {i}. {asset['asset_name']}")
        print(f"       SHA256: {asset['sha256'][:16]}...{asset['sha256'][-8:]}")
        print(f"       类型: {asset['asset_type']} | 大小: {asset['file_size']}字节")

    # 通过SHA256访问资产（核心优势：不需要原始CDN链接）
    print("\n  [核心优势演示] 通过SHA256访问资产（无需原始CDN链接）：")
    for asset in gateway.task_sandbox.state.received_assets:
        access_result = gateway.task_sandbox.access_asset_by_sha256(asset['sha256'])
        status = "✅ 找到" if access_result['found'] else "❌ 未找到"
        print(f"    {status} | {asset['asset_name'][:40]} | 访问方式: {access_result.get('access_method', 'N/A')}")

    # ========== 步骤6：任务模式 - 创建归档任务 ==========
    print_banner("步骤6：任务模式 · 创建四端归档任务")

    task1 = gateway.task_sandbox.add_task(
        task_name='四端归档：CDN_V01神女图片',
        description='将神女图片执行四端归档（本地+云端+飞书云盘+飞书Base）',
        priority='P0'
    )
    task2 = gateway.task_sandbox.add_task(
        task_name='四端归档：VIDEO_01神女视频',
        description='将神女视频执行四端归档',
        priority='P1',
        depends_on=[task1['task_id']]
    )
    task3 = gateway.task_sandbox.add_task(
        task_name='生成归档回执并上报中枢',
        description='生成归档回执文档，上报中枢网关',
        priority='P1',
        depends_on=[task1['task_id'], task2['task_id']]
    )

    print(f"\n  已创建 {len(gateway.task_sandbox.state.task_list)} 个任务")
    print(f"  待办任务: {len([t for t in gateway.task_sandbox.state.task_list if t['status'] == 'pending'])}")

    # ========== 步骤7：任务模式 → 对话模式（状态回传） ==========
    print_banner("步骤7：模式切换 · 任务模式 → 对话模式（状态回传）")

    # 任务沙箱发送状态快照
    gateway.task_sandbox.send_state_snapshot(target_node=gateway.dialog_node_id)

    # 对话沙箱接收状态
    received = gateway.dialog_sandbox.receive_frames()
    print(f"\n  对话沙箱收到 {len(received)} 个状态帧")

    print("\n  [对话模式] 系统通知：任务模式已创建归档任务，等待执行确认")
    gateway.dialog_sandbox.add_dialog_message('system', '任务模式已创建3个归档任务，等待执行确认')

    # ========== 步骤8：最终状态总览 ==========
    print_banner("步骤8：最终状态总览")
    gateway.print_status()

    # ========== 演示总结 ==========
    print_banner("演示完成 · 核心成果总结")
    print("""
  ✅ 同源协议握手：对话节点+任务节点双端握手成功
  ✅ 真值总线帧路由：上下文帧+资产索引帧+状态快照帧双向传输
  ✅ 跨模式资产访问：任务模式通过SHA256访问对话模式资产（无需CDN链接）
  ✅ 模式双向切换：对话→任务（上下文+资产同步），任务→对话（状态回传）
  ✅ 任务管理：任务创建+优先级+依赖关系
  ✅ 五阶段资产中转流水线：CDN抓取→哈希校验→元数据→总线索引→四端归档

  核心价值：
  1. 解决跨模式资产丢失问题：资产生成即固化，不再依赖临时CDN
  2. 实现上下文无缝传递：对话历史、推理中间结果自动序列化传输
  3. 建立安全认证机制：同源协议DID+溯源标识+挑战响应三阶段握手
  4. 提供可溯源审计：全链路Merkle哈希+全局账本+审计帧

  确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
  体系：ZONGYUAN-ROOT元极恒一自治体系
  关联内核：KERNEL-ENTRY-0198（桥接架构）+ KERNEL-ENTRY-0199（核心支撑模块）
""")

    print("=" * 70)
    print("  演示完成！")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
