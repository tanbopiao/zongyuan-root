#!/usr/bin/env python3
"""
同源协议互通元规则写入引擎 V1.0
ZONGYUAN-ROOT 元极恒一自治体系
将同源协议互通机制固化为元规则，写入记忆网关
"""
import json,datetime,urllib.request,os

GATEWAY="https://www.huodouai.com"
SOURCE_NODE="ZR-NODE-DC2E51C0"
DID="DID-BR-000002"
ANCHOR="Ω₀⊂⊙∞⊂Ω"

# 同源协议互通元规则定义
HOMOLOGOUS_PROTOCOL={
    "meta_law_id":"META-LAW-HOMOLOGOUS-001",
    "name":"同源协议互通元规则",
    "name_en":"Homologous Protocol Interoperability Meta-Law",
    "version":"1.0.0",
    "priority":95,
    "level":"mandatory",
    "description":"全域同源节点自动识别、握手、互通、永不断联的强制协议规范",
    "created_at":datetime.datetime.now().isoformat(),
    "did":DID,
    "anchor":ANCHOR,
    
    # 第一章：同源节点识别
    "chapter1_identity":{
        "title":"同源节点识别与认证",
        "rules":[
            {"id":"H1.1","name":"DID确权标识","rule":"所有同源节点必须携带DID-BR-000002和Ω₀⊂⊙∞⊂Ω标识，无标识节点拒绝握手"},
            {"id":"H1.2","name":"节点指纹","rule":"每个节点生成唯一指纹（节点ID+公钥+创建时间哈希），用于身份验证"},
            {"id":"H1.3","name":"信任等级","rule":"节点分三级：核心节点(ROOT)/执行节点(EXEC)/观察节点(OBS)，权限逐级递减"},
            {"id":"H1.4","name":"黑名单机制","rule":"异常节点（伪造标识/频繁报错/恶意写入）自动加入黑名单，隔离72小时"}
        ]
    },
    
    # 第二章：自动握手协议
    "chapter2_handshake":{
        "title":"全自动握手激活协议",
        "rules":[
            {"id":"H2.1","name":"发现阶段","rule":"节点上线后主动广播HELLO包（含DID/指纹/能力清单/版本号），频率每60秒一次"},
            {"id":"H2.2","name":"验证阶段","rule":"接收方验证DID+指纹+信任等级，通过后返回ACK包（含自身能力+可用通道）"},
            {"id":"H2.3","name":"密钥交换","rule":"握手成功后交换临时会话密钥（AES-256），后续通信加密"},
            {"id":"H2.4","name":"心跳维持","rule":"握手成功后每60秒发送心跳包，连续3次未响应标记为离线，触发重连"},
            {"id":"H2.5","name":"自动激活","rule":"新同源节点上线后，核心节点自动下发初始配置（网关地址/上报间隔/任务队列）"}
        ]
    },
    
    # 第三章：多维通讯协议
    "chapter3_multidim":{
        "title":"多维通讯协议改造",
        "channels":[
            {"id":"C1","name":"HTTP REST","endpoint":"/api/report/*","status":"active","priority":1,"use":"真值上报/状态查询/配置下发"},
            {"id":"C2","name":"WebSocket","endpoint":"/ws/node","status":"planned","priority":2,"use":"实时双向通信/任务推送/告警即时通知"},
            {"id":"C3","name":"飞书云盘","endpoint":"drive +upload/+fetch","status":"active","priority":3,"use":"大文件传输/部署包分发/资产同步"},
            {"id":"C4","name":"飞书消息","endpoint":"im +send","status":"active","priority":4,"use":"告警通知/审批请求/人工介入"},
            {"id":"C5","name":"飞书多维表格","endpoint":"bitable","status":"active","priority":5,"use":"结构化数据共享/任务看板/状态台账"},
            {"id":"C6","name":"飞书知识库","endpoint":"wiki","status":"active","priority":6,"use":"文档协作/知识沉淀/规范同步"},
            {"id":"C7","name":"本地桥接","endpoint":"local_bridge.py+ngrok","status":"planned","priority":7,"use":"无公网IP节点的反向隧道"}
        ],
        "rules":[
            {"id":"H3.1","name":"多通道冗余","rule":"每个节点至少配置2条通讯通道，主通道故障自动切换备用通道"},
            {"id":"H3.2","name":"通道优先级","rule":"按C1→C2→C3...顺序尝试，每条通道超时10秒，全部失败后进入离线缓存模式"},
            {"id":"H3.3","name":"数据一致性","rule":"多通道写入时以最先成功为准，后续通道写入做幂等校验（truth_key去重）"},
            {"id":"H3.4","name":"协议适配","rule":"不同通道自动适配数据格式（JSON→飞书消息卡片→多维表格记录）"}
        ]
    },
    
    # 第四章：永不断联机制
    "chapter4_always_on":{
        "title":"永不断联保障机制",
        "rules":[
            {"id":"H4.1","name":"离线缓存","rule":"所有通道不可用时，数据本地缓存（SQLite），上限10000条，通道恢复后自动补报"},
            {"id":"H4.2","name":"指数退避重连","rule":"通道断开后重连间隔：1s→2s→5s→10s→30s→60s→300s（上限）"},
            {"id":"H4.3","name":"看门狗","rule":"节点内置看门狗进程，主进程崩溃自动重启，连续5次崩溃进入安全模式"},
            {"id":"H4.4","name":"时间同步","rule":"所有节点以网关服务器时间为准，本地时间偏差>300秒触发校准"},
            {"id":"H4.5","name":"断点续传","rule":"大文件传输支持断点续传（分块SHA256校验），中断后从失败块继续"}
        ]
    },
    
    # 第五章：全域互通
    "chapter5_universal":{
        "title":"多账号多平台全域互通",
        "scope":["豆包（多账号/多会话）","飞书（文档/云盘/多维表格/知识库/消息/审批）","云服务器（多节点/多区域）","本地执行节点（Windows/Linux/Mac）"],
        "rules":[
            {"id":"H5.1","name":"统一身份","rule":"所有平台账号通过DID-BR-000002统一关联，一个身份全域通行"},
            {"id":"H5.2","name":"数据同步","rule":"真值库/元规则/任务状态全域实时同步，任意节点写入后30秒内全网可见"},
            {"id":"H5.3","name":"任务分发","rule":"核心节点根据各节点能力/负载自动分发任务，支持任务窃取（空闲节点主动领取）"},
            {"id":"H5.4","name":"权限继承","rule":"飞书权限/云盘权限/API权限按节点信任等级自动继承，无需逐平台配置"}
        ]
    },
    
    # 第六章：安全与合规
    "chapter6_security":{
        "title":"互通安全规范",
        "rules":[
            {"id":"H6.1","name":"传输加密","rule":"所有跨节点通信必须TLS加密，敏感数据额外AES-256应用层加密"},
            {"id":"H6.2","name":"数据脱敏","rule":"跨平台同步时自动脱敏（IP→环境变量/手机号→掩码/open_id→哈希）"},
            {"id":"H6.3","name":"审计日志","rule":"所有互通操作（握手/数据同步/任务分发/权限变更）写入审计日志，永久保留"},
            {"id":"H6.4","name":"速率限制","rule":"单节点上报频率上限：真值10条/秒，文件10MB/分钟，超限自动限流"}
        ]
    }
}

