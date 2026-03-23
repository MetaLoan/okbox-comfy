#!/bin/bash
echo "🚀 终极版无人值守部署启动！防爆硬盘+全自动节点补齐+模型拉取..."

COMFY_DIR=""
for path in /comfyui /src/ComfyUI /root/ComfyUI /opt/ComfyUI /workspace/ComfyUI; do
    if [ -f "$path/main.py" ]; then
        COMFY_DIR="$path"
        break
    fi
done

if [ -z "$COMFY_DIR" ]; then
    echo "❌ 没找到内置 ComfyUI！正在 /workspace 这块 100GB 永久超大副盘下，为您执行全新纯净版物理安装..."
    cd /workspace
    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd ComfyUI
    pip install -r requirements.txt
    COMFY_DIR="/workspace/ComfyUI"
    echo "✅ 全新 ComfyUI 安装完毕，天然生长在永久副盘，永不爆碎主盘！"
else
    echo "🎯 侦测到了云服务器自带的 ComfyUI，当前病态位置位于：$COMFY_DIR （极可能在主盘！）"
    echo "🔄 正在使用空间魔法转移一切阵地到 100GB 永久网络副盘（/workspace）中..."
    mkdir -p /workspace/my_stable_models
    
    if [ ! -L "$COMFY_DIR/models" ]; then
        cp -rn $COMFY_DIR/models/* /workspace/my_stable_models/ 2>/dev/null || true
        rm -rf $COMFY_DIR/models
        ln -s /workspace/my_stable_models $COMFY_DIR/models
    fi
fi

echo "🔍 【最终验证】查阅系统视角下 models 目录的真面目（如果是软链接指向 /workspace 证明完全转移至副盘）："
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
# 部分节点需要特定依赖
pip install -r rgthree-comfy/requirements.txt 2>/dev/null || true

echo "📥 开始巨容量模型（30GB+）安全下发，统统降临至 $COMFY_DIR/models 背后实际的 /workspace 副盘中..."
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
wget -q --show-progress -nc -O $COMFY_DIR/models/diffusion_models/WAN2.2-NSFW-FastMove-V2-H.safetensors "https://civitai.com/api/download/models/2613591?type=Model&format=SafeTensor&size=pruned&fp=fp16"
wget -q --show-progress -nc -O $COMFY_DIR/models/diffusion_models/WAN2.2-NSFW-FastMove-V2-L.safetensors "https://civitai.com/api/download/models/2613591?type=Model&format=SafeTensor&size=pruned&fp=fp16"
wget -q --show-progress -nc -O $COMFY_DIR/models/loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors?download=true"

echo "✅ 史诗级胜利！彻底执行完成！去网页最右侧控制面板点一下 Refresh (刷新) 即可开始生产！"
