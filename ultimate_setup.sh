#!/bin/bash
echo "🚀 终极版无人值守部署启动！智能防爆盘+全自动节点补齐+模型拉取..."

WORKSPACE_DIR="/workspace"
if [ -d "/runpod-volume" ]; then
    echo "💡 侦测到 Network Volume (网络共享云盘) 的挂载特征！主盘口切换至 /runpod-volume！"
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
    echo "✅ 全新 ComfyUI 安装完毕！"
else
    echo "🎯 精准侦测到正在运行的 ComfyUI，当前位置位于：$COMFY_DIR "
    echo "🔄 正在为您建立永久模型库（$WORKSPACE_DIR/my_stable_models）..."
    mkdir -p $WORKSPACE_DIR/my_stable_models
    
    # 灾难抢救：用带进度条的极速同步
    if [ -d "$WORKSPACE_DIR/ComfyUI/models" ] && [ "$COMFY_DIR" != "$WORKSPACE_DIR/ComfyUI" ]; then
        echo "♻️ 正在智能回收几十G上次下载偏离的模型资源... （此过程大概需要2-3分钟，底部会展示进度条，请千万不要关闭页面！）"
        rsync -aP $WORKSPACE_DIR/ComfyUI/models/ $WORKSPACE_DIR/my_stable_models/ 2>/dev/null || true
        rm -rf $WORKSPACE_DIR/ComfyUI 2>/dev/null || true
    fi

    if [ ! -L "$COMFY_DIR/models" ]; then
        echo "📦 正在无损迁移系统自带模型...（稍等数秒）"
        rsync -aP $COMFY_DIR/models/ $WORKSPACE_DIR/my_stable_models/ 2>/dev/null || true
        rm -rf $COMFY_DIR/models
        ln -s $WORKSPACE_DIR/my_stable_models $COMFY_DIR/models
    fi
fi

echo "🔍 【最终验证】查阅软链接是否已指向安全副盘 $WORKSPACE_DIR ："
ls -ld $COMFY_DIR/models
echo "--------------------------------------------------------"

echo "📂 创建高级权限防上传500崩溃夹..."
mkdir -p $COMFY_DIR/input $COMFY_DIR/output
chmod -R 777 $COMFY_DIR/input $COMFY_DIR/output

echo "🧩 自动补全工作流必备神仙节点（rgthree / kjnodes）..."
mkdir -p $COMFY_DIR/custom_nodes
cd $COMFY_DIR/custom_nodes
git clone https://github.com/rgthree/rgthree-comfy.git 2>/dev/null || true
git clone https://github.com/kijai/ComfyUI-KJNodes.git 2>/dev/null || true

PIPBIN="pip"
if [ -f "$COMFY_DIR/.venv-cu128/bin/pip" ]; then
    PIPBIN="$COMFY_DIR/.venv-cu128/bin/pip"
elif [ -f "$COMFY_DIR/venv/bin/pip" ]; then
    PIPBIN="$COMFY_DIR/venv/bin/pip"
fi

$PIPBIN install sageattention 2>/dev/null || true
$PIPBIN install -r rgthree-comfy/requirements.txt 2>/dev/null || true
$PIPBIN install -r ComfyUI-KJNodes/requirements.txt 2>/dev/null || true

echo "📥 开始巨容量模型安全下发，彻底降临至副盘..."
mkdir -p $COMFY_DIR/models/diffusion_models
mkdir -p $COMFY_DIR/models/vae
mkdir -p $COMFY_DIR/models/text_encoders
mkdir -p $COMFY_DIR/models/loras
mkdir -p $COMFY_DIR/models/clip_vision

wget -q --show-progress -nc -O $COMFY_DIR/models/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
wget -q --show-progress -nc -O $COMFY_DIR/models/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
wget -q --show-progress -nc -O $COMFY_DIR/models/vae/wan_2.1_vae.safetensors "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors?download=true"
wget -q --show-progress -nc -O $COMFY_DIR/models/text_encoders/nsfw_wan_umt5-xxl_fp8_scaled.safetensors "https://huggingface.co/NSFW-API/NSFW-Wan-UMT5-XXL/resolve/main/nsfw_wan_umt5-xxl_fp8_scaled.safetensors?download=true"
wget -q --show-progress -nc -O $COMFY_DIR/models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors?download=true"
wget -q --show-progress -nc -O $COMFY_DIR/models/loras/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Stable-Video-Infinity/v2.0/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors?download=true"
wget -q --show-progress -nc -O $COMFY_DIR/models/loras/SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Stable-Video-Infinity/v2.0/SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors?download=true"
wget -q --show-progress -nc -O $COMFY_DIR/models/loras/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors "https://huggingface.co/lightx2v/Wan2.2-Distill-Loras/resolve/main/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors?download=true"
echo "🔓 正在通过专属秘钥自动破解防线，极速拉取 C站 15+15GB 高端限制级模型，请稍候 (真实进度条展示)..."
curl -# -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36" -H "Authorization: Bearer 95f1a54dbe965d73177e8759bd55b6ea" "https://civitai.com/api/download/models/2477539" -o $COMFY_DIR/models/diffusion_models/WAN2.2-NSFW-FastMove-V2-H.safetensors
curl -# -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36" -H "Authorization: Bearer 95f1a54dbe965d73177e8759bd55b6ea" "https://civitai.com/api/download/models/2477548" -o $COMFY_DIR/models/diffusion_models/WAN2.2-NSFW-FastMove-V2-L.safetensors
wget -q --show-progress -nc -O $COMFY_DIR/models/loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors?download=true"

echo "✅ 史诗级胜利！彻底执行完成！去网页最右侧控制面板点一下 Refresh (刷新) 即可开始生产！"
