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

set -uo pipefail
ERRORS=0

BASE="/workspace/my_stable_models"
REGISTRY_URL="https://raw.githubusercontent.com/MetaLoan/okbox-comfy/main/lora_style_registry.json"
COMFY_ORG="https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files"
KIJAI="https://huggingface.co/Kijai/WanVideo_comfy/resolve/main"

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

get_size() {
    stat -c%s "$1" 2>/dev/null || stat -f%z "$1" 2>/dev/null || echo 0
}

# download_model path url min_bytes description
download_model() {
    local path="$1"
    local url="$2"
    local min_bytes="$3"
    local desc="$4"
    local name=$(basename "$path")

    # 检查是否已存在且大小正确
    if [ -f "$path" ]; then
        local size=$(get_size "$path")
        if [ "$size" -ge "$min_bytes" ]; then
            echo "  ✅ 已存在，跳过: ${name} ($(numfmt --to=iec $size))"
            return 0
        else
            echo "  ⚠️  文件太小 ${name} ($(numfmt --to=iec $size)，期望 ≥$(numfmt --to=iec $min_bytes))，重新下载..."
            rm -f "$path"
        fi
    fi

    echo "  ⬇️  下载 ${desc}..."
    wget -L --show-progress -O "$path" "$url" 2>&1 || true

    # 验证下载后大小
    local size=$(get_size "$path")
    if [ "$size" -ge "$min_bytes" ]; then
        echo "  ✅ ${name} ($(numfmt --to=iec $size))"
    else
        echo "  ❌ 下载失败或文件无效: ${name} ($(numfmt --to=iec $size)，期望 ≥$(numfmt --to=iec $min_bytes))"
        rm -f "$path"
        ERRORS=$((ERRORS+1))
        return 0
    fi
}

# DiT 模型（各 ~14GB，最小验证 10GB）
download_model \
    "${BASE}/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors" \
    "${COMFY_ORG}/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors" \
    10737418240 "Wan2.2 I2V High Noise DiT (~14GB)"

download_model \
    "${BASE}/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors" \
    "${COMFY_ORG}/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors" \
    10737418240 "Wan2.2 I2V Low Noise DiT (~14GB)"

# VAE（~254MB，最小验证 200MB）
download_model \
    "${BASE}/vae/wan_2.1_vae.safetensors" \
    "${COMFY_ORG}/vae/wan_2.1_vae.safetensors" \
    209715200 "Wan VAE (~254MB)"

# CLIP Text Encoder（~5GB，最小验证 4GB）
download_model \
    "${BASE}/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
    "${COMFY_ORG}/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
    4294967296 "T5 Text Encoder (~5GB)"

# CLIP Vision（~3.3GB，最小验证 3GB — 来自 Kijai repo）
download_model \
    "${BASE}/clip_vision/clip_vision_h.safetensors" \
    "${KIJAI}/clip_vision_h.safetensors" \
    3221225472 "CLIP Vision (~3.3GB)"

echo "  ✅ 基础模型下载完成"

# =================== Step 3: 下载 LoRA ===================
echo ""
echo "[Step 3/4] 下载 LoRA 文件..."

# CivitAI Anal Missionary I2V（~343MB，最小验证 300MB）
download_model \
    "${BASE}/loras/analMissionary_i2v.safetensors" \
    "https://civitai.com/api/download/models/1700298?token=95f1a54dbe965d73177e8759bd55b6ea" \
    314572800 "Anal Missionary I2V LoRA (~343MB)"

# 自训练 LoRA（~586MB，最小验证 500MB）
download_model \
    "${BASE}/loras/analgirl_low.safetensors" \
    "https://vcdn.sprize.ai/loras/analgirl_low.safetensors" \
    524288000 "analgirl Low Noise LoRA (~586MB)"

download_model \
    "${BASE}/loras/analgirl_high.safetensors" \
    "https://vcdn.sprize.ai/loras/analgirl_high.safetensors" \
    524288000 "analgirl High Noise LoRA (~586MB)"

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
