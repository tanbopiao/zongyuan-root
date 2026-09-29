#!/usr/bin/env python3
"""
政务中台RAG知识库引擎
- 向量化检索（TF-IDF + 语义相似度）
- 知识图谱（实体关系抽取）
- 混合检索（关键词+语义）
- 上下文增强（相关片段拼接）
"""
import json
import os
import re
import math
from collections import Counter, defaultdict
from datetime import datetime

DATA_DIR = '/opt/ZONGYUAN-ROOT/gov_api/data'

class RAGEngine:
    def __init__(self):
        self.policies = self._load_json('policies.json', [])
        self.guides = self._load_json('guides.json', [])
        self.doc_templates = self._load_json('doc_templates.json', [])
        self.knowledge_base = []
        self.inverted_index = defaultdict(list)
        self.doc_freq = Counter()
        self._build_knowledge_base()
        self._build_index()
    
    def _load_json(self, filename, default):
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    
    def _tokenize(self, text):
        """简单中文分词（按字符+常见词）"""
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
        tokens = []
        # 单字
        for char in text:
            if char.strip():
                tokens.append(char)
        # 2-gram
        for i in range(len(text)-1):
            if text[i].strip() and text[i+1].strip():
                tokens.append(text[i:i+2])
        return tokens
    
    def _build_knowledge_base(self):
        """构建知识库"""
        doc_id = 0
        # 政策
        for p in self.policies:
            if isinstance(p, dict):
                content = f"{p.get('title','')} {p.get('content','')} {p.get('summary','')} {p.get('category','')}"
                self.knowledge_base.append({
                    'id': f'policy_{doc_id}',
                    'type': 'policy',
                    'title': p.get('title', ''),
                    'content': content,
                    'category': p.get('category', ''),
                    'source': p
                })
                doc_id += 1
        # 办事指南
        for g in self.guides:
            if isinstance(g, dict):
                content = f"{g.get('title','')} {g.get('content','')} {g.get('materials','')} {g.get('process','')}"
                self.knowledge_base.append({
                    'id': f'guide_{doc_id}',
                    'type': 'guide',
                    'title': g.get('title', ''),
                    'content': content,
                    'category': g.get('category', ''),
                    'source': g
                })
                doc_id += 1
        # 公文模板
        for t in self.doc_templates:
            if isinstance(t, dict):
                content = f"{t.get('name','')} {t.get('description','')} {t.get('template','')}"
                self.knowledge_base.append({
                    'id': f'doc_{doc_id}',
                    'type': 'doc_template',
                    'title': t.get('name', ''),
                    'content': content,
                    'category': t.get('category', ''),
                    'source': t
                })
                doc_id += 1
    
    def _build_index(self):
        """构建倒排索引"""
        for doc in self.knowledge_base:
            tokens = set(self._tokenize(doc['content']))
            for token in tokens:
                self.inverted_index[token].append(doc['id'])
                self.doc_freq[token] += 1
    
    def _tf_idf_score(self, query_tokens, doc):
        """计算TF-IDF相似度"""
        doc_tokens = self._tokenize(doc['content'])
        doc_tf = Counter(doc_tokens)
        doc_len = len(doc_tokens)
        if doc_len == 0:
            return 0
        score = 0
        N = len(self.knowledge_base)
        for token in query_tokens:
            if token in doc_tf:
                tf = doc_tf[token] / doc_len
                df = self.doc_freq.get(token, 0)
                idf = math.log((N + 1) / (df + 1)) + 1
                score += tf * idf
        return score
    
    def _semantic_score(self, query, doc):
        """语义相似度（基于关键词重叠+标题匹配）"""
        score = 0
        query_lower = query.lower()
        title = doc['title'].lower()
        content = doc['content'].lower()
        # 标题匹配权重高
        if query_lower in title:
            score += 5
        # 内容匹配
        query_chars = set(query_lower)
        content_chars = set(content)
        overlap = len(query_chars & content_chars)
        score += overlap / max(len(query_chars), 1) * 3
        # 分类匹配
        if doc.get('category') and doc['category'] in query:
            score += 2
        return score
    
    def search(self, query, top_k=5, doc_type=None):
        """混合检索"""
        query_tokens = self._tokenize(query)
        scores = {}
        for doc in self.knowledge_base:
            if doc_type and doc['type'] != doc_type:
                continue
            tfidf = self._tf_idf_score(query_tokens, doc)
            semantic = self._semantic_score(query, doc)
            total = tfidf * 0.4 + semantic * 0.6
            if total > 0:
                scores[doc['id']] = total
        # 排序
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for doc_id, score in ranked:
            doc = next(d for d in self.knowledge_base if d['id'] == doc_id)
            results.append({
                'id': doc['id'],
                'type': doc['type'],
                'title': doc['title'],
                'category': doc.get('category', ''),
                'score': round(score, 4),
                'snippet': doc['content'][:200] + '...' if len(doc['content']) > 200 else doc['content'],
                'source': doc['source']
            })
        return results
    
    def get_context(self, query, max_docs=3):
        """获取RAG上下文（用于增强AI回答）"""
        results = self.search(query, top_k=max_docs)
        if not results:
            return ''
        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(f"[参考{i}] {r['title']}（{r['type']}）：{r['snippet']}")
        return '\n'.join(context_parts)
    
    def get_stats(self):
        """获取知识库统计"""
        type_count = Counter(d['type'] for d in self.knowledge_base)
        category_count = Counter(d.get('category', '未分类') for d in self.knowledge_base)
        return {
            'total_docs': len(self.knowledge_base),
            'by_type': dict(type_count),
            'by_category': dict(category_count),
            'index_size': len(self.inverted_index),
            'status': 'READY'
        }
    
    def extract_entities(self, text):
        """简单实体抽取（政策/部门/地点/时间）"""
        entities = {
            'policies': [],
            'departments': [],
            'locations': [],
            'dates': []
        }
        # 政策名称
        policy_patterns = [r'[《〈][^》〉]+[》〉]', r'[\u4e00-\u9fa5]+条例', r'[\u4e00-\u9fa5]+办法', r'[\u4e00-\u9fa5]+规定']
        for pattern in policy_patterns:
            entities['policies'].extend(re.findall(pattern, text))
        # 部门
        dept_patterns = [r'[\u4e00-\u9fa5]+局', r'[\u4e00-\u9fa5]+委', r'[\u4e00-\u9fa5]+办', r'[\u4e00-\u9fa5]+中心']
        for pattern in dept_patterns:
            entities['departments'].extend(re.findall(pattern, text))
        # 日期
        date_patterns = [r'\d{4}年\d{1,2}月\d{1,2}日', r'\d{4}-\d{1,2}-\d{1,2}']
        for pattern in date_patterns:
            entities['dates'].extend(re.findall(pattern, text))
        # 去重
        for k in entities:
            entities[k] = list(set(entities[k]))[:10]
        return entities

# 全局实例
rag_engine = RAGEngine()

if __name__ == '__main__':
    stats = rag_engine.get_stats()
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print()
    results = rag_engine.search('社保补贴', top_k=3)
    print('搜索"社保补贴"结果：')
    for r in results:
        print(f"  [{r['score']}] {r['title']} ({r['type']})")
