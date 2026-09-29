#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双轨记忆索引桥 - 核心映射引擎
truth_key(云端记忆网关9120) ↔ asset_id(本地M9账本/IMA/飞书Base)

通道：
  1. RULE_EXACT    - 精确ID引用匹配
  2. RULE_NAMING   - 命名规范匹配
  3. SEMANTIC      - 语义关键词匹配
  4. REFERENCE     - 上下文引用推断
  5. MANUAL        - 人工确认

铁律：AAB双隔离 | 本地仿真→人工审核→才上云 | 真值优先
锚：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""
import json
import hashlib
import re
import os
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set

# ===================== 配置 =====================
BRIDGE_ID = "DUAL-INDEX-BRIDGE-V1.0"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

# 语义匹配置信度阈值
SEMANTIC_THRESHOLD = 0.35
# 关键词最小长度
MIN_KEYWORD_LEN = 2

# ===================== 工具函数 =====================

def sha256_hex(text: str, length: int = 16) -> str:
    """计算SHA256哈希前N位"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:length].upper()


def extract_keywords(text: str) -> Set[str]:
    """
    从文本中提取关键词集合
    - 中文词（2字以上连续中文）
    - 英文大写缩写（2字母以上）
    - 技术术语（API/SSH/SDK/IaC等）
    """
    if not text:
        return set()
    # 中文连续词
    cn_words = set(re.findall(r'[\u4e00-\u9fa5]{2,}', text))
    # 英文大写缩写
    en_abbr = set(re.findall(r'[A-Z]{2,}', text))
    # 技术术语（小写也可）
    tech_terms = set(re.findall(r'\b(?:api|ssh|sdk|iac|cpu|ram|dns|tcp|udp|http|https|json|xml|yaml|sql|nosql|kv|cdn|oss|cos|nginx|flask|fastapi|docker|k8s|vm|pid|gui|cli|sdk)\b', text, re.IGNORECASE))
    # 过滤过短和停用词
    stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '他', '她', '它', '们', '而', '与', '及', '或', '等', '之', '其', '此', '该', '所', '以', '为', '于', '从', '向', '对', '将', '把', '被', '让', '使', '令', '叫', '请', '能', '可以', '应该', '必须', '需要', '已经', '正在', '将要'}
    keywords = set()
    for w in cn_words:
        if len(w) >= MIN_KEYWORD_LEN and w not in stopwords:
            keywords.add(w)
    for w in en_abbr:
        if len(w) >= 2:
            keywords.add(w.upper())
    for w in tech_terms:
        keywords.add(w.upper())
    return keywords


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """计算Jaccard相似度"""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def now_iso() -> str:
    return datetime.now().isoformat()


# ===================== 数据加载器 =====================

class TruthKeyLoader:
    """加载云端truth_key数据（从本地镜像）"""

    def __init__(self, mirror_path: str):
        self.mirror_path = mirror_path
        self.truths: Dict[str, dict] = {}
        self._load()

    def _load(self):
        with open(self.mirror_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.truths = data.get('truths', {})

    def get_all(self) -> Dict[str, dict]:
        return self.truths

    def get_keywords(self, key: str) -> Set[str]:
        """获取某个truth_key的关键词集合（键名+value内容）"""
        if key not in self.truths:
            return set()
        v = self.truths[key]
        text = key + ' '
        val = v.get('value', '')
        if isinstance(val, str):
            # 只取前500字避免过长
            text += val[:500]
        elif isinstance(val, dict):
            text += json.dumps(val, ensure_ascii=False)[:500]
        cat = v.get('category', '')
        if cat:
            text += ' ' + cat
        return extract_keywords(text)

    def get_value_preview(self, key: str, max_len: int = 200) -> str:
        if key not in self.truths:
            return ''
        val = self.truths[key].get('value', '')
        if isinstance(val, str):
            return val[:max_len]
        return json.dumps(val, ensure_ascii=False)[:max_len]


class AssetLoader:
    """加载本地asset_id数据（IMA目录 + 飞书Base台账）"""

    def __init__(self, ima_path: str, feishu_base_records: List[dict] = None):
        self.ima_path = ima_path
        self.assets: Dict[str, dict] = {}
        self._load_ima()
        if feishu_base_records:
            self._load_feishu_base(feishu_base_records)

    def _load_ima(self):
        """加载IMA资产目录，使用media_id作为唯一标识，合并同组标题"""
        with open(self.ima_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 先按asset_id分组，收集所有标题
        group_titles = defaultdict(list)
        group_records = defaultdict(list)
        for atype, assets in data.get('assets_by_type', {}).items():
            if isinstance(assets, list):
                for a in assets:
                    if isinstance(a, dict):
                        aid = a.get('asset_id', '')
                        if aid:
                            title = a.get('title', '')
                            if title:
                                group_titles[aid].append(title)
                            group_records[aid].append({**a, '_ima_type': atype})

        # 为每个文件创建唯一条目（使用media_id或哈希）
        for atype, assets in data.get('assets_by_type', {}).items():
            if isinstance(assets, list):
                for a in assets:
                    if not isinstance(a, dict):
                        continue
                    aid = a.get('asset_id', '')
                    media_id = a.get('media_id', '')
                    title = a.get('title', '')
                    sha = a.get('sha256', '')

                    # 唯一ID：优先media_id，其次sha前16位，最后asset_id+title哈希
                    if media_id:
                        unique_id = f"IMA-MEDIA-{media_id}"
                    elif sha:
                        unique_id = f"IMA-SHA-{sha[:16]}"
                    else:
                        unique_id = f"IMA-{aid}-{sha256_hex(title or aid, 8)}"

                    if unique_id in self.assets:
                        continue

                    # 合并同组所有标题作为额外关键词上下文
                    all_titles = list(set(group_titles.get(aid, [])))
                    context_titles = ' '.join(all_titles[:10])  # 最多10个标题

                    self.assets[unique_id] = {
                        'asset_id': unique_id,
                        'ima_group_id': aid,
                        'source': 'IMA',
                        'asset_type': a.get('asset_type', atype),
                        'title': title,
                        'sha256': sha,
                        'media_id': media_id,
                        'kb_id': a.get('kb_id', ''),
                        'context_titles': context_titles,
                    }

    def _load_feishu_base(self, records: List[dict]):
        """
        从飞书Base记录加载资产
        records中的键为字段ID(fldxxx)，需要映射到实际字段名
        字段映射(按索引): 0=资产名称, 2=DID, 4=SHA256, 7=真值SHA256, 10=资产ID
        """
        # 字段ID到名称的映射（根据实际Base结构）
        FIELD_MAP = {
            'fldddwY6MD': 'asset_name',
            'fldAy19GI3': 'did',
            'fldFL8YczA': 'sha256_short',
            'fldpradZn6': 'sha256_full',
            'fldwr8rm1r': 'asset_id',
            'fld0pXLyyg': 'field_1',
            'fldd1J50k8': 'field_3',
            'fldnOjYGVD': 'field_5',
            'fldoKPdpdp': 'field_6',
            'fldTjNagV7': 'field_8',
            'fldumYwXip': 'field_9',
        }

        for r in records:
            # 映射字段
            mapped = {}
            for fid, val in r.items():
                name = FIELD_MAP.get(fid, fid)
                mapped[name] = val

            aid = mapped.get('asset_id', '')
            if not aid:
                # 如果没有asset_id，用名称哈希生成
                name = mapped.get('asset_name', '')
                if name:
                    aid = f"KD-AUTO-{sha256_hex(name, 8)}"

            if aid and aid not in self.assets:
                sha = mapped.get('sha256_full', '') or mapped.get('sha256_short', '')
                self.assets[aid] = {
                    'asset_id': aid,
                    'source': 'FEISHU_BASE',
                    'asset_type': 'archived_asset',
                    'title': mapped.get('asset_name', ''),
                    'sha256': sha,
                    'did': mapped.get('did', ''),
                    'description': '',
                }

    def get_all(self) -> Dict[str, dict]:
        return self.assets

    def get_keywords(self, aid: str) -> Set[str]:
        if aid not in self.assets:
            return set()
        a = self.assets[aid]
        text = (a.get('title', '') + ' ' +
                a.get('description', '') + ' ' +
                a.get('asset_type', '') + ' ' +
                a.get('context_titles', '') + ' ' +
                aid)
        return extract_keywords(text)


# ===================== 匹配通道 =====================

class MatchEngine:
    """多通道匹配引擎"""

    def __init__(self, truth_loader: TruthKeyLoader, asset_loader: AssetLoader):
        self.truth_loader = truth_loader
        self.asset_loader = asset_loader
        self.mappings: List[dict] = []
        self._truth_keywords_cache: Dict[str, Set[str]] = {}
        self._asset_keywords_cache: Dict[str, Set[str]] = {}

    def _get_truth_keywords(self, key: str) -> Set[str]:
        if key not in self._truth_keywords_cache:
            self._truth_keywords_cache[key] = self.truth_loader.get_keywords(key)
        return self._truth_keywords_cache[key]

    def _get_asset_keywords(self, aid: str) -> Set[str]:
        if aid not in self._asset_keywords_cache:
            self._asset_keywords_cache[aid] = self.asset_loader.get_keywords(aid)
        return self._asset_keywords_cache[aid]

    def _make_mapping_id(self, truth_key: str, asset_id: str) -> str:
        th = sha256_hex(truth_key, 8)
        ah = sha256_hex(asset_id, 8)
        return f"MAP-{th}-{ah}"

    def _build_record(self, truth_key: str, asset_id: str,
                      channel: str, confidence: float,
                      evidence: str, semantic_score: float = 0.0,
                      rule_score: float = 0.0) -> dict:
        t = self.truth_loader.truths.get(truth_key, {})
        a = self.asset_loader.assets.get(asset_id, {})
        return {
            'mapping_id': self._make_mapping_id(truth_key, asset_id),
            'truth_key': truth_key,
            'truth_category': t.get('category', ''),
            'truth_node_id': t.get('node_id', ''),
            'asset_id': asset_id,
            'asset_source': a.get('source', ''),
            'asset_type': a.get('asset_type', ''),
            'asset_title': a.get('title', ''),
            'match_channel': channel,
            'confidence': round(confidence, 4),
            'match_evidence': evidence,
            'semantic_score': round(semantic_score, 4),
            'rule_score': round(rule_score, 4),
            'status': 'PENDING',
            'created_at': now_iso(),
            'updated_at': now_iso(),
        }

    # ---- 通道1: 精确ID引用匹配 ----
    def channel_rule_exact(self) -> List[dict]:
        """
        在truth_key的value中搜索asset_id的精确引用
        在asset的title/description中搜索truth_key的精确引用
        """
        results = []
        asset_ids = set(self.asset_loader.assets.keys())
        truth_keys = set(self.truth_loader.truths.keys())

        # truth -> asset: 在truth value中找asset_id
        for tk, tv in self.truth_loader.truths.items():
            val = tv.get('value', '')
            val_str = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
            for aid in asset_ids:
                if aid in val_str:
                    rec = self._build_record(
                        tk, aid, 'RULE_EXACT', 0.95,
                        f"truth_key的value中精确包含asset_id: {aid}",
                        rule_score=1.0
                    )
                    results.append(rec)

        # asset -> truth: 在asset title/desc中找truth_key
        for aid, av in self.asset_loader.assets.items():
            text = av.get('title', '') + ' ' + av.get('description', '')
            for tk in truth_keys:
                if tk in text:
                    # 避免重复
                    mid = self._make_mapping_id(tk, aid)
                    if not any(r['mapping_id'] == mid for r in results):
                        rec = self._build_record(
                            tk, aid, 'RULE_EXACT', 0.95,
                            f"asset的title/description中精确包含truth_key: {tk}",
                            rule_score=1.0
                        )
                        results.append(rec)

        return results

    # ---- 通道2: 命名规范匹配 ----
    def channel_rule_naming(self) -> List[dict]:
        """
        基于命名规范的匹配：
        - KD-{CATEGORY}-{NUMBER} 格式的truth_key与asset_id对应
        - 相同category前缀+相近编号
        """
        results = []
        kd_pattern = re.compile(r'KD-([A-Z]+)-(\d+)')

        # 收集KD格式的truth_key和asset_id
        tk_kd = {}
        for tk in self.truth_loader.truths.keys():
            m = kd_pattern.search(tk)
            if m:
                cat, num = m.group(1), int(m.group(2))
                tk_kd.setdefault(cat, []).append((num, tk))

        aid_kd = {}
        for aid in self.asset_loader.assets.keys():
            m = kd_pattern.search(aid)
            if m:
                cat, num = m.group(1), int(m.group(2))
                aid_kd.setdefault(cat, []).append((num, aid))

        # 同category内匹配
        for cat in set(tk_kd.keys()) & set(aid_kd.keys()):
            tk_list = sorted(tk_kd[cat])
            aid_list = sorted(aid_kd[cat])
            for tnum, tk in tk_list:
                for anum, aid in aid_list:
                    if tnum == anum:
                        # 完全相同编号
                        rec = self._build_record(
                            tk, aid, 'RULE_NAMING', 0.85,
                            f"同category({cat})同编号({tnum})命名规范匹配",
                            rule_score=0.9
                        )
                        results.append(rec)
                    elif abs(tnum - anum) <= 2:
                        # 相近编号（差<=2），低置信度
                        rec = self._build_record(
                            tk, aid, 'RULE_NAMING', 0.60,
                            f"同category({cat})相近编号(t={tnum},a={anum})命名规范匹配",
                            rule_score=0.6
                        )
                        results.append(rec)
        return results

    # ---- 通道3: 语义关键词匹配 ----
    def channel_semantic(self, top_k: int = 3) -> List[dict]:
        """
        基于关键词集合的Jaccard相似度匹配
        对每个truth_key，找相似度最高的top_k个asset
        """
        results = []
        truth_keys = list(self.truth_loader.truths.keys())
        asset_ids = list(self.asset_loader.assets.keys())

        # 预计算所有asset的关键词
        asset_kw = {aid: self._get_asset_keywords(aid) for aid in asset_ids}

        for tk in truth_keys:
            tk_kw = self._get_truth_keywords(tk)
            if not tk_kw:
                continue

            # 计算与所有asset的相似度
            scores = []
            for aid in asset_ids:
                ak = asset_kw[aid]
                if not ak:
                    continue
                sim = jaccard_similarity(tk_kw, ak)
                if sim >= SEMANTIC_THRESHOLD:
                    scores.append((sim, aid))

            # 取top_k
            scores.sort(reverse=True)
            for sim, aid in scores[:top_k]:
                # 置信度 = 基础0.6 + 相似度*0.35，上限0.92
                confidence = min(0.6 + sim * 0.35, 0.92)
                common_kw = tk_kw & asset_kw[aid]
                evidence = f"语义Jaccard相似度={sim:.3f}, 共同关键词({len(common_kw)}): {', '.join(list(common_kw)[:10])}"
                rec = self._build_record(
                    tk, aid, 'SEMANTIC', confidence, evidence,
                    semantic_score=sim
                )
                results.append(rec)

        return results

    # ---- 通道4: 上下文引用推断 ----
    def channel_reference(self) -> List[dict]:
        """
        引用匹配：truth_key的value描述了某个资产的部署/锁档/状态
        通过关键词（部署/锁档/上线/归档/已发布等）+ 资产类型推断关联
        """
        results = []
        deploy_keywords = {'部署', '上线', '发布', '归档', '锁档', '已部署', '已上线', '已发布', '已归档', '配置', '安装', '启动', '运行', '服务'}

        for tk, tv in self.truth_loader.truths.items():
            val = tv.get('value', '')
            val_str = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
            tk_kw = self._get_truth_keywords(tk)

            # 如果truth_key包含部署/锁档类关键词
            has_deploy = bool(tk_kw & deploy_keywords) or any(kw in val_str for kw in deploy_keywords)
            if not has_deploy:
                continue

            # 找与该truth_key语义最相关的asset（但不走纯语义通道，用引用推断）
            best_asset = None
            best_score = 0
            for aid in self.asset_loader.assets.keys():
                ak = self._get_asset_keywords(aid)
                sim = jaccard_similarity(tk_kw, ak)
                if sim > best_score and sim >= 0.2:
                    best_score = sim
                    best_asset = aid

            if best_asset:
                confidence = min(0.55 + best_score * 0.3, 0.82)
                rec = self._build_record(
                    tk, best_asset, 'REFERENCE', confidence,
                    f"truth_key含部署/锁档上下文，推断关联asset(语义相似度={best_score:.3f})",
                    semantic_score=best_score, rule_score=0.5
                )
                results.append(rec)

        return results

    # ---- 执行所有通道 ----
    def run_all_channels(self) -> List[dict]:
        """执行所有匹配通道，去重合并"""
        all_mappings = []
        seen_ids = set()

        channels = [
            ('RULE_EXACT', self.channel_rule_exact),
            ('RULE_NAMING', self.channel_rule_naming),
            ('SEMANTIC', self.channel_semantic),
            ('REFERENCE', self.channel_reference),
        ]

        for name, func in channels:
            print(f"  执行通道: {name} ...")
            recs = func()
            print(f"    产出 {len(recs)} 条映射")
            for r in recs:
                mid = r['mapping_id']
                if mid not in seen_ids:
                    seen_ids.add(mid)
                    all_mappings.append(r)
                else:
                    # 已存在，保留置信度更高的
                    existing = next(m for m in all_mappings if m['mapping_id'] == mid)
                    if r['confidence'] > existing['confidence']:
                        existing.update(r)

        self.mappings = all_mappings
        return all_mappings


# ===================== 索引桥构建器 =====================

class DualIndexBridge:
    """双轨索引桥主类"""

    def __init__(self, truth_mirror_path: str, ima_path: str,
                 feishu_base_records: List[dict] = None,
                 output_dir: str = '.'):
        self.truth_loader = TruthKeyLoader(truth_mirror_path)
        self.asset_loader = AssetLoader(ima_path, feishu_base_records)
        self.engine = MatchEngine(self.truth_loader, self.asset_loader)
        self.output_dir = output_dir
        self.mappings: List[dict] = []
        self.truth_index: Dict[str, dict] = {}
        self.asset_index: Dict[str, dict] = {}

    def build(self) -> dict:
        """执行完整索引桥构建"""
        print("=" * 60)
        print("  双轨记忆索引桥构建启动")
        print(f"  时间: {now_iso()}")
        print(f"  DID: {DID} | {TRACE}")
        print("=" * 60)

        print(f"\n[1/5] 数据加载完成")
        print(f"  云端 truth_key: {len(self.truth_loader.truths)} 条")
        print(f"  本地 asset_id: {len(self.asset_loader.assets)} 条")

        print(f"\n[2/5] 执行多通道匹配...")
        self.mappings = self.engine.run_all_channels()
        print(f"  合并去重后: {len(self.mappings)} 条映射")

        print(f"\n[3/5] 构建双侧索引...")
        self._build_truth_index()
        self._build_asset_index()

        print(f"\n[4/5] 生成元数据与统计...")
        metadata = self._build_metadata()

        print(f"\n[5/5] 输出结果...")
        output_files = self._output(metadata)

        print("\n" + "=" * 60)
        print("  索引桥构建完成")
        print("=" * 60)
        print(f"  总映射数: {metadata['total_mappings']}")
        print(f"  通道分布: {json.dumps(metadata['match_channel_distribution'], ensure_ascii=False)}")
        print(f"  置信度分布: {json.dumps(metadata['confidence_distribution'], ensure_ascii=False)}")
        print(f"  输出文件: {output_files}")
        print(f"  确权: {TRACE} | {DID}")
        print("=" * 60)

        return {
            'metadata': metadata,
            'mappings': self.mappings,
            'truth_index': self.truth_index,
            'asset_index': self.asset_index,
            'output_files': output_files,
        }

    def _build_truth_index(self):
        for tk in self.truth_loader.truths.keys():
            linked = [m for m in self.mappings if m['truth_key'] == tk]
            self.truth_index[tk] = {
                'truth_key': tk,
                'category': self.truth_loader.truths[tk].get('category', ''),
                'node_id': self.truth_loader.truths[tk].get('node_id', ''),
                'value_hash': sha256_hex(str(self.truth_loader.truths[tk].get('value', ''))),
                'value_preview': self.truth_loader.get_value_preview(tk),
                'keyword_set': sorted(list(self.engine._get_truth_keywords(tk))),
                'linked_asset_count': len(linked),
                'linked_assets': [m['mapping_id'] for m in linked],
            }

    def _build_asset_index(self):
        for aid in self.asset_loader.assets.keys():
            linked = [m for m in self.mappings if m['asset_id'] == aid]
            a = self.asset_loader.assets[aid]
            self.asset_index[aid] = {
                'asset_id': aid,
                'source': a.get('source', ''),
                'asset_type': a.get('asset_type', ''),
                'title': a.get('title', ''),
                'sha256': a.get('sha256', ''),
                'keyword_set': sorted(list(self.engine._get_asset_keywords(aid))),
                'linked_truth_count': len(linked),
                'linked_truths': [m['mapping_id'] for m in linked],
            }

    def _build_metadata(self) -> dict:
        channel_dist = defaultdict(int)
        conf_dist = {'high(>=0.8)': 0, 'medium(0.6-0.8)': 0, 'low(<0.6)': 0}
        for m in self.mappings:
            channel_dist[m['match_channel']] += 1
            c = m['confidence']
            if c >= 0.8:
                conf_dist['high(>=0.8)'] += 1
            elif c >= 0.6:
                conf_dist['medium(0.6-0.8)'] += 1
            else:
                conf_dist['low(<0.6)'] += 1

        # 计算Merkle根（简化版：所有mapping_id的哈希链）
        all_ids = sorted([m['mapping_id'] for m in self.mappings])
        merkle_input = '|'.join(all_ids)
        merkle_root = sha256_hex(merkle_input, 64)

        return {
            'bridge_id': BRIDGE_ID,
            'version': '1.0.0',
            'did': DID,
            'trace_mark': TRACE,
            'total_truth_keys': len(self.truth_loader.truths),
            'total_asset_ids': len(self.asset_loader.assets),
            'total_mappings': len(self.mappings),
            'confirmed_mappings': 0,
            'pending_mappings': len(self.mappings),
            'rejected_mappings': 0,
            'match_channel_distribution': dict(channel_dist),
            'confidence_distribution': conf_dist,
            'last_full_sync': now_iso(),
            'merkle_root': merkle_root,
            'iron_rules': [
                'AAB双隔离：仅通过9120真值通道读取云端数据',
                '本地仿真→人工审核→才上云',
                '真值优先：冲突时以truth_key为准',
                '映射不可删除：只可标记REJECTED保留审计',
                '每次变更须Merkle快照+三端同步锁档',
            ],
        }

    def _output(self, metadata: dict) -> List[str]:
        os.makedirs(self.output_dir, exist_ok=True)
        files = []

        # 1. 映射表
        mappings_path = os.path.join(self.output_dir, 'mappings.json')
        with open(mappings_path, 'w', encoding='utf-8') as f:
            json.dump(self.mappings, f, ensure_ascii=False, indent=2)
        files.append(mappings_path)

        # 2. truth侧索引
        truth_index_path = os.path.join(self.output_dir, 'truth_side_index.json')
        with open(truth_index_path, 'w', encoding='utf-8') as f:
            json.dump(self.truth_index, f, ensure_ascii=False, indent=2)
        files.append(truth_index_path)

        # 3. asset侧索引
        asset_index_path = os.path.join(self.output_dir, 'asset_side_index.json')
        with open(asset_index_path, 'w', encoding='utf-8') as f:
            json.dump(self.asset_index, f, ensure_ascii=False, indent=2)
        files.append(asset_index_path)

        # 4. 元数据
        metadata_path = os.path.join(self.output_dir, 'bridge_metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        files.append(metadata_path)

        # 5. 对账报告（可读文本）
        report_path = os.path.join(self.output_dir, 'reconcile_report.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_report(metadata))
        files.append(report_path)

        return files

    def _generate_report(self, metadata: dict) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("  双轨记忆索引桥 - 对账报告")
        lines.append(f"  生成时间: {now_iso()}")
        lines.append(f"  DID: {DID} | {TRACE}")
        lines.append("=" * 60)
        lines.append("")
        lines.append("【数据规模】")
        lines.append(f"  云端 truth_key: {metadata['total_truth_keys']} 条")
        lines.append(f"  本地 asset_id: {metadata['total_asset_ids']} 条")
        lines.append(f"  映射总数: {metadata['total_mappings']} 条")
        lines.append("")
        lines.append("【通道分布】")
        for ch, cnt in metadata['match_channel_distribution'].items():
            lines.append(f"  {ch}: {cnt} 条")
        lines.append("")
        lines.append("【置信度分布】")
        for level, cnt in metadata['confidence_distribution'].items():
            lines.append(f"  {level}: {cnt} 条")
        lines.append("")
        lines.append("【高置信度映射 Top20 (>=0.8)】")
        high_conf = sorted([m for m in self.mappings if m['confidence'] >= 0.8],
                           key=lambda x: -x['confidence'])[:20]
        for i, m in enumerate(high_conf, 1):
            lines.append(f"  [{i}] {m['truth_key'][:45]}")
            lines.append(f"       ↔ {m['asset_id']} ({m['asset_source']})")
            lines.append(f"       通道: {m['match_channel']} | 置信度: {m['confidence']}")
            lines.append(f"       证据: {m['match_evidence'][:80]}")
        lines.append("")
        lines.append("【未匹配的truth_key (无任何映射)】")
        unmatched_tk = [tk for tk, idx in self.truth_index.items() if idx['linked_asset_count'] == 0]
        lines.append(f"  共 {len(unmatched_tk)} 条")
        for tk in unmatched_tk[:15]:
            cat = self.truth_index[tk]['category']
            lines.append(f"    - [{cat}] {tk[:55]}")
        lines.append("")
        lines.append("【未匹配的asset_id (无任何映射)】")
        unmatched_aid = [aid for aid, idx in self.asset_index.items() if idx['linked_truth_count'] == 0]
        lines.append(f"  共 {len(unmatched_aid)} 条")
        for aid in unmatched_aid[:15]:
            title = self.asset_index[aid]['title'][:40]
            lines.append(f"    - {aid} | {title}")
        lines.append("")
        lines.append("【Merkle根】")
        lines.append(f"  {metadata['merkle_root']}")
        lines.append("")
        lines.append("【铁律】")
        for rule in metadata['iron_rules']:
            lines.append(f"  - {rule}")
        lines.append("")
        lines.append("=" * 60)
        lines.append("  报告结束 | 本地仿真模式，待人工审核后上云")
        lines.append("=" * 60)
        return '\n'.join(lines)


# ===================== 主入口 =====================

if __name__ == '__main__':
    import sys

    # 默认路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    truth_mirror = os.path.join(base_dir, 'truth-mirror', 'truth-mirror-20260911-055658.json')
    ima_path = os.path.join(base_dir, 'IMA资产全量目录_20260911.json')
    output_dir = os.path.join(base_dir, 'dual_index_bridge', 'output')

    # 飞书Base资产记录（从飞书Base拉取的100条归档资产）
    feishu_records = []
    feishu_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'feishu_base_assets.json')
    if os.path.exists(feishu_path):
        with open(feishu_path, 'r', encoding='utf-8') as f:
            fb_data = json.load(f)
        feishu_records = fb_data.get('assets', [])
        print(f"已加载飞书Base资产: {len(feishu_records)} 条")

    bridge = DualIndexBridge(
        truth_mirror_path=truth_mirror,
        ima_path=ima_path,
        feishu_base_records=feishu_records,
        output_dir=output_dir,
    )
    result = bridge.build()
    print(f"\n完成！映射文件位于: {output_dir}")
