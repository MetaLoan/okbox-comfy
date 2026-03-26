#!/bin/bash
# ============================================================
# 🚀 Wan2.2 Serverless 模型一键部署脚本
# ============================================================
# 用法: bash setup_volume.sh
#
# 功能:
#   1. 创建 Serverless 需要的目录结构
#   2. 下载官方 Wan2.2 I2V 模型（Comfy-Org 格式）
#   3. 下载 LoRA 文件
#   4. 同步 lora_style_registry.json
# ============================================================

set -e

BASE="/workspace/my_stable_models"
REGISTRY_URL="https://raw.githubusercontent.com/MetaLoan/okbox-comfy/main/lora_style_registry.json"
COMFY_ORG="https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_repackaged/resolve/main/split_files"

echo "============================================================"
echo "🚀 Wan2.2 Serverless Volume 部署"
echo "============================================================"
echo "Volume 路径: ${BASE}"
df -h /workspace | tail -1
echo "============================================================"

# =================== Step 1: 创建目录 ===================
echo ""
echo "[Step 1/4] 创建目录结构..."
mkdir -p "${BASE}/diffusion_models"
mkdir -p "${BASE}/vae"
mkdir -p "${BASE}/text_encoders"
mkdir -p "${BASE}/clip_vision"
mkdir -p "${BASE}/loras"
echo "  ✅ 目录创建完成"

# =================== Step 2: 下载模型 ===================
echo ""
echo "[Step 2/4] 下载 Wan2.2 官方模型..."

download_if_missing() {
    local path="$1"
    local url="$2"
    local name=$(basename "$path")
    if [ -f "$path" ] && [ $(stat -f%z "$path" 2>/dev/null || stat -c%s "$path" 2>/dev/null) -gt 1000000 ]; then
        echo "  ✅ 已存在，跳过: ${name}"
    else
        echo "  ⬇️  下载: ${name}..."
        wget -q --show-progress -O "$path" "$url"
        echo "  ✅ ${name} 完成 ($(ls -lh $path | awk '{print $5}'))"
    fi
}

# DiT 模型（核心，各 ~14GB）
download_if_missing \
    "${BASE}/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors" \
    "${COMFY_ORG}/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"

download_if_missing \
    "${BASE}/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors" \
    "${COMFY_ORG}/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"

# VAE（~254MB）
download_if_missing \
    "${BASE}/vae/wan_2.1_vae.safetensors" \
    "${COMFY_ORG}/vae/wan_2.1_vae.safetensors"

# CLIP Text Encoder（~5GB）
download_if_missing \
    "${BASE}/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
    "${COMFY_ORG}/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"

# CLIP Vision（~3.3GB）
download_if_missing \
    "${BASE}/clip_vision/clip_vision_h.safetensors" \
    "${COMFY_ORG}/clip_vision/clip_vision_h.safetensors"

echo "  ✅ 所有基础模型下载完成"

# =================== Step 3: 下载 LoRA ===================
echo ""
echo "[Step 3/4] 下载 LoRA 文件..."

# CivitAI Anal Missionary I2V LoRA
download_if_missing \
    "${BASE}/loras/analMissionary_i2v.safetensors" \
    "https://civitai.com/api/download/models/1700298?token=95f1a54dbe965d73177e8759bd55b6ea"

# 自训练 LoRA（如果 R2 上有的话）
download_if_missing \
    "${BASE}/loras/analgirl_low.safetensors" \
    "https://vcdn.sprize.ai/loras/analgirl_low.safetensors"

download_if_missing \
    "${BASE}/loras/analgirl_high.safetensors" \
    "https://vcdn.sprize.ai/loras/analgirl_high.safetensors"

echo "  ✅ LoRA 下载完成"

# =================== Step 4: 同步 Registry ===================
echo ""
echo "[Step 4/4] 同步 LoRA 注册表 & 模型路径配置..."

# 同步 lora_style_registry.json
wget -q -O "${BASE}/lora_style_registry.json" "${REGISTRY_URL}"
echo "  ✅ Registry 已更新"

# 同步 extra_model_paths.yaml（支持两种安装路径）
YAML_URL="https://raw.githubusercontent.com/MetaLoan/okbox-comfy/test2/doc/extra_model_paths.yaml"
for COMFY_PATH in "/workspace/ComfyUI" "/workspace/runpod-slim/ComfyUI"; do
    if [ -d "$COMFY_PATH" ]; then
        wget -q -O "${COMFY_PATH}/extra_model_paths.yaml" "$YAML_URL"
        echo "  ✅ extra_model_paths.yaml → ${COMFY_PATH}"
    fi
done

cat "${BASE}/lora_style_registry.json" | python3 -c "
import json, sys
reg = json.load(sys.stdin)
for k in reg:
    if k != 'none':
        print(f'    - {k}')
"

# =================== 完成 ===================
echo ""
echo "============================================================"
echo "🎉 部署完成！"
echo "============================================================"
echo ""
echo "目录结构:"
find "${BASE}" -name "*.safetensors" | while read f; do
    size=$(ls -lh "$f" | awk '{print $5}')
    echo "  ${size}  $(basename $f)"
done
echo ""
echo "剩余空间:"
df -h /workspace | tail -1
echo "============================================================"
