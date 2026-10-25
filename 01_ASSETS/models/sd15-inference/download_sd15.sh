#!/bin/bash
BASE="https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main"
DEST="/home/user/Doubao/models/sd15"

echo "[$(date)] 开始下载SD1.5完整权重..."

# 1. UNet (~3.4GB)
echo "[$(date)] 1/4 UNet diffusion_pytorch_model.bin (~3.4GB)"
curl -sL --retry 3 -o "$DEST/unet/diffusion_pytorch_model.bin" "$BASE/unet/diffusion_pytorch_model.bin" && echo "  ✅ UNet完成"

# 2. VAE (~320MB)
echo "[$(date)] 2/4 VAE diffusion_pytorch_model.bin (~320MB)"
curl -sL --retry 3 -o "$DEST/vae/diffusion_pytorch_model.bin" "$BASE/vae/diffusion_pytorch_model.bin" && echo "  ✅ VAE完成"

# 3. Text Encoder (~492MB)
echo "[$(date)] 3/4 text_encoder pytorch_model.bin (~492MB)"
curl -sL --retry 3 -o "$DEST/text_encoder/pytorch_model.bin" "$BASE/text_encoder/pytorch_model.bin" && echo "  ✅ TextEncoder完成"

# 4. Tokenizer文件
echo "[$(date)] 4/4 tokenizer文件"
curl -sL --retry 3 -o "$DEST/tokenizer/vocab.json" "$BASE/tokenizer/vocab.json"
curl -sL --retry 3 -o "$DEST/tokenizer/merges.txt" "$BASE/tokenizer/merges.txt"
curl -sL --retry 3 -o "$DEST/tokenizer/special_tokens_map.json" "$BASE/tokenizer/special_tokens_map.json"
curl -sL --retry 3 -o "$DEST/model_index.json" "$BASE/model_index.json"
echo "  ✅ Tokenizer完成"

echo ""
echo "[$(date)] 全部下载完成！"
du -sh "$DEST"
echo "DONE"
