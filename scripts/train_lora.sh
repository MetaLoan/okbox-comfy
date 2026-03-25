#!/bin/bash
# ============================================================
# 🎬 Wan2.2 I2V LoRA 一键训练脚本
# ============================================================
# 用法: bash train_lora.sh <视频文件> <提示词> [模型名称]
#
# 示例:
#   bash train_lora.sh /workspace/my_video.mp4 \
#     "A woman is having sex in the cowgirl position. She moves her hips up and down." \
#     cowgirl
#
# 此脚本会自动:
#   1. 安装 musubi-tuner（如未安装）
#   2. 将视频切成 5 秒片段（首帧静止过渡格式）
#   3. 为每个片段生成 caption 文件
#   4. 预缓存 latents 和 text encoder outputs
#   5. 分别训练 High Noise 和 Low Noise LoRA
#   6. 将输出拷贝到 Network Volume 的 loras 目录
#
# 要求:
#   - GPU Pod with ≥40GB VRAM (推荐 A100 80GB / H100 80GB)
#   - Network Volume 挂载到 /runpod-volume（已有 Wan2.2 模型文件）
# ============================================================

set -e

# ==================== 参数解析 ====================
VIDEO_PATH="${1:?用法: bash train_lora.sh <视频文件> <提示词> [模型名称]}"
PROMPT="${2:?用法: bash train_lora.sh <视频文件> <提示词> [模型名称]}"
MODEL_NAME="${3:-my_lora}"

# ==================== 路径配置 ====================
WORK_DIR="/workspace/lora_training/${MODEL_NAME}"
CLIPS_DIR="${WORK_DIR}/clips"
CACHE_DIR="${WORK_DIR}/cache"
OUTPUT_DIR="${WORK_DIR}/output"
MUSUBI_DIR="/workspace/musubi-tuner"

# Wan2.2 模型路径（Network Volume 上）
VOLUME_BASE="/runpod-volume/my_stable_models"
# 自动探测 DiT 模型路径
DIT_HIGH=""
DIT_LOW=""
VAE=""
T5=""

# ==================== 训练参数 ====================
CLIP_DURATION=5          # 每段视频长度（秒）
RESOLUTION_W=832         # Portrait 模式
RESOLUTION_H=1216
NETWORK_DIM=64           # LoRA rank
LEARNING_RATE="2e-4"
MAX_TRAIN_STEPS=1500     # 训练步数
SAVE_EVERY_N_STEPS=500
SEED=42
DISCRETE_FLOW_SHIFT=5.0  # I2V 推荐值

echo "============================================================"
echo "🎬 Wan2.2 I2V LoRA 一键训练"
echo "============================================================"
echo "视频: ${VIDEO_PATH}"
echo "提示词: ${PROMPT}"
echo "模型名: ${MODEL_NAME}"
echo "分辨率: ${RESOLUTION_W}x${RESOLUTION_H}"
echo "LoRA Rank: ${NETWORK_DIM}"
echo "训练步数: ${MAX_TRAIN_STEPS}"
echo "============================================================"

# ==================== Step 0: 检测模型文件 ====================
echo ""
echo "[Step 0/7] 检测模型文件..."

# 查找 DiT 模型
find_model() {
    local pattern="$1"
    local desc="$2"
    local found=$(find "${VOLUME_BASE}" -name "${pattern}" -type f 2>/dev/null | head -1)
    if [ -z "$found" ]; then
        echo "❌ 找不到 ${desc}: ${pattern}"
        echo "   请检查 ${VOLUME_BASE} 下是否有对应模型文件"
        return 1
    fi
    echo "  ✅ ${desc}: $(basename $found)"
    echo "$found"
}

# 尝试寻找 High/Low noise DiT 模型
# Wan2.2 通常有独立的 High 和 Low noise 模型
echo "  查找 Wan2.2 I2V 模型..."

