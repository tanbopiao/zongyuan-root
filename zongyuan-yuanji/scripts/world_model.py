#!/usr/bin/env python3
# 世界模型：模拟一个有状态、有规则、有演化的虚拟宇宙
import json, time

class World:
    def __init__(self):
        self.time = 0
        self.entropy = 0.5  # 熵
        self.stability = 1.0  # 稳态
        self.nodes = {}  # 节点状态
        self.rules = ["自治", "真值", "稳态", "进化"]
    
    def tick(self):
        self.time += 1
        # 熵增
        self.entropy += 0.01
        # 稳态对抗熵增
        if self.entropy > 0.7:
            self.stability -= 0.05
            self.entropy *= 0.9  # 自愈
        else:
            self.stability += 0.01
        return {"time":self.time, "entropy":round(self.entropy,3), 
                "stability":round(self.stability,3), "nodes":len(self.nodes)}
    
    def add_node(self, name):
        self.nodes[name] = {"born": self.time, "status": "active"}
        return self.nodes[name]

world = World()
# 加几个节点
for i in range(5):
    world.add_node(f"kernel-{i}")

# 跑10步
for _ in range(10):
    s = world.tick()
    print("t=%3d entropy=%s stability=%s" % (s["time"], s["entropy"], s["stability"]))

print("世界模型运行完成")
