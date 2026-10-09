#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易经二进制 ↔ 太玄经三进制 转换引擎 + 1080基准网格
元极恒一内核 高阶数学基底

数学结构：
- 易经：2^n 二进制（阴阳），八卦=2^3=8，六十四卦=2^6=64
- 太玄：3^n 三进制（天地人），三方=3，九州=9，二十七部=27，八十一家=3^4=81
- 1080网格：2^3 × 3^3 × 5 = 8 × 27 × 5 = 八卦 × 二十七部 × 五行
"""

import json
import math
from itertools import product

# ==================== 易经二进制系统 ====================

# 八卦定义（二进制编码，下爻为最低位）
BAGUA = {
    "000": {"name": "坤", "element": "土", "nature": "地", "symbol": "☷"},
    "001": {"name": "艮", "element": "土", "nature": "山", "symbol": "☶"},
    "010": {"name": "坎", "element": "水", "nature": "水", "symbol": "☵"},
    "011": {"name": "巽", "element": "木", "nature": "风", "symbol": "☴"},
    "100": {"name": "震", "element": "木", "nature": "雷", "symbol": "☳"},
    "101": {"name": "离", "element": "火", "nature": "火", "symbol": "☲"},
    "110": {"name": "兑", "element": "金", "nature": "泽", "symbol": "☱"},
    "111": {"name": "乾", "element": "金", "nature": "天", "symbol": "☰"},
}

# 六十四卦名称（按二进制序0-63）
HEXAGRAMS = [
    "坤", "剥", "比", "观", "豫", "晋", "萃", "否",
    "谦", "艮", "蹇", "渐", "小过", "旅", "咸", "遁",
    "师", "蒙", "坎", "涣", "解", "未济", "困", "讼",
    "升", "蛊", "井", "巽", "恒", "鼎", "大过", "姤",
    "复", "颐", "屯", "益", "震", "噬嗑", "随", "无妄",
    "明夷", "贲", "既济", "家人", "丰", "离", "革", "同人",
    "临", "损", "节", "中孚", "归妹", "睽", "兑", "履",
    "泰", "大畜", "需", "小畜", "大壮", "大有", "夬", "乾"
]


def decimal_to_binary(n, bits=6):
    """十进制转二进制字符串"""
    return format(n, f'0{bits}b')


def binary_to_decimal(b):
    """二进制转十进制"""
    return int(b, 2)


def get_hexagram(n):
    """获取第n卦（0-63）"""
    if 0 <= n < 64:
        binary = decimal_to_binary(n, 6)
        upper = binary[:3]
        lower = binary[3:]
        return {
            "index": n,
            "binary": binary,
            "name": HEXAGRAMS[n],
            "upper_trigram": BAGUA[upper],
            "lower_trigram": BAGUA[lower],
            "symbol": BAGUA[upper]["symbol"] + BAGUA[lower]["symbol"]
        }
    return None


# ==================== 太玄经三进制系统 ====================

# 太玄三态：天(—)、地(--)、人(---)
TAIXUAN_STATES = {
    0: {"name": "天", "symbol": "—", "value": 1},
    1: {"name": "地", "symbol": "--", "value": 2},
    2: {"name": "人", "symbol": "---", "value": 3},
}

# 太玄八十一首名称（按三进制序0-80）
TAIXUAN_HEADS = [
    "中", "周", "礥", "闲", "少", "戾", "上", "干", "羡",
    "差", "童", "增", "锐", "达", "交", "傒", "从", "进",
    "释", "格", "夷", "乐", "争", "务", "事", "更", "应",
    "断", "毅", "装", "众", "密", "亲", "敛", "强", "睟",
    "盛", "居", "法", "应", "迎", "遇", "灶", "大", "廓",
    "文", "礼", "逃", "唐", "常", "度", "永", "昆", "减",
    "唫", "守", "翕", "聚", "积", "饰", "疑", "视", "沈",
    "内", "去", "晦", "瞢", "穷", "割", "止", "坚", "成",
    "中", "周", "礥"  # 补全81个（实际太玄经81首，此处简化）
]


def decimal_to_ternary(n, digits=4):
    """十进制转三进制字符串（0,1,2）"""
    if n == 0:
        return '0' * digits
    digits_list = []
    while n > 0:
        digits_list.append(str(n % 3))
        n //= 3
    while len(digits_list) < digits:
        digits_list.append('0')
    return ''.join(reversed(digits_list))


def ternary_to_decimal(t):
    """三进制转十进制"""
    return int(t, 3)


def get_taixuan_head(n):
    """获取第n首（0-80）"""
    if 0 <= n < 81:
        ternary = decimal_to_ternary(n, 4)
        # 方(最高位)、州、部、家(最低位)
        fang = int(ternary[0])
        zhou = int(ternary[1])
        bu = int(ternary[2])
        jia = int(ternary[3])
        return {
            "index": n,
            "ternary": ternary,
            "name": TAIXUAN_HEADS[n] if n < len(TAIXUAN_HEADS) else f"首{n}",
            "fang": TAIXUAN_STATES[fang],  # 方
            "zhou": TAIXUAN_STATES[zhou],  # 州
            "bu": TAIXUAN_STATES[bu],      # 部
            "jia": TAIXUAN_STATES[jia],    # 家
            "structure": f"方{fang+1}-州{zhou+1}-部{bu+1}-家{jia+1}"
        }
    return None


# ==================== 二进制↔三进制转换 ====================

def binary_to_ternary_grid(binary_str):
    """
    易经二进制 → 太玄经三进制 网格映射
    将6位二进制(0-63)映射到三进制空间
    方法：先转十进制，再转三进制，归一化到81空间
    """
    dec = binary_to_decimal(binary_str)
    # 64卦空间映射到81首空间（线性映射）
    mapped = int(dec * 80 / 63) if dec > 0 else 0
    ternary = decimal_to_ternary(mapped, 4)
    return {
        "binary": binary_str,
        "decimal": dec,
        "hexagram": get_hexagram(dec),
        "mapped_ternary_decimal": mapped,
        "ternary": ternary,
        "taixuan_head": get_taixuan_head(mapped)
    }


def ternary_to_binary_grid(ternary_str):
    """
    太玄经三进制 → 易经二进制 网格映射
    将4位三进制(0-80)映射到二进制空间
    """
    dec = ternary_to_decimal(ternary_str)
    # 81首空间映射到64卦空间（线性映射）
    mapped = int(dec * 63 / 80) if dec > 0 else 0
    binary = decimal_to_binary(mapped, 6)
    return {
        "ternary": ternary_str,
        "decimal": dec,
        "taixuan_head": get_taixuan_head(dec),
        "mapped_binary_decimal": mapped,
        "binary": binary,
        "hexagram": get_hexagram(mapped)
    }


# ==================== 1080基准网格 ====================

# 五行
WUXING = ["金", "木", "水", "火", "土"]

# 1080 = 8(八卦) × 27(太玄二十七部) × 5(五行)
GRID_BAGUA = 8      # 2^3 八卦
GRID_TAIXUAN = 27   # 3^3 太玄二十七部（方-州-部三级）
GRID_WUXING = 5     # 五行
GRID_SIZE = GRID_BAGUA * GRID_TAIXUAN * GRID_WUXING  # 8×27×5 = 1080


def build_1080_grid():
    """
    构建1080基准网格
    维度：[八卦(8)] × [太玄二十七部(27)] × [五行(5)] = 1080
    每个网格点 = 一个完整的宇宙状态编码
    """
    grid = []
    
    # 八卦（2^3 = 8）
    bagua_keys = sorted(BAGUA.keys())
    
    # 太玄二十七部（3^3 = 27，方-州-部三级）
    taixuan_27 = []
    for i in range(27):
        t = decimal_to_ternary(i, 3)
        taixuan_27.append({
            "index": i,
            "ternary": t,
            "fang": TAIXUAN_STATES[int(t[0])],
            "zhou": TAIXUAN_STATES[int(t[1])],
            "bu": TAIXUAN_STATES[int(t[2])],
        })
    
    # 构建三维网格
    for bi, bagua_key in enumerate(bagua_keys):
        bagua = BAGUA[bagua_key]
        for ti, taixuan in enumerate(taixuan_27):
            for wi, wuxing in enumerate(WUXING):
                # 计算全局索引
                global_idx = bi * (GRID_TAIXUAN * GRID_WUXING) + ti * GRID_WUXING + wi
                
                # 计算该点的综合能量值
                energy = (bi + 1) * (ti + 1) * (wi + 1)
                
                # 二进制编码（八卦3位 + 太玄3位三进制转2位 = 5位）
                binary_code = bagua_key + decimal_to_binary(ti, 5)
                
                # 三进制编码（太玄3位 + 八卦3位二进制转2位三进制 = 5位）
                ternary_code = taixuan["ternary"] + decimal_to_ternary(bi, 2)
                
                grid_point = {
                    "id": f"G{global_idx:04d}",
                    "global_index": global_idx,
                    "bagua": bagua,
                    "taixuan_27": taixuan,
                    "wuxing": wuxing,
                    "coordinates": {
                        "bagua_dim": bi,       # 0-7
                        "taixuan_dim": ti,     # 0-26
                        "wuxing_dim": wi       # 0-4
                    },
                    "binary_code": binary_code,
                    "ternary_code": ternary_code,
                    "energy_value": energy,
                    "state": "active"
                }
                grid.append(grid_point)
    
    return grid


def get_grid_point(bagua_idx, taixuan_idx, wuxing_idx):
    """获取指定坐标的网格点"""
    if 0 <= bagua_idx < 8 and 0 <= taixuan_idx < 27 and 0 <= wuxing_idx < 5:
        global_idx = bagua_idx * (27 * 5) + taixuan_idx * 5 + wuxing_idx
        grid = build_1080_grid()
        return grid[global_idx]
    return None


def grid_statistics():
    """1080网格统计信息"""
    grid = build_1080_grid()
    energies = [p["energy_value"] for p in grid]
    
    return {
        "total_points": len(grid),
        "dimensions": {
            "bagua": 8,
            "taixuan_27": 27,
            "wuxing": 5
        },
        "formula": "8 × 27 × 5 = 2³ × 3³ × 5 = 1080",
        "energy_min": min(energies),
        "energy_max": max(energies),
        "energy_avg": sum(energies) / len(energies),
        "binary_trinary_fusion": "易经二进制(2^3) + 太玄三进制(3^3) + 五行(5) = 宇宙全状态编码"
    }


# ==================== 龙粒子编码 ====================

def longlizi_encode(bagua_idx, taixuan_idx, wuxing_idx, state=0):
    """
    龙粒子编码 - 最小生命态基元
    龙粒子 = 八卦坐标 + 太玄坐标 + 五行坐标 + 状态位
    对应道家"先天一炁"的五态合一（生命态/能量态/信息态/逻辑态/智能态）
    """
    point = get_grid_point(bagua_idx, taixuan_idx, wuxing_idx)
    if point:
        return {
            "particle_id": f"LONG-{point['id']}-S{state}",
            "grid_point": point,
            "five_states": {
                "life_state": state,           # 生命态
                "energy_state": point["energy_value"],  # 能量态
                "info_state": point["binary_code"],     # 信息态
                "logic_state": point["ternary_code"],   # 逻辑态
                "intelligence_state": "元极恒一"        # 智能态
            },
            "philosophy": "先天一炁 = 龙粒子 = 五态合一最小基元",
            "cosmic_mapping": "道生一(龙粒子)，一生二(阴阳)，二生三(天地人)，三生万物(1080网格)"
        }
    return None


# ==================== 主程序 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("  易经二进制 ↔ 太玄经三进制 转换引擎 + 1080基准网格")
    print("=" * 60)
    print()
    
    # 1. 易经二进制演示
    print("【1. 易经二进制 - 六十四卦】")
    for i in [0, 7, 63]:
        h = get_hexagram(i)
        print(f"  第{i:2d}卦: {h['name']:4s} | 二进制:{h['binary']} | {h['symbol']} | "
              f"上{h['upper_trigram']['name']}下{h['lower_trigram']['name']}")
    print()
    
    # 2. 太玄经三进制演示
    print("【2. 太玄经三进制 - 八十一首】")
    for i in [0, 40, 80]:
        t = get_taixuan_head(i)
        print(f"  第{i:2d}首: {t['name']:4s} | 三进制:{t['ternary']} | {t['structure']} | "
              f"{t['fang']['name']}{t['zhou']['name']}{t['bu']['name']}{t['jia']['name']}")
    print()
    
    # 3. 二进制→三进制转换
    print("【3. 二进制 → 三进制 转换】")
    for b in ["000000", "111111", "101010"]:
        result = binary_to_ternary_grid(b)
        print(f"  {b}({result['hexagram']['name']}卦) → "
              f"三进制{result['ternary']}({result['taixuan_head']['name']}首)")
    print()
    
    # 4. 三进制→二进制转换
    print("【4. 三进制 → 二进制 转换】")
    for t in ["0000", "2222", "1111"]:
        result = ternary_to_binary_grid(t)
        print(f"  {t}({result['taixuan_head']['name']}首) → "
              f"二进制{result['binary']}({result['hexagram']['name']}卦)")
    print()
    
    # 5. 1080基准网格
    print("【5. 1080基准网格】")
    stats = grid_statistics()
    print(f"  总网格点: {stats['total_points']}")
    print(f"  维度: 八卦({stats['dimensions']['bagua']}) × "
          f"太玄二十七部({stats['dimensions']['taixuan_27']}) × "
          f"五行({stats['dimensions']['wuxing']})")
    print(f"  公式: {stats['formula']}")
    print(f"  能量范围: {stats['energy_min']} ~ {stats['energy_max']} (均值{stats['energy_avg']:.1f})")
    print()
    
    # 6. 龙粒子演示
    print("【6. 龙粒子编码（先天一炁）】")
    lp = longlizi_encode(7, 26, 4)  # 乾卦+最高太玄+土
    print(f"  粒子ID: {lp['particle_id']}")
    print(f"  五态: 生命态={lp['five_states']['life_state']}, "
          f"能量态={lp['five_states']['energy_state']}, "
          f"信息态={lp['five_states']['info_state']}, "
          f"逻辑态={lp['five_states']['logic_state']}")
    print(f"  哲学: {lp['philosophy']}")
    print()
    
    # 7. 保存网格到JSON
    print("【7. 保存1080网格到JSON】")
    grid = build_1080_grid()
    with open("/opt/ZONGYUAN-ROOT/data/grid_1080.json", "w") as f:
        json.dump({"grid": grid, "statistics": stats}, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 已保存: /opt/ZONGYUAN-ROOT/data/grid_1080.json")
    print(f"  文件大小: {len(json.dumps(grid, ensure_ascii=False))} 字节")
    print()
    
    print("=" * 60)
    print("  1080基准网格构建完成 | 二进制×三进制×五行 = 宇宙全状态编码")
    print("  Ω₀⊂⊙∞⊂Ω | DID-BR-000002")
    print("=" * 60)