# 检查是否有合并的单文件模型
SINGLE_DIT=$(find "${VOLUME_BASE}" -name "*wan2*i2v*14b*" -o -name "*Wan2*I2V*" -type f 2>/dev/null | grep -i "\.safetensors$" | grep -iv "high\|low\|lora" | head -1)

if [ -n "$SINGLE_DIT" ]; then
    echo "  ✅ DiT (单文件): $(basename $SINGLE_DIT)"
    DIT_LOW="$SINGLE_DIT"
    DIT_HIGH=""
else
    # 查找独立的 High/Low 模型
    DIT_HIGH=$(find "${VOLUME_BASE}" -name "*wan*high*" -type f 2>/dev/null | grep -i "\.safetensors$" | grep -iv "lora" | head -1)
    DIT_LOW=$(find "${VOLUME_BASE}" -name "*wan*low*" -type f 2>/dev/null | grep -i "\.safetensors$" | grep -iv "lora" | head -1)

    if [ -z "$DIT_LOW" ]; then
        echo "❌ 找不到 Wan2.2 DiT 模型"
        echo "   在 ${VOLUME_BASE} 下搜索的文件:"
        find "${VOLUME_BASE}" -name "*.safetensors" -type f | head -20
        exit 1
    fi
    echo "  ✅ DiT Low: $(basename $DIT_LOW)"
    [ -n "$DIT_HIGH" ] && echo "  ✅ DiT High: $(basename $DIT_HIGH)"
fi

# 查找 VAE
VAE=$(find "${VOLUME_BASE}" -name "*vae*" -type f 2>/dev/null | grep -i "\.safetensors$\|\.pth$" | head -1)
if [ -z "$VAE" ]; then
    echo "❌ 找不到 VAE 模型"
    exit 1
fi
echo "  ✅ VAE: $(basename $VAE)"

# 查找 T5 text encoder
T5=$(find "${VOLUME_BASE}" -name "*t5*" -o -name "*umt5*" -type f 2>/dev/null | grep -i "\.pth$\|\.safetensors$" | head -1)
if [ -z "$T5" ]; then
    echo "⚠️  找不到 T5 模型，将尝试自动下载..."
fi

# ==================== Step 1: 安装 musubi-tuner ====================
echo ""
echo "[Step 1/7] 安装 musubi-tuner..."

if [ ! -d "$MUSUBI_DIR" ]; then
    cd /workspace
    git clone https://github.com/kohya-ss/musubi-tuner.git
    cd musubi-tuner
    pip install -e . -q
    echo "  ✅ musubi-tuner 安装完成"
else
    cd "$MUSUBI_DIR"
    git pull --quiet 2>/dev/null || true
    echo "  ✅ musubi-tuner 已存在，已更新"
fi

# 配置 accelerate（静默）
if [ ! -f ~/.cache/huggingface/accelerate/default_config.yaml ]; then
    mkdir -p ~/.cache/huggingface/accelerate
    cat > ~/.cache/huggingface/accelerate/default_config.yaml << 'ACCEL'
compute_environment: LOCAL_MACHINE
distributed_type: 'NO'
mixed_precision: bf16
use_cpu: false
ACCEL
    echo "  ✅ accelerate 配置完成"
fi

# ==================== Step 2: 视频分片 ====================
echo ""
echo "[Step 2/7] 视频分片..."

mkdir -p "$CLIPS_DIR" "$CACHE_DIR" "$OUTPUT_DIR"

# 获取视频总时长
DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VIDEO_PATH" | cut -d. -f1)
echo "  视频总时长: ${DURATION}s"
echo "  切片长度: ${CLIP_DURATION}s"

