#!/bin/bash
echo "🚀 模型下载到 Network Volume 专用脚本"
echo "目标路径: /runpod-volume/my_stable_models/"

MODEL_DIR="/runpod-volume/my_stable_models"
mkdir -p $MODEL_DIR/diffusion_models
mkdir -p $MODEL_DIR/vae
mkdir -p $MODEL_DIR/text_encoders
mkdir -p $MODEL_DIR/clip_vision
mkdir -p $MODEL_DIR/loras

echo "📥 [1/7] 下载 VAE (350MB)..."
wget -q --show-progress -nc -O $MODEL_DIR/vae/wan_2.1_vae.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors?download=true"

echo "📥 [2/7] 下载 CLIP Vision (1.7GB)..."
wget -q --show-progress -nc -O $MODEL_DIR/clip_vision/clip_vision_h.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors?download=true"

echo "📥 [3/7] 下载 Text Encoder (4.9GB)..."
wget -q --show-progress -nc -O $MODEL_DIR/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors?download=true"

echo "📥 [4/7] 下载 I2V High Noise 14B (14GB)..."
wget -q --show-progress -nc -O $MODEL_DIR/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"

echo "📥 [5/7] 下载 I2V Low Noise 14B (14GB)..."
wget -q --show-progress -nc -O $MODEL_DIR/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors \
  "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"

echo "📥 [6/7] 下载 NSFW FastMove V2 High (15GB)..."
curl -# -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36" \
  -H "Authorization: Bearer 95f1a54dbe965d73177e8759bd55b6ea" \
  "https://civitai.com/api/download/models/2477539" \
  -o $MODEL_DIR/diffusion_models/WAN2.2-NSFW-FastMove-V2-H.safetensors

echo "📥 [7/7] 下载 NSFW FastMove V2 Low (15GB)..."
curl -# -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36" \
  -H "Authorization: Bearer 95f1a54dbe965d73177e8759bd55b6ea" \
  "https://civitai.com/api/download/models/2477548" \
  -o $MODEL_DIR/diffusion_models/WAN2.2-NSFW-FastMove-V2-L.safetensors

echo ""
echo "🔍 最终验证 - 检查所有文件："
echo "=== diffusion_models ==="
ls -lh $MODEL_DIR/diffusion_models/
echo "=== vae ==="
ls -lh $MODEL_DIR/vae/
echo "=== text_encoders ==="
ls -lh $MODEL_DIR/text_encoders/
echo "=== clip_vision ==="
ls -lh $MODEL_DIR/clip_vision/
echo ""
echo "✅ 全部下载完毕！现在可以 Terminate 这台 Pod 了，模型安全存储在 Network Volume 上！"
