#!/bin/bash
echo "🚀 正在智能探测系统真正安装路径并做底层扩容..."

# 1. 寻找这台机器的真实 ComfyUI 躲在哪里
COMFY_DIR=""
for path in /comfyui /src/ComfyUI /root/ComfyUI /opt/ComfyUI /workspace/ComfyUI; do
    if [ -f "$path/main.py" ]; then
        COMFY_DIR="$path"
        break
    fi
done

if [ -z "$COMFY_DIR" ]; then
    echo "❌ 完蛋，没找到 ComfyUI 真正安装的核心目录！"
    exit 1
fi
echo "🎯 终于抓到了！ComfyUI 真实的运行代码竟然藏在：$COMFY_DIR"

# 2. 强行在不扣钱的 100GB /workspace 建立一个真正的永久硬盘基地
mkdir -p /workspace/my_stable_models

# 3. 把系统里的那个假的/临时的模型文件夹，强行引流到网盘里
if [ ! -L "$COMFY_DIR/models" ]; then
    echo "📦 正在无损迁移系统自带模型大礼包到永久闲置扩展盘..."
    cp -r $COMFY_DIR/models/* /workspace/my_stable_models/ 2>/dev/null || true
    rm -rf $COMFY_DIR/models
fi
ln -s /workspace/my_stable_models $COMFY_DIR/models
echo "🔗 惊天地泣鬼神级别的软连接打通完毕！"

# 4. 创建魔法 input 夹防御500上传崩溃
mkdir -p $COMFY_DIR/input && chmod -R 777 $COMFY_DIR/input

echo "🚀 正在极速向真正的 100GB 网盘中拉取巨无霸底模集群..."
mkdir -p /workspace/my_stable_models/diffusion_models
mkdir -p /workspace/my_stable_models/vae
mkdir -p /workspace/my_stable_models/text_encoders
mkdir -p /workspace/my_stable_models/loras
mkdir -p /workspace/my_stable_models/clip_vision

# 【补充】原工作流的 GGUF 替换成了普通的 UNETLoader，我们把模型下载进去！
wget -q --show-progress -nc -O /workspace/my_stable_models/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
wget -q --show-progress -nc -O /workspace/my_stable_models/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
wget -q --show-progress -nc -O /workspace/my_stable_models/vae/wan_2.1_vae.safetensors "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors?download=true"
wget -q --show-progress -nc -O /workspace/my_stable_models/text_encoders/nsfw_wan_umt5-xxl_fp8_scaled.safetensors "https://huggingface.co/NSFW-API/NSFW-Wan-UMT5-XXL/resolve/main/nsfw_wan_umt5-xxl_fp8_scaled.safetensors?download=true"
wget -q --show-progress -nc -O /workspace/my_stable_models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors?download=true"
wget -q --show-progress -nc -O /workspace/my_stable_models/loras/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Stable-Video-Infinity/v2.0/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors?download=true"
wget -q --show-progress -nc -O /workspace/my_stable_models/loras/SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Stable-Video-Infinity/v2.0/SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors?download=true"
wget -q --show-progress -nc -O /workspace/my_stable_models/loras/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors "https://huggingface.co/lightx2v/Wan2.2-Distill-Loras/resolve/main/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors?download=true"
wget -q --show-progress -nc -O /workspace/my_stable_models/diffusion_models/WAN2.2-NSFW-FastMove-V2-H.safetensors "https://civitai.com/api/download/models/2613591?type=Model&format=SafeTensor&size=pruned&fp=fp16"
wget -q --show-progress -nc -O /workspace/my_stable_models/diffusion_models/WAN2.2-NSFW-FastMove-V2-L.safetensors "https://civitai.com/api/download/models/2613591?type=Model&format=SafeTensor&size=pruned&fp=fp16"
wget -q --show-progress -nc -O /workspace/my_stable_models/loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors?download=true"

echo "✅ 王者归来！模型全部下载完成！老规矩：去网页端点一下 Refresh 刷新！"