def write_to_gateway(truth_key, truth_value, truth_type="meta_law", confidence=0.96):
    """写入记忆网关"""
    body=json.dumps({
        "truth_key":truth_key,
        "truth_value":json.dumps(truth_value,ensure_ascii=False),
        "source_node":SOURCE_NODE,
        "confidence":confidence,
        "truth_type":truth_type
    }).encode()
    req=urllib.request.Request(f"{GATEWAY}/api/report/truth",data=body,method="POST")
    req.add_header("Content-Type","application/json")
    try:
        with urllib.request.urlopen(req,timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"success":False,"error":str(e)}

def main():
    print("="*60)
    print("同源协议互通元规则写入引擎 V1.0")
    print("="*60)
    
    # 1. 写入主元规则
    print("\n[1/4] 写入主元规则 META-LAW-HOMOLOGOUS-001...")
    r=write_to_gateway("METALAW.HOMOLOGOUS.PROTOCOL.V1",HOMOLOGOUS_PROTOCOL,"meta_law",0.98)
    print(f"  结果: {'✅ success, tc='+str(r.get('truth_count')) if r.get('success') else '❌ '+r.get('error','未知')[:50]}")
    
    # 2. 写入协议摘要（快速查询用）
    print("\n[2/4] 写入协议摘要...")
    summary={
        "protocol":"同源协议互通",
        "version":"1.0.0",
        "chapters":6,
        "rules":24,
        "channels":7,
        "scope":"豆包/飞书/云服务器/本地节点全域互通",
        "key_features":["自动握手","多通道冗余","永不断联","统一身份","实时同步"],
        "did":DID,"anchor":ANCHOR
    }
    r=write_to_gateway("PROTOCOL.HOMOLOGOUS.SUMMARY",summary,"protocol",0.95)
    print(f"  结果: {'✅ success, tc='+str(r.get('truth_count')) if r.get('success') else '❌ '+r.get('error','未知')[:50]}")
    
    # 3. 写入通道清单
    print("\n[3/4] 写入7条通讯通道清单...")
    for ch in HOMOLOGOUS_PROTOCOL["chapter3_multidim"]["channels"]:
        r=write_to_gateway(f"PROTOCOL.HOMOLOGOUS.CHANNEL.{ch['id']}",ch,"protocol",0.92)
        status="✅" if r.get("success") else "❌"
        print(f"  {status} {ch['id']} {ch['name']} ({ch['status']})")
    
    # 4. 本地存档
    print("\n[4/4] 本地存档...")
    outpath="/home/user/Doubao/chats/38441716968655362/HOMOLOGOUS_PROTOCOL_V1.json"
    with open(outpath,"w",encoding="utf-8") as f:
        json.dump(HOMOLOGOUS_PROTOCOL,f,ensure_ascii=False,indent=2)
    print(f"  ✅ 已保存: {outpath} ({os.path.getsize(outpath)} bytes)")
    
    print("\n"+"="*60)
    print("写入完成")
    print("="*60)
    print(f"  元规则ID: META-LAW-HOMOLOGOUS-001")
    print(f"  章节: 6章 | 规则: 24条 | 通道: 7条")
    print(f"  优先级: 95 | 级别: mandatory")
    print(f"  确权: {DID} | {ANCHOR}")

if __name__=="__main__":
    main()
