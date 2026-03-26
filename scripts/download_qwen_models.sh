#!/bin/bash

# Configuration (Overridable via Environment Variables)
COMFYUI_DIR=${COMFYUI_DIR:-"/workspace/ComfyUI"} # Default runpod path
MODELS_DIR="${COMFYUI_DIR}/models"

# Define the models to download
# Format: "URL|DESTINATION_DIR|FILENAME"
models=(
    "https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors|${MODELS_DIR}/unet|qwen_image_edit_2509_fp8_e4m3fn.safetensors"
    "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors|${MODELS_DIR}/clip|qwen_2.5_vl_7b_fp8_scaled.safetensors"
    "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors|${MODELS_DIR}/vae|qwen_image_vae.safetensors"
    "https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Edit-2509/Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors|${MODELS_DIR}/loras|Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors"
)

# Helper function to download a file
download_file() {
    local url=$1
    local dest_dir=$2
    local filename=$3
    local final_path="${dest_dir}/${filename}"

    # Create destination directory if it doesn't exist
    mkdir -p "${dest_dir}"

    if [ -f "${final_path}" ]; then
        echo "✅ Model already exists: ${final_path} (Skipping)"
        return 0
    fi

    echo "⬇️ Downloading ${filename} to ${dest_dir}..."

    # Use aria2c if available (faster, parallel connections)
    if command -v aria2c &> /dev/null; then
        aria2c --console-log-level=error -c -x 16 -s 16 -k 1M "${url}" -d "${dest_dir}" -o "${filename}"
    else
        # Fallback to wget
        wget -c -q --show-progress -O "${final_path}" "${url}"
    fi

    if [ $? -eq 0 ]; then
        echo "✅ Successfully downloaded: ${filename}"
    else
        echo "❌ Failed to download: ${filename}"
        exit 1
    fi
}

echo "�� Starting Qwen 2509 Model Downloads..."

for entry in "${models[@]}"; do
    IFS='|' read -r url dest filename <<< "$entry"
    download_file "$url" "$dest" "$filename"
done

echo "🎉 All Qwen 2509 resources have been successfully downloaded!"
