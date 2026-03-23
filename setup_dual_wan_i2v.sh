#!/bin/bash
echo "🚀 Dual Wan I2V 极简化专供部署脚本启动..."

WORKSPACE_DIR="/workspace"
if [ -d "/runpod-volume" ]; then
    echo "💡 侦测到 Network Volume ，主盘口切换至 /runpod-volume"
    WORKSPACE_DIR="/runpod-volume"
fi

COMFY_DIR=""
for path in /workspace/runpod-slim/ComfyUI /runpod-volume/runpod-slim/ComfyUI $WORKSPACE_DIR/ComfyUI /comfyui /src/ComfyUI /root/ComfyUI /opt/ComfyUI; do
    if [ -f "$path/main.py" ]; then
        COMFY_DIR="$path"
        break
    fi
done

if [ -z "$COMFY_DIR" ]; then
    echo "❌ 没找到内置 ComfyUI！执行全新纯净版安装..."
    cd $WORKSPACE_DIR
    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd ComfyUI
    pip install -r requirements.txt
    COMFY_DIR="$WORKSPACE_DIR/ComfyUI"
else
    echo "🎯 发现 ComfyUI 当前位置：$COMFY_DIR "
    mkdir -p $WORKSPACE_DIR/my_stable_models
    if [ ! -L "$COMFY_DIR/models" ]; then
        echo "📦 正在无损迁移系统自带模型..."
        rsync -aP $COMFY_DIR/models/ $WORKSPACE_DIR/my_stable_models/ 2>/dev/null || true
        rm -rf $COMFY_DIR/models
        ln -s $WORKSPACE_DIR/my_stable_models $COMFY_DIR/models
    fi
fi

# Engine Upgrade for FP8 format bug fixes
echo "⏫ 执行新版 ComfyUI 内核升级，避免 load_unet 遭遇 FP8 模型崩溃报错..."
cd $COMFY_DIR && git stash 2>/dev/null || true
git pull 2>/dev/null || true

echo "🔋 强制同步运行环境与依赖包 (防御 NumPy/PyTorch 版本撕裂问题)..."
pip install -r requirements.txt 2>/dev/null || true
pip install "numpy<2" 2>/dev/null || true
pip install torch torchvision torchaudio --upgrade --extra-index-url https://download.pytorch.org/whl/cu121 2>/dev/null || true

# Folder Setup
mkdir -p $COMFY_DIR/input $COMFY_DIR/output
chmod -R 777 $COMFY_DIR/input $COMFY_DIR/output

mkdir -p $COMFY_DIR/custom_nodes
cd $COMFY_DIR/custom_nodes
# Helper Suite to render webm formats cleanly
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git 2>/dev/null || true

echo "📥 开始拉取极简化组件（仅限 dual_wan_i2v 工作流核心大模型）..."
mkdir -p $COMFY_DIR/models/diffusion_models
mkdir -p $COMFY_DIR/models/vae
mkdir -p $COMFY_DIR/models/text_encoders
mkdir -p $COMFY_DIR/models/clip_vision

wget -q --show-progress -nc -O $COMFY_DIR/models/vae/wan_2.1_vae.safetensors "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors?download=true"
wget -q --show-progress -nc -O $COMFY_DIR/models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors?download=true"
wget -q --show-progress -nc -O $COMFY_DIR/models/clip_vision/clip_vision_h.safetensors "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors?download=true"

echo "🔓 突破 C站 拦截限制，高速下载绝版 FastMove 高阶模型..."
curl -# -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36" -H "Authorization: Bearer 95f1a54dbe965d73177e8759bd55b6ea" "https://civitai.com/api/download/models/2477539" -o $COMFY_DIR/models/diffusion_models/WAN2.2-NSFW-FastMove-V2-H.safetensors
curl -# -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36" -H "Authorization: Bearer 95f1a54dbe965d73177e8759bd55b6ea" "https://civitai.com/api/download/models/2477548" -o $COMFY_DIR/models/diffusion_models/WAN2.2-NSFW-FastMove-V2-L.safetensors

echo "✅ Dual Wan I2V 极速版部署全部完成！请重开网页或 Restart 机器读取最新引擎与模型！"
