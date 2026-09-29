#!/usr/bin/env python3
"""测试视觉模型图片质检能力 - 检测多手/肢体扭曲等AI artifacts"""

import requests
import base64
import json
import os
import sys

# 智谱API配置
ZHIPU_API_KEY = "1dfafcccce4e483287fe39bcdea7691c.78z9iYwdDTRiquIk"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

# 豆包API配置
DOUBAO_API_KEY = "6f8c69a7-d613-41d6-9db3-5c929a9a49e4"
DOUBAO_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DOUBAO_ENDPOINT = "ep-m-20260325114252-xcd64"

def encode_image(image_path):
    """将图片编码为base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_zhipu_vision(image_path):
    """测试智谱GLM-4V-Flash视觉模型"""
    print("=" * 60)
    print("【测试智谱GLM-4V-Flash】")
    print("=" * 60)
    
    image_base64 = encode_image(image_path)
    
    prompt = """你是AI图片质量检测专家。请检测这张图片是否存在以下AI artifacts问题：
1. 多个手/多余手指（正常人类只有2只手，每只手5根手指）
2. 肢体扭曲/关节异常
3. 面部崩坏/五官不对称
4. 衣物穿模/纹理错误
5. 背景不合理/透视错误

请按以下JSON格式输出（不要输出其他内容）：
{
  "quality_score": 0-100,
  "has_issues": true/false,
  "issues": ["问题1", "问题2"],
  "issue_locations": ["问题位置描述"],
  "severity": "low/medium/high/critical",
  "pass": true/false
}"""

    try:
        response = requests.post(
            f"{ZHIPU_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {ZHIPU_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "glm-4v-flash",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.1
            },
            timeout=30
        )
        
        result = response.json()
        print(f"  HTTP状态: {response.status_code}")
        
        if "choices" in result:
            content = result["choices"][0]["message"]["content"]
            print(f"  模型回复:\n{content}")
            
            # 尝试解析JSON
            try:
                # 提取JSON部分
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    quality_data = json.loads(content[json_start:json_end])
                    print(f"\n  解析结果:")
                    print(f"    质量分: {quality_data.get('quality_score')}")
                    print(f"    有问题: {quality_data.get('has_issues')}")
                    print(f"    问题列表: {quality_data.get('issues')}")
                    print(f"    严重程度: {quality_data.get('severity')}")
                    print(f"    是否通过: {quality_data.get('pass')}")
            except Exception as e:
                print(f"  JSON解析失败: {e}")
        else:
            print(f"  错误: {result}")
            
    except Exception as e:
        print(f"  请求失败: {e}")

def test_doubao_vision(image_path):
    """测试豆包视觉模型"""
    print("\n" + "=" * 60)
    print("【测试豆包视觉模型】")
    print("=" * 60)
    
    image_base64 = encode_image(image_path)
    
    prompt = """你是AI图片质量检测专家。请检测这张图片是否存在以下AI artifacts问题：
1. 多个手/多余手指
2. 肢体扭曲/关节异常
3. 面部崩坏/五官不对称
4. 衣物穿模/纹理错误

请输出：质量分(0-100)、是否有问题、问题列表、是否通过(70分以上通过)"""

    try:
        response = requests.post(
            f"{DOUBAO_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DOUBAO_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": DOUBAO_ENDPOINT,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000
            },
            timeout=30
        )
        
        result = response.json()
        print(f"  HTTP状态: {response.status_code}")
        
        if "choices" in result:
            content = result["choices"][0]["message"]["content"]
            print(f"  模型回复:\n{content}")
        else:
            print(f"  错误: {result}")
            
    except Exception as e:
        print(f"  请求失败: {e}")

if __name__ == "__main__":
    # 测试图片路径
    test_image = "/www/wwwroot/huodouai.com/drama/keyframes/ep01/S01-005_玄女战争形态降临.jpg"
    
    if not os.path.exists(test_image):
        print(f"测试图片不存在: {test_image}")
        # 尝试其他图片
        test_image = "/www/wwwroot/huodouai.com/drama/gallery/keyframes/jiutian_xuannv_keyframe_01_fullbody.png"
        if not os.path.exists(test_image):
            print("找不到测试图片")
            sys.exit(1)
    
    print(f"测试图片: {test_image}")
    print(f"图片大小: {os.path.getsize(test_image) / 1024:.1f}KB")
    print()
    
    # 测试智谱视觉模型
    test_zhipu_vision(test_image)
    
    # 测试豆包视觉模型
    test_doubao_vision(test_image)
