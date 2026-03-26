#!/bin/bash
# ============================================================
# 🚀 ComfyUI 官方模板 一键安装脚本
# ============================================================
# 适用于 RunPod 官方 ComfyUI 模板（无需 Network Volume）
# 用法: bash setup_comfy.sh
# ============================================================

set -uo pipefail
ERRORS=0

# === 自动检测 ComfyUI 目录 ===
COMFY_DIR=$(find /workspace /root /home -maxdepth 4 -name "main.py" -path "*/ComfyUI/*" \
    ! -path "*/.venv*" ! -path "*/site-packages*" 2>/dev/null | head -1 | xargs dirname 2>/dev/null)

if [ -z "$COMFY_DIR" ]; then
    echo "❌ 找不到 ComfyUI 目录！确保你使用的是 ComfyUI 模板。"
    exit 1
fi

MODELS="$COMFY_DIR/models"
CUSTOM="$COMFY_DIR/custom_nodes"

echo "============================================================"
echo "🚀 ComfyUI 官方模板 一键安装"
echo "============================================================"
echo "ComfyUI 目录: $COMFY_DIR"
echo "Models 目录:  $MODELS"
df -h /workspace 2>/dev/null | tail -1 || df -h / | tail -1
echo "============================================================"

# === Step 1: 创建目录 ===
echo ""
echo "[Step 1/4] 创建模型目录..."
mkdir -p "$MODELS/diffusion_models" "$MODELS/vae" "$MODELS/text_encoders" \
         "$MODELS/clip_vision" "$MODELS/loras" "$MODELS/upscale_models"
echo "  ✅ 目录创建完成"

# === 下载函数（带大小验证）===
get_size() { stat -c%s "$1" 2>/dev/null || stat -f%z "$1" 2>/dev/null || echo 0; }

download_model() {
    local path="$1" url="$2" min_bytes="$3" desc="$4"
    local name=$(basename "$path")

    if [ -f "$path" ]; then
        local size=$(get_size "$path")
        if [ "$size" -ge "$min_bytes" ]; then
            echo "  ✅ 已存在，跳过: ${name} ($(numfmt --to=iec $size))"
            return 0
        else
            echo "  ⚠️  文件太小($(numfmt --to=iec $size))，重新下载: ${name}"
            rm -f "$path"
        fi
    fi

    echo "  ⬇️  下载 ${desc}..."
    wget -L --show-progress -O "$path" "$url" 2>&1 || true

    local size=$(get_size "$path")
    if [ "$size" -ge "$min_bytes" ]; then
        echo "  ✅ ${name} ($(numfmt --to=iec $size))"
    else
        echo "  ❌ 下载失败: ${name} ($(numfmt --to=iec $size)，期望≥$(numfmt --to=iec $min_bytes))"
        rm -f "$path"
        ERRORS=$((ERRORS+1))
    fi
}

COMFY_ORG22="https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files"
COMFY_ORG21="https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files"
CIVITAI_TOKEN="95f1a54dbe965d73177e8759bd55b6ea"

# === Step 2: 下载 Wan2.2 基础模型 ===
echo ""
echo "[Step 2/4] 下载 Wan2.2 官方模型..."

download_model \
    "$MODELS/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors" \
    "$COMFY_ORG22/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors" \
    10737418240 "Wan2.2 I2V High Noise DiT (~14GB)"

download_model \
    "$MODELS/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors" \
    "$COMFY_ORG22/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors" \
    10737418240 "Wan2.2 I2V Low Noise DiT (~14GB)"

download_model \
    "$MODELS/vae/wan_2.1_vae.safetensors" \
    "$COMFY_ORG22/vae/wan_2.1_vae.safetensors" \
    209715200 "Wan VAE (~254MB)"

download_model \
    "$MODELS/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
    "$COMFY_ORG22/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
    4294967296 "T5 Text Encoder (~6.3GB)"

download_model \
    "$MODELS/clip_vision/clip_vision_h.safetensors" \
    "$COMFY_ORG21/clip_vision/clip_vision_h.safetensors" \
    1073741824 "CLIP Vision (~1.26GB)"

echo "  ✅ 基础模型完成"

# === Step 3: 下载 LoRA ===
echo ""
echo "[Step 3/4] 下载 LoRA 文件..."

download_model \
    "$MODELS/loras/analMissionary_i2v.safetensors" \
    "https://civitai.com/api/download/models/1700298?token=${CIVITAI_TOKEN}" \
    314572800 "Anal Missionary I2V LoRA (~343MB)"

download_model \
    "$MODELS/loras/analgirl_low.safetensors" \
    "https://vcdn.sprize.ai/loras/analgirl_low.safetensors" \
    524288000 "analgirl Low Noise LoRA (~586MB)"

download_model \
    "$MODELS/loras/analgirl_high.safetensors" \
    "https://vcdn.sprize.ai/loras/analgirl_high.safetensors" \
    524288000 "analgirl High Noise LoRA (~586MB)"

echo "  ✅ LoRA 下载完成"

# === Step 4: 安装自定义节点 ===
echo ""
echo "[Step 4/4] 安装自定义节点..."

install_node() {
    local name="$1" url="$2"
    local dir="$CUSTOM/$name"
    if [ -d "$dir" ]; then
        echo "  ✅ 已安装，更新: $name"
        git -C "$dir" pull -q 2>/dev/null || true
    else
        echo "  ⬇️  安装: $name..."
        git clone -q "$url" "$dir"
        echo "  ✅ $name 已安装"
    fi
    if [ -f "$dir/requirements.txt" ]; then
        pip install -r "$dir/requirements.txt" -q --root-user-action=ignore 2>/dev/null || true
    fi
}

install_node "ComfyUI-KJNodes" "https://github.com/kijai/ComfyUI-KJNodes.git"
install_node "ComfyUI-VideoHelperSuite" "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git"
install_node "ComfyUI-Frame-Interpolation" "https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git"
install_node "cg-use-everywhere" "https://github.com/chrisgoringe/cg-use-everywhere.git"
install_node "ComfyUI-Easy-Use" "https://github.com/yolain/ComfyUI-Easy-Use.git"

echo "  ✅ 自定义节点安装完成"

# === Manager 安全级别解锁 ===
MANAGER_DIR="$CUSTOM/ComfyUI-Manager"
if [ -d "$MANAGER_DIR" ]; then
    python3 -c "
import os, configparser
cfg_path = os.path.join('$MANAGER_DIR', 'config.ini')
cfg = configparser.ConfigParser()
cfg.read(cfg_path)
if 'default' not in cfg:
    cfg['default'] = {}
cfg['default']['security_level'] = 'weak'
with open(cfg_path, 'w') as f:
    cfg.write(f)
print('  ✅ Manager 安全级别已设为 weak')
" 2>/dev/null || echo "  ⚠️  Manager 配置更新跳过"
fi

# === 完成 ===
echo ""
echo "============================================================"
if [ "$ERRORS" -eq 0 ]; then
    echo "🎉 全部完成！请重启 ComfyUI 后加载 workflow。"
else
    echo "⚠️  完成，但有 ${ERRORS} 个文件下载失败，请检查网络后重新运行。"
fi
echo "============================================================"
echo ""
echo "模型清单:"
find "$MODELS" -name "*.safetensors" 2>/dev/null | while read f; do
    printf "  %6s  %s\n" "$(numfmt --to=iec $(get_size $f))" "$(basename $f)"
done
echo "============================================================"
