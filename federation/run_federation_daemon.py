import time, json, os, sys
sys.path.insert(0, '/opt/ZONGYUAN-ROOT/federation')
NODES_FILE = "/opt/ZONGYUAN-ROOT/federation/federation_nodes.json"
print('[联邦引擎] 启动，节点数:', len(json.load(open(NODES_FILE))))
while True:
    try:
        nodes = json.load(open(NODES_FILE))
        for nid, node in nodes.items():
            if node.get("role") == "advisor":
                pass  # 可添加心跳检测
        time.sleep(300)
    except Exception as e:
        print(f'[联邦引擎] 错误: {e}')
        time.sleep(60)
