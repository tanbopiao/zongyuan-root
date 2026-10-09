#!/usr/bin/env python3
"""
D5-T4 跨平台统一资产视图执行器 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
功能：四平台统一资产清单、跨平台去重、关联、统一锁档、M1-M9元类跨平台统一
"""
import json
import hashlib
import time
from typing import Dict, List, Tuple, Set
from collections import defaultdict

class UnifiedAssetExecutor:
    def __init__(self, manifest_path: str):
        self.manifest_path = manifest_path
        self.manifest = json.load(open(manifest_path))
        self.assets = self.manifest.get('assets', {})
        self.platforms = ['feishu_drive', 'feishu_wiki', 'feishu_base', 'local']
        self.meta_classes = ['M1','M2','M3','M4','M5','M6','M7','M8','M9']
        
    def _sha256(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def analyze_platform_distribution(self) -> Dict:
        """分析资产平台分布"""
        platform_count = defaultdict(int)
        platform_meta = defaultdict(lambda: defaultdict(int))
        
        for asset_id, asset in self.assets.items():
            platform = asset.get('platform', 'unknown')
            meta_class = asset.get('meta_class', 'UNCLASSIFIED')
            platform_count[platform] += 1
            platform_meta[platform][meta_class] += 1
        
        return {
            'total': len(self.assets),
            'platform_distribution': dict(platform_count),
            'platform_meta_distribution': {k: dict(v) for k, v in platform_meta.items()}
        }
    
    def detect_duplicates(self) -> Dict:
        """跨平台去重检测（基于内容哈希+标题相似度）"""
        hash_groups = defaultdict(list)
        title_groups = defaultdict(list)
        
        for asset_id, asset in self.assets.items():
            content_hash = asset.get('content_hash', '')
            title = asset.get('name', '').strip().lower()
            
            if len(content_hash) == 64:
                hash_groups[content_hash].append(asset_id)
            if title:
                title_groups[title].append(asset_id)
        
        # 精确重复（相同内容哈希）
        exact_duplicates = {h: ids for h, ids in hash_groups.items() if len(ids) > 1}
        
        # 疑似重复（相同标题）
        potential_duplicates = {t: ids for t, ids in title_groups.items() if len(ids) > 1}
        
        return {
            'exact_duplicate_groups': len(exact_duplicates),
            'exact_duplicate_assets': sum(len(v) for v in exact_duplicates.values()),
            'potential_duplicate_groups': len(potential_duplicates),
            'potential_duplicate_assets': sum(len(v) for v in potential_duplicates.values()),
            'exact_duplicates': dict(list(exact_duplicates.items())[:10]),
            'potential_duplicates': dict(list(potential_duplicates.items())[:10])
        }
    
    def unify_meta_classes(self) -> Dict:
        """M1-M9元类跨平台统一补全"""
        unclassified = []
        auto_classified = 0
        
        # 元类推断规则
        def infer_meta_class(asset: dict) -> str:
            asset_type = asset.get('asset_type', '').lower()
            name = asset.get('name', '').lower()
            
            if any(k in asset_type for k in ['algorithm', 'arch', 'engine', 'operator']):
                return 'M1'
            elif any(k in asset_type for k in ['data', 'model', 'schema']):
                return 'M2'
            elif any(k in asset_type for k in ['api', 'protocol', 'interface']):
                return 'M3'
            elif any(k in asset_type for k in ['theory', 'whitepaper', 'philosophy']):
                return 'M4'
            elif any(k in asset_type for k in ['product', 'application', 'pipeline']):
                return 'M5'
            elif any(k in asset_type for k in ['ops', 'governance', 'monitor']):
                return 'M6'
            elif any(k in asset_type for k in ['security', 'compliance', 'legal']):
                return 'M7'
            elif any(k in asset_type for k in ['business', 'commercial', 'workflow']):
                return 'M8'
            elif any(k in asset_type for k in ['meta', 'root', 'law', 'kernel']):
                return 'M9'
            return 'UNCLASSIFIED'
        
        for asset_id, asset in self.assets.items():
            current = asset.get('meta_class', 'UNCLASSIFIED')
            if current == 'UNCLASSIFIED' or not current:
                inferred = infer_meta_class(asset)
                if inferred != 'UNCLASSIFIED':
                    asset['meta_class'] = inferred
                    asset['meta_class_confidence'] = 0.7
                    asset['meta_class_source'] = 'auto_inferred'
                    auto_classified += 1
                else:
                    unclassified.append(asset_id)
        
        # 统计元类分布
        meta_dist = defaultdict(int)
        for asset in self.assets.values():
            meta_dist[asset.get('meta_class', 'UNCLASSIFIED')] += 1
        
        return {
            'auto_classified': auto_classified,
            'remaining_unclassified': len(unclassified),
            'meta_class_distribution': dict(sorted(meta_dist.items())),
            'unclassified_samples': unclassified[:10]
        }
    
    def build_cross_platform_links(self) -> Dict:
        """构建跨平台资产关联"""
        links = []
        # 基于相同内容哈希建立关联
        hash_map = defaultdict(list)
        for asset_id, asset in self.assets.items():
            h = asset.get('content_hash', '')
            if len(h) == 64:
                hash_map[h].append(asset_id)
        
        for h, ids in hash_map.items():
            if len(ids) > 1:
                links.append({
                    'link_type': 'same_content',
                    'content_hash': h,
                    'assets': ids,
                    'confidence': 1.0
                })
        
        return {
            'total_links': len(links),
            'link_samples': links[:10]
        }
    
    def execute(self) -> Dict:
        """执行D5-T4全流程"""
        start_time = time.time()
        
        # 1. 平台分布分析
        distribution = self.analyze_platform_distribution()
        
        # 2. 去重检测
        duplicates = self.detect_duplicates()
        
        # 3. 元类统一补全
        meta_unify = self.unify_meta_classes()
        
        # 4. 跨平台关联
        links = self.build_cross_platform_links()
        
        # 保存更新后的清单
        json.dump(self.manifest, open(self.manifest_path, 'w'), ensure_ascii=False, indent=2)
        
        elapsed = time.time() - start_time
        
        return {
            'task_id': 'D5-T4',
            'task_name': '跨平台统一资产视图',
            'status': 'COMPLETED',
            'execution_time': round(elapsed, 2),
            'distribution': distribution,
            'duplicates': duplicates,
            'meta_unify': meta_unify,
            'cross_platform_links': links,
            'DID': 'DID-BR-000002',
            'trace': 'Ω₀⊂⊙∞⊂Ω'
        }

if __name__ == '__main__':
    executor = UnifiedAssetExecutor('/sandboxdata/workspace/file/UNIFIED_GLOBAL_LOCK_MANIFEST.json')
    result = executor.execute()
    print(json.dumps(result, ensure_ascii=False, indent=2))
