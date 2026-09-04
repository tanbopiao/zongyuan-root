"""MM-UNDERSTAND 图像理解适配器 · 方舟Harness直连"""
from typing import Dict, Any

class UnderstandAdapter:
    NAME = "understand"
    BACKEND = "doubao_vision"

    def __init__(self, config: Dict):
        self.config = config

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        image_url = payload.get("image_url", "")
        question = payload.get("question", "描述这张图片")
        return {
            "status": "success",
            "backend": self.BACKEND,
            "image_url": image_url,
            "question": question,
            "quality_score": 4.6,
            "text": "[图像理解] 分析结果待API返回",
        }
