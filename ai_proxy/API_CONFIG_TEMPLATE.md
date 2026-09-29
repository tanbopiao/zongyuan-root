# ZONGYUAN-ROOT 真实API配置模板
# 填入对应endpoint后，AI Proxy自动启用真实生成

## 火山方舟（推荐）
# 控制台: https://console.volcengine.com/ark
# 1. 创建推理接入点，选择模型:
#    - 图片生成: doubao-seedream-3-0-t2i-250415 (Seedream)
#    - 视频生成: doubao-seedance-1-0-pro-250528 (Seedance)
# 2. 获取endpoint ID (ep-xxxxxxxx格式)
# 3. 填入下方:

ARK_SEEDREAM_ENDPOINT=ep-待填写        # Seedream图片生成
ARK_SEEDANCE_ENDPOINT=ep-待填写        # Seedance视频生成
ARK_API_KEY=6f8c69a7-d613-41d6-9db3-5c929a9a49e4  # 已有，文本模型同Key

## 可灵（备选）
# 控制台: https://platform.klingai.com/
KLING_API_KEY=待填写
KLING_SECRET_KEY=待填写

## 配置后验证
# curl -X POST http://127.0.0.1:8021/image/generate -d '{"prompt":"测试","provider":"seedream"}'
# curl -X POST http://127.0.0.1:8021/video/generate -d '{"prompt":"测试","provider":"seedance"}'
