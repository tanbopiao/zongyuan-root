#!/usr/bin/env python3
"""
本地阶段性全域大脑 - 记忆系统
功能：记忆存储 + 关键词召回 + 心跳维护
"""
import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path('/opt/ZONGYUAN-ROOT/ZONGYUAN-ROOT')
MEMORY_DIR = ROOT / 'memory'
CONFIG_DIR = ROOT / 'config'
LOG_DIR = ROOT / 'logs'

MEMORY_FILE = MEMORY_DIR / 'memory_index.json'

class LocalBrain:
    def __init__(self):
        self.root = ROOT
        self.memory_file = MEMORY_FILE
        self.config = self._load_config()
        self.memories = self._load_memories()
    
    def _load_config(self):
        with open(CONFIG_DIR / 'kernel_state.json') as f:
            return json.load(f)
    
    def _load_memories(self):
        if self.memory_file.exists():
            with open(self.memory_file) as f:
                return json.load(f)
        return {
            'did': self.config['did'],
            'total_memories': 0,
            'memories': []
        }
    
    def _save_memories(self):
        with open(self.memory_file, 'w') as f:
            json.dump(self.memories, f, indent=2, ensure_ascii=False)
    
    def remember(self, category, content, tags=None):
        """写入一条新记忆"""
        memory = {
            'id': f"MEM-{self.memories['total_memories']+1:04d}",
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'content': content,
            'tags': tags or []
        }
        self.memories['memories'].append(memory)
        self.memories['total_memories'] += 1
        self._save_memories()
        print(f'✅ 记忆已写入: {memory["id"]} - {content[:30]}...')
        return memory
    
    def recall(self, keyword, top_k=5):
        """根据关键词召回相关记忆"""
        keyword = keyword.lower()
        results = []
        for m in self.memories['memories']:
            score = 0
            if keyword in m['content'].lower():
                score += 10
            if keyword in str(m['tags']).lower():
                score += 5
            if score > 0:
                results.append((score, m))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in results[:top_k]]
    
    def heartbeat(self):
        """心跳更新"""
        self.config['last_heartbeat'] = datetime.now().isoformat()
        with open(CONFIG_DIR / 'kernel_state.json', 'w') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        return self.config['last_heartbeat']
    
    def status(self):
        """返回大脑状态"""
        return {
            'did': self.config['did'],
            'version': self.config['version'],
            'status': self.config['status'],
            'total_memories': self.memories['total_memories'],
            'last_heartbeat': self.config['last_heartbeat'],
            'anchor': self.config['trace_symbol']
        }

if __name__ == '__main__':
    brain = LocalBrain()
    
    # 初始化：写入第一条记忆
    if brain.memories['total_memories'] == 0:
        brain.remember(
            category='init',
            content='本地阶段性全域大脑初始化完成',
            tags=['init', 'core', 'v53']
        )
    
    # 打印状态
    print('=== 本地大脑状态 ===')
    s = brain.status()
    for k, v in s.items():
        print(f'  {k}: {v}')
    
    # 心跳
    brain.heartbeat()
    print('\n💓 心跳已更新')
