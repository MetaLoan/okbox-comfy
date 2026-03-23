#!/bin/bash
echo "🚀 正在为您将系统原生模型库进行超大杯软链接重路由扩充..."

# 1. 强制在拥有 100GB 大容量的 /workspace 盘下圈地
mkdir -p /workspace/ComfyUI/models

# 2. 如果本来就已经存在默认的老文件路径，我们要将它转移。如果它是链接则跳过
if [ -d "/root/ComfyUI/models" ] && [ ! -L "/root/ComfyUI/models" ]; then
    echo "📦 正在无损迁移系统自带模型大礼包到永久闲置扩展盘..."
    cp -r /root/ComfyUI/models/* /workspace/ComfyUI/models/ 2>/dev/null || true
    rm -rf /root/ComfyUI/models
fi

# 3. 施加时空魔法：强行把内部系统访问 /root 下的模型视线转移到挂载的 /workspace 盘下！
ln -s /workspace/ComfyUI/models /root/ComfyUI/models
echo "🔗 软连接打通完毕！这台机器再也不会卡死且重启不掉配置了！"

# 4. 创建可以接受外面图片上传的魔法防崩溃 input 接口文件夹
mkdir -p /root/ComfyUI/input
chmod -R 777 /root/ComfyUI/input

echo "🚀 正在往 /workspace 网盘专属地盘极速脱机下载核心模型..."
mkdir -p /workspace/ComfyUI/models/diffusion_models
mkdir -p /workspace/ComfyUI/models/vae
mkdir -p /workspace/ComfyUI/models/text_encoders
mkdir -p /workspace/ComfyUI/models/loras
mkdir -p /workspace/ComfyUI/models/clip_vision

wget -q --show-progress -nc -O /workspace/ComfyUI/models/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
wget -q --show-progress -nc -O /workspace/ComfyUI/models/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
wget -q --show-progress -nc -O /workspace/ComfyUI/models/vae/wan_2.1_vae.safetensors "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors?download=true"
wget -q --show-progress -nc -O /workspace/ComfyUI/models/text_encoders/nsfw_wan_umt5-xxl_fp8_scaled.safetensors "https://huggingface.co/NSFW-API/NSFW-Wan-UMT5-XXL/resolve/main/nsfw_wan_umt5-xxl_fp8_scaled.safetensors?download=true"
wget -q --show-progress -nc -O /workspace/ComfyUI/models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors?download=true"
wget -q --show-progress -nc -O /workspace/ComfyUI/models/loras/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Stable-Video-Infinity/v2.0/SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors?download=true"
wget -q --show-progress -nc -O /workspace/ComfyUI/models/loras/SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Stable-Video-Infinity/v2.0/SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors?download=true"
wget -q --show-progress -nc -O /workspace/ComfyUI/models/loras/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors "https://huggingface.co/lightx2v/Wan2.2-Distill-Loras/resolve/main/wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors?download=true"
wget -q --show-progress -nc -O /workspace/ComfyUI/models/diffusion_models/WAN2.2-NSFW-FastMove-V2-H.safetensors "https://civitai.com/api/download/models/2613591?type=Model&format=SafeTensor&size=pruned&fp=fp16"
wget -q --show-progress -nc -O /workspace/ComfyUI/models/diffusion_models/WAN2.2-NSFW-FastMove-V2-L.safetensors "https://civitai.com/api/download/models/2613591?type=Model&format=SafeTensor&size=pruned&fp=fp16"
wget -q --show-progress -nc -O /workspace/ComfyUI/models/loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors?download=true"

echo "✅ 模型全部下载完成！现在去网页端点一下 Refresh 刷新，一切准备就绪！"