# 切片
CLIP_COUNT=0
for START in $(seq 0 $CLIP_DURATION $((DURATION - 1))); do
    CLIP_NUM=$(printf "%03d" $CLIP_COUNT)
    CLIP_FILE="${CLIPS_DIR}/clip_${CLIP_NUM}.mp4"

    ffmpeg -y -ss "$START" -i "$VIDEO_PATH" \
        -t "$CLIP_DURATION" \
        -c:v libx264 -preset fast -crf 18 \
        -vf "scale=${RESOLUTION_W}:${RESOLUTION_H}:force_original_aspect_ratio=decrease,pad=${RESOLUTION_W}:${RESOLUTION_H}:(ow-iw)/2:(oh-ih)/2" \
        -an -r 16 \
        "$CLIP_FILE" -loglevel error

    # 创建对应的 caption 文件（所有片段用同一个 prompt）
    echo "$PROMPT" > "${CLIPS_DIR}/clip_${CLIP_NUM}.txt"

    CLIP_COUNT=$((CLIP_COUNT + 1))
done

echo "  ✅ 切成 ${CLIP_COUNT} 个片段"
ls -lh "$CLIPS_DIR"/*.mp4 | awk '{print "    " $5 " " $NF}'

# ==================== Step 3: 生成数据集配置 ====================
echo ""
echo "[Step 3/7] 生成数据集配置..."

DATASET_CONFIG="${WORK_DIR}/dataset.toml"
cat > "$DATASET_CONFIG" << EOF
[general]
resolution = [${RESOLUTION_W}, ${RESOLUTION_H}]
caption_extension = ".txt"
batch_size = 1
enable_bucket = false

[[datasets]]
video_directory = "${CLIPS_DIR}"
cache_directory = "${CACHE_DIR}"
target_frames = [1, 41, 81]
frame_extraction = "head"
EOF

echo "  ✅ 配置文件: ${DATASET_CONFIG}"
cat "$DATASET_CONFIG"

# ==================== Step 4: 预缓存 latents ====================
echo ""
echo "[Step 4/7] 预缓存 latents..."

cd "$MUSUBI_DIR"

python src/musubi_tuner/wan_cache_latents.py \
    --dataset_config "$DATASET_CONFIG" \
    --vae "$VAE" \
    --i2v \
    --batch_size 1

echo "  ✅ Latent 缓存完成"

# ==================== Step 5: 预缓存 text encoder outputs ====================
echo ""
echo "[Step 5/7] 预缓存 text encoder outputs..."

T5_ARGS=""
if [ -n "$T5" ]; then
    T5_ARGS="--t5 $T5"
fi

python src/musubi_tuner/wan_cache_text_encoder_outputs.py \
    --dataset_config "$DATASET_CONFIG" \
    $T5_ARGS \
    --batch_size 8

echo "  ✅ Text encoder 缓存完成"

# ==================== Step 6: 训练 LoRA ====================
echo ""
echo "[Step 6/7] 开始训练 LoRA..."

# --- 6a: 训练 Low Noise LoRA ---
echo ""
echo "  ━━━ 训练 Low Noise LoRA ━━━"

LOW_OUTPUT="${OUTPUT_DIR}/low_noise"
mkdir -p "$LOW_OUTPUT"

accelerate launch --num_cpu_threads_per_process 1 --mixed_precision bf16 \
    src/musubi_tuner/wan_train_network.py \
    --task i2v-A14B \
    --dit "$DIT_LOW" \
    --dataset_config "$DATASET_CONFIG" \
    --sdpa \
    --mixed_precision bf16 \
    --fp8_base \
    --optimizer_type adamw8bit \
    --learning_rate "$LEARNING_RATE" \
    --gradient_checkpointing \
    --max_data_loader_n_workers 2 \
    --persistent_data_loader_workers \
    --network_module networks.lora_wan \
    --network_dim "$NETWORK_DIM" \
    --timestep_sampling shift \
    --discrete_flow_shift "$DISCRETE_FLOW_SHIFT" \
    --min_timestep 0 \
    --max_timestep 900 \
    --preserve_distribution_shape \
    --max_train_steps "$MAX_TRAIN_STEPS" \
    --save_every_n_steps "$SAVE_EVERY_N_STEPS" \
    --seed "$SEED" \
    --output_dir "$LOW_OUTPUT" \
    --output_name "${MODEL_NAME}_low"

echo "  ✅ Low Noise LoRA 训练完成"

# --- 6b: 训练 High Noise LoRA ---
echo ""
echo "  ━━━ 训练 High Noise LoRA ━━━"

HIGH_OUTPUT="${OUTPUT_DIR}/high_noise"
mkdir -p "$HIGH_OUTPUT"

# 确定 High noise 模型路径
HIGH_DIT_ARG=""
if [ -n "$DIT_HIGH" ]; then
    HIGH_DIT_ARG="--dit $DIT_HIGH"
else
    # 如果只有单文件模型，用同一个但调整 timestep 范围
    HIGH_DIT_ARG="--dit $DIT_LOW"
fi

accelerate launch --num_cpu_threads_per_process 1 --mixed_precision bf16 \
    src/musubi_tuner/wan_train_network.py \
    --task i2v-A14B \
    $HIGH_DIT_ARG \
    --dataset_config "$DATASET_CONFIG" \
    --sdpa \
    --mixed_precision bf16 \
    --fp8_base \
    --optimizer_type adamw8bit \
    --learning_rate "$LEARNING_RATE" \
    --gradient_checkpointing \
    --max_data_loader_n_workers 2 \
    --persistent_data_loader_workers \
    --network_module networks.lora_wan \
    --network_dim "$NETWORK_DIM" \
    --timestep_sampling shift \
    --discrete_flow_shift "$DISCRETE_FLOW_SHIFT" \
    --min_timestep 900 \
    --max_timestep 1000 \
    --preserve_distribution_shape \
    --max_train_steps "$MAX_TRAIN_STEPS" \
    --save_every_n_steps "$SAVE_EVERY_N_STEPS" \
    --seed "$SEED" \
    --output_dir "$HIGH_OUTPUT" \
    --output_name "${MODEL_NAME}_high"

echo "  ✅ High Noise LoRA 训练完成"

# ==================== Step 7: 部署到 Volume ====================
echo ""
echo "[Step 7/7] 部署到 Network Volume..."

LORA_DIR="${VOLUME_BASE}/loras"
mkdir -p "$LORA_DIR"

# 找到最终的 safetensors 文件
LOW_FILE=$(ls -t "${LOW_OUTPUT}"/*.safetensors 2>/dev/null | head -1)
HIGH_FILE=$(ls -t "${HIGH_OUTPUT}"/*.safetensors 2>/dev/null | head -1)

if [ -n "$LOW_FILE" ]; then
    cp "$LOW_FILE" "${LORA_DIR}/${MODEL_NAME}_low.safetensors"
    echo "  ✅ Low Noise: ${LORA_DIR}/${MODEL_NAME}_low.safetensors"
else
    echo "  ❌ Low Noise LoRA 文件未找到"
fi

if [ -n "$HIGH_FILE" ]; then
    cp "$HIGH_FILE" "${LORA_DIR}/${MODEL_NAME}_high.safetensors"
    echo "  ✅ High Noise: ${LORA_DIR}/${MODEL_NAME}_high.safetensors"
else
    echo "  ❌ High Noise LoRA 文件未找到"
fi

# ==================== 完成 ====================
echo ""
echo "============================================================"
echo "🎉 训练完成！"
echo "============================================================"
echo ""
echo "输出文件:"
echo "  High Noise: ${LORA_DIR}/${MODEL_NAME}_high.safetensors"
echo "  Low Noise:  ${LORA_DIR}/${MODEL_NAME}_low.safetensors"
echo ""
echo "下一步 — 注册到 lora_style_registry.json:"
echo ""
echo "  \"${MODEL_NAME}\": {"
echo "    \"high\": \"${MODEL_NAME}_high.safetensors\","
echo "    \"low\": \"${MODEL_NAME}_low.safetensors\""
echo "  }"
echo ""
echo "训练数据保存在: ${WORK_DIR}"
echo "============================================================"
