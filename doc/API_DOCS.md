# Okbox ComfyUI Serverless API 文档

> 基于 RunPod Serverless 的 Wan2.2 视频生成 API
>
> 最后更新: 2026-03-25
> 版本: v2.0 Multi-LoRA

---

## 🏗️ 项目结构

```
okbox-comfy/
├── .github/workflows/docker-build.yml  # GitHub Actions 自动打包 Docker 镜像
├── video-storage/                      # Fly.io 视频存储服务（Node.js）
│   ├── server.js
│   ├── Dockerfile
│   ├── fly.toml
│   └── package.json
├── Dockerfile.serverless               # 生产 Docker 镜像定义
├── runpod_worker.py                    # 核心 Handler（RunPod 入口）
├── dual_wan_i2v_api.json               # ComfyUI API 工作流模板
├── extra_model_paths.yaml              # Volume 模型路径映射
├── lora_style_registry.json            # LoRA 风格注册表（API style 参数映射）
├── start.sh                            # ComfyUI 启动脚本
├── download_models_to_volume.sh        # 首次部署：下载模型到 Network Volume
├── test_serverless_remote.py           # API 测试脚本
└── API_DOCS.md                         # 本文档
```

---

## 🔗 接口地址

```
POST https://api.runpod.ai/v2/{ENDPOINT_ID}/run              # 异步提交
GET  https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{JOB_ID}  # 查询状态
```

## 🔑 认证

```
Authorization: Bearer {RUNPOD_API_KEY}
```

---

## 📥 请求参数

### POST `/run`

```json
{
  "input": {
    "positive_prompt": "描述视频内容的正向提示词",
    "negative_prompt": "不想出现的负向提示词",
    "image_url": "https://example.com/input.png",
    "frames": 81,
    "width": 480,
    "height": 832,
    "style": "anime_cumshot(0.7,0.9),massage_tits(0.2,0.3)",
    "seed": 12345
  }
}
```

### 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `positive_prompt` | string | 否 | `"High quality anime style, masterpiece"` | 正向提示词，描述视频内容 |
| `negative_prompt` | string | 否 | `"ugly, deformation"` | 负向提示词 |
| `image_url` | string | **二选一** | - | 输入参考图片的 URL |
| `image_base64` | string | **二选一** | - | 输入图片的 Base64 编码 |
| `frames` | int | 否 | `81` | 生成帧数。21≈1.3秒, 42≈2.6秒, 81≈5秒 |
| `width` | int | 否 | `480` | 视频宽度（像素）|
| `height` | int | 否 | `832` | 视频高度（像素）|
| `style` | string | 否 | `"none"` | LoRA 风格，支持单选和多 LoRA 叠加，见 [风格参数格式](#-风格参数格式-v20-multi-lora) |
| `seed` | int | 否 | 随机 | 随机种子，固定值可复现结果 |

> ⚠️ `image_url` 和 `image_base64` 必须提供其中一个作为参考图

---

## 🎨 风格参数格式 (v2.0 Multi-LoRA)

### `style` 参数支持以下格式

| 格式 | 示例 | 说明 |
|------|------|------|
| 不使用 LoRA | `"none"` | 默认值，不加载任何 LoRA |
| 单 LoRA（默认强度） | `"anime_cumshot"` | ⬅️ 向后兼容 v1 格式，High/Low 强度均为 1.0 |
| 单 LoRA（自定义强度） | `"anime_cumshot(0.7,0.9)"` | High Noise 强度=0.7, Low Noise 强度=0.9 |
| 多 LoRA 叠加 | `"anime_cumshot(0.7,0.9),massage_tits(0.2,0.3)"` | 按顺序叠加，可无限串联 |
| 三重叠加 | `"A(0.8,0.5),B(0.3,0.2),C(0.1,0.1)"` | A → B → C 顺序执行 |

### 格式语法

```
style = "stylename(high_strength,low_strength),stylename2(high,low),..."
```

- `stylename`: LoRA 风格注册名（见下方已安装列表）
- `high_strength`: High Noise 模型的 LoRA 强度（浮点数），负责大动作、姿势
- `low_strength`: Low Noise 模型的 LoRA 强度（浮点数），负责细节、脸部、画质

### ⚠️ LoRA 叠加原则与注意事项

| 原则 | 说明 |
|------|------|
| **节点类型** | 使用 `LoraLoaderModelOnly`（不是普通 LoraLoader）|
| **双路径分离** | High Noise 和 Low Noise 分别独立叠加链 |
| **High Noise 强度** | 推荐 0.8~1.8，负责大动作/姿势/NSFW 强度 |
| **Low Noise 强度** | 推荐 0.4~1.0，过高容易模糊/崩坏 |
| **总强度上限** | 所有 LoRA 加起来别超过 1.5~2.0 |
| **叠加顺序** | 动作/姿势 LoRA 放前面，细节/画质放后面 |
| **叠加数量** | 建议 ≤3~4 个，超过容易画质模糊/脸崩 |

### 典型叠加组合推荐

```
角色 LoRA + NSFW 动作 LoRA + 画质 LoRA
风格 LoRA + 湿润/液体 LoRA
```

### 如果出现问题

| 问题 | 解决方案 |
|------|---------|
| 画面模糊 | 降低 Low Noise 强度，或降低总强度 (1.0 → 0.7 → 0.5) |
| 脸崩 | 减少叠加数量，降低 Low Noise 强度 |
| 动作混乱 | 降低 High Noise 强度总和 |
| 过曝 | 降低所有 LoRA 强度 |

---

## 📋 可用 LoRA 风格列表

### 已安装 LoRA 一览

| `style` 参数值 | 作用描述 | 来源 | 兼容性 |
|---|---|---|---|
| `"none"` | 不使用 LoRA（默认）| 内置 | 所有场景 |
| `"anime_cumshot"` | 增强动漫风格射精场景的密度、精度、冲击力和美学真实感 | [CivitAI #1869475](https://civitai.com/models/1869475) | ⚠️ 仅兼容 Wan2.2 官方 Base Model |
| `"massage_tits"` | 从背后按摩/揉捏胸部动作，支持隔衣/内衣/直接接触 | [CivitAI #1952945](https://civitai.com/models/1952945) | ⚠️ 仅兼容 Wan2.2 官方 Base Model |
| `"closeup_spread"` | POV 视角近距离展开特写（阴部+肛部），附带 bukkake 效果 | [CivitAI #2426014](https://civitai.com/models/2426014) | ⚠️ 仅兼容 Wan2.2 官方 Base Model |
| `"pussy_anus"` | 阴部/肛部细节 LoRA，支持各种角度和阴毛风格变化 | [CivitAI #2109996](https://civitai.com/models/2109996) | ⚠️ 仅兼容 Wan2.2 官方 Base Model |

### 各 LoRA 详细说明

---

#### `anime_cumshot` — Anime Cumshot Aesthetics Precision Load (I2V Beta)

**模型文件：**
- High Noise: `23High_noise-Cumshot_Aesthetics.safetensors`
- Low Noise: `56Low_noise-Cumshot_Aesthetics.safetensors`

**v2.0 调用方式（自定义强度）：**
```json
{ "input": { "style": "anime_cumshot(0.8,0.6)", "positive_prompt": "...", "image_url": "..." } }
```

**v1 兼容调用（默认强度 1.0）：**
```json
{ "input": { "style": "anime_cumshot", "positive_prompt": "...", "image_url": "..." } }
```

**⚠️ 注意事项：**
- 仅兼容 Wan2.2 官方 Base Model（不兼容 AIO / 合并模型）
- 主要作用于面部，胸部/身体为间接溅射效果
- 约 80% 成功率，偶尔有伪影，多次生成取最佳

**推荐参数：** Steps 8-10, CFG High 2.0, CFG Low 1.0, Sampler Euler

**🎭 触发提示词模板：**

| 类别 | 提示词 |
|------|--------|
| 姿势 | `A girl is kneeling.` / `sitting.` / `lying down.` / `standing.` |
| 入场 | `A man's penis enters from below.` / `from the bottom left corner.` |
| 动作 | `The man is stroking his penis. He ejaculates on her face.` |
| 质感 | `The cum is thick and sticky, clinging like paste before sliding off.` |
| 惊讶 | `She flinches, recoiling slightly, eyes widening in confusion.` |
| 接受 | `Her expression remains calm, lips slightly parted, receiving directly.` |
| 回避 | `She instinctively turns her head away.` |

---

#### `massage_tits` — Wan 2.2 Massage Tits by MQ Lab (I2V v1.0)

**模型文件：**
- High Noise: `mql_massage_tits_wan22_i2v_v1_high_noise.safetensors`
- Low Noise: `mql_massage_tits_wan22_i2v_v1_low_noise.safetensors`

**v2.0 调用方式（自定义强度）：**
```json
{ "input": { "style": "massage_tits(0.9,0.5)", "positive_prompt": "...", "image_url": "..." } }
```

**v1 兼容调用（默认强度 1.0）：**
```json
{ "input": { "style": "massage_tits", "positive_prompt": "...", "image_url": "..." } }
```

**⚠️ 注意事项：**
- 仅兼容 Wan2.2 官方 Base Model
- 如果输出视频模糊，增加 Low Noise 步数
- 如果动作太快，FPS 设为 16（当前默认 16）

**🎭 触发提示词模板：**

| 类别 | 提示词 |
|------|--------|
| 场景 | `A woman is standing naked.` / `wearing a bra.` / `in clothes.` |
| 入场 | `A man walks in from the right edge of screen.` |
| 隔衣 | `The man stands behind the woman. He massages her breasts with his hands over her clothes.` |
| 隔内衣 | `He massages her breasts with his hands over her bra.` |
| 直接 | `He massages her breasts with his hands directly.` |

---

#### `closeup_spread` — Close-up Pussy & Anus POV Hands Spreading (WAN2.2 I2V 14B) +Bukkake

**模型文件：**
- High Noise: `CloseUpSpreadCreamPai_H_Wan2-2_i2v_A14B.safetensors`
- Low Noise: `CloseUpSpreadCreamPai_L_Wan2-2_i2v_A14B.safetensors`

**v2.0 调用方式（自定义强度）：**
```json
{ "input": { "style": "closeup_spread(0.9,0.7)", "positive_prompt": "...", "image_url": "..." } }
```

**v1 兼容调用（默认强度 1.0）：**
```json
{ "input": { "style": "closeup_spread", "positive_prompt": "...", "image_url": "..." } }
```

**⚠️ 注意事项：**
- 仅兼容 Wan2.2 官方 Base Model（I2V 14B）
- 经过 2000 STEP 训练，无需指定 END 图即可生成细致展开表现
- 训练数据为真实系素材，用于动漫风格图片时如果感觉过于写实，请降低模型强度
- 动漫风格推荐强度范围：0.7~0.9（低于 0.7 描画精度会急剧下降）
- **推荐分辨率**: Portrait 832×1216 ❤️（不推荐 Square 或 Landscape）
- 训练参数：Clip=5, STEP=2000, Frame Num=42

**🎭 触发提示词模板：**

| 类别 | 提示词 |
|------|--------|
| 核心动作 | `The camera zooms in on her pussy. The camera's POV hands spread her pussy and asshole wide open.` |
| 展开描写 | `Her pussy is stretched very wide. Her asshole is stretched very wide too.` |
| 细节观察 | `We get a detailed look inside her pussy and asshole.` |
| Bukkake | `A white slime-like substance splashes over her.` |

**叠加推荐组合：**
```
"closeup_spread(0.9,0.7),anime_cumshot(0.5,0.3)"  — 展开特写 + 颜射效果
```

---

#### `pussy_anus` — Wan 2.2 Pussy and Anus LoRA (by HearmemanAI)

**模型文件：**
- High Noise: `PussyLoRA_HighNoise_Wan2.2_HearmemanAI.safetensors`
- Low Noise: `PussyLoRA_LowNoise_Wan2.2_HearmemanAI.safetensors`
- 下载格式：ZIP 压缩包，需解压后使用

**v2.0 调用方式（自定义强度）：**
```json
{ "input": { "style": "pussy_anus(0.9,0.7)", "positive_prompt": "...", "image_url": "..." } }
```

**v1 兼容调用（默认强度 1.0）：**
```json
{ "input": { "style": "pussy_anus", "positive_prompt": "...", "image_url": "..." } }
```

**⚠️ 注意事项：**
- 仅兼容 Wan2.2 官方 Base Model
- LoRA 并非完美，但当它工作时效果相当好
- 触发词主要围绕 `vagina`，**不要使用 `pussy`**（训练时未使用该词）
- 作者仅在 T2V 上测试过，I2V 未经官方测试（社区验证中）
- 使用 2×H200 并行训练
- **推荐分辨率**: Portrait 832×1216

**🎭 触发提示词模板：**

| 类别 | 提示词 |
|------|--------|
| 阴毛风格 | `Thick dense pubic hair` / `Shaved vagina` / `Trimmed pubic hair` |
| 角度 | `shaved vagina from behind` / `vagina from above` / `vagina from below` |
| 动作 | `She is spreading her labia with her fingers.` |

**叠加推荐组合：**
```
"pussy_anus(0.8,0.6),closeup_spread(0.5,0.3)"  — 阴部细节 + 展开特写
```

**📥 下载脚本（ZIP 需解压）：**
```bash
cd /workspace/my_stable_models/loras/

# ===== 1. 下载 ZIP =====
wget -O "PussyLoRA_Wan2.2_HearmemanAI.zip" \
  "https://civitai.com/api/download/models/2387016?token=YOUR_CIVITAI_TOKEN"

# ===== 2. 解压并提取 safetensors 文件 =====
unzip -o "PussyLoRA_Wan2.2_HearmemanAI.zip"

# 验证解压结果
ls -lh PussyLoRA_*Wan2.2*.safetensors

# 清理 ZIP
rm -f "PussyLoRA_Wan2.2_HearmemanAI.zip"

# ===== 3. 顺手更新 Volume 的 registry =====
# ⚠️ 执行前确保已先同步 Git 仓库的 lora_style_registry.json，防止下次发版被覆盖！
cat > /workspace/my_stable_models/lora_style_registry.json << 'EOF'
{
  "none": { "high": "none", "low": "none" },
  "anime_cumshot": {
    "high": "23High_noise-Cumshot_Aesthetics.safetensors",
    "low": "56Low_noise-Cumshot_Aesthetics.safetensors"
  },
  "massage_tits": {
    "high": "mql_massage_tits_wan22_i2v_v1_high_noise.safetensors",
    "low": "mql_massage_tits_wan22_i2v_v1_low_noise.safetensors"
  },
  "closeup_spread": {
    "high": "CloseUpSpreadCreamPai_H_Wan2-2_i2v_A14B.safetensors",
    "low": "CloseUpSpreadCreamPai_L_Wan2-2_i2v_A14B.safetensors"
  },
  "pussy_anus": {
    "high": "PussyLoRA_HighNoise_Wan2.2_HearmemanAI.safetensors",
    "low": "PussyLoRA_LowNoise_Wan2.2_HearmemanAI.safetensors"
  }
}
EOF

echo "✅ Registry updated:"
cat /workspace/my_stable_models/lora_style_registry.json
```

---

## 📤 响应格式

### 提交任务（POST `/run`）
```json
{ "id": "job-uuid-here", "status": "IN_QUEUE" }
```

### 成功（URL 方式，配置了 R2 上传时）
```json
{
  "status": "COMPLETED",
  "output": {
    "status": "success",
    "video_url": "https://vcdn.sprize.ai/videos/xxxxx.mp4",
    "video_count": 1,
    "image_count": 41,
    "parameters_used": {
      "style": "anime_cumshot(0.7,0.9),massage_tits(0.2,0.3)",
      "frames": 42,
      "..."
    },
    "lora_stack": [
      {"name": "anime_cumshot", "high_strength": 0.7, "low_strength": 0.9},
      {"name": "massage_tits", "high_strength": 0.2, "low_strength": 0.3}
    ]
  }
}
```

### 成功（Base64 方式，未配置上传地址时）
```json
{
  "status": "COMPLETED",
  "output": {
    "status": "success",
    "video_count": 1,
    "video_base64_array": ["data:video/mp4;base64,..."],
    "parameters_used": { "..." }
  }
}
```

### 失败
```json
{ "status": "FAILED", "error": "错误详情..." }
```

---

## 💻 实际调用案例

> 以下案例基于当前已部署的 Endpoint

### 案例 1: 无 LoRA 基础生成（42帧）

```bash
curl -X POST "https://api.runpod.ai/v2/{ENDPOINT_ID}/run" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "positive_prompt": "A beautiful woman walking on the beach, cinematic lighting, high quality",
      "negative_prompt": "ugly, blurry, low resolution, bad hands, deformation",
      "image_url": "https://files.catbox.moe/9yx65r.png",
      "style": "none",
      "frames": 42,
      "width": 480,
      "height": 832
    }
  }'
```

---

### 案例 2: 单 LoRA 自定义强度

```bash
curl -X POST "https://api.runpod.ai/v2/{ENDPOINT_ID}/run" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "positive_prompt": "A girl is kneeling...",
      "image_url": "https://files.catbox.moe/9yx65r.png",
      "style": "anime_cumshot(0.8,0.6)",
      "frames": 42
    }
  }'
```

---

### 案例 3: 多 LoRA 叠加（v2.0 新功能）

```bash
curl -X POST "https://api.runpod.ai/v2/{ENDPOINT_ID}/run" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "positive_prompt": "A woman is standing naked. A man walks in...",
      "negative_prompt": "ugly, blurry, low resolution",
      "image_url": "https://files.catbox.moe/9yx65r.png",
      "style": "anime_cumshot(0.7,0.9),massage_tits(0.2,0.3)",
      "frames": 42,
      "width": 480,
      "height": 832
    }
  }'
```

> 🔗 LoRA 加载链路：
> - **High Noise**: UNET-H → anime_cumshot(0.7) → massage_tits(0.2) → Sampler
> - **Low Noise**: UNET-L → anime_cumshot(0.9) → massage_tits(0.3) → Sampler

---

### 案例 4: Python 完整调用脚本（含 Multi-LoRA）

```python
import requests, time, base64, os

API_KEY = os.environ.get("RUNPOD_API_KEY", "")
ENDPOINT_ID = "your_endpoint_id"
BASE = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 1. 提交 - 多 LoRA 叠加
resp = requests.post(f"{BASE}/run", headers=HEADERS, json={
    "input": {
        "positive_prompt": "A woman dancing gracefully, cinematic",
        "negative_prompt": "ugly, blurry",
        "image_url": "https://files.catbox.moe/9yx65r.png",
        "style": "anime_cumshot(0.7,0.9),massage_tits(0.2,0.3)",
        "frames": 42
    }
}, timeout=30)
job_id = resp.json()["id"]
print(f"Job: {job_id}")

# 2. 轮询
while True:
    time.sleep(5)
    data = requests.get(f"{BASE}/status/{job_id}", headers=HEADERS).json()
    print(f"  [{time.strftime('%H:%M:%S')}] {data['status']}")

    if data["status"] == "COMPLETED":
        output = data["output"]
        # LoRA 叠加详情
        if output.get("lora_stack"):
            print(f"LoRA Stack: {output['lora_stack']}")
        # 视频 URL 方式
        if output.get("video_url"):
            print(f"✅ 下载: {output['video_url']}")
        # Base64 方式
        elif output.get("video_base64_array"):
            b64 = output["video_base64_array"][0].split(",", 1)[1]
            with open("output.mp4", "wb") as f:
                f.write(base64.b64decode(b64))
            print("✅ 已保存: output.mp4")
        break
    elif data["status"] == "FAILED":
        print(f"❌ {data.get('error')}")
        break
```

---

## 🔧 添加新 LoRA（完整流程）

> ⚠️ **重要原则：Git 仓库的 `lora_style_registry.json` 是主版本！**
> 
> 每次新 Worker 启动时，Docker 镜像内置的 registry 会**自动覆盖** Volume 上的 registry。
> 因此必须**先更新 Git 仓库**，再更新 Volume，否则下次发版 Volume 上的改动会丢失。

### 完整流程图

```
  ① 先更新 Git 仓库: lora_style_registry.json  ← 主版本，发版时自动同步到 Volume
  ② SSH 到 Pod 一条龙操作：
     - 下载 .safetensors 到 /runpod-volume/my_stable_models/loras/
     - 顺手更新 Volume 上的 lora_style_registry.json（立即生效）
         ↓
  ③ 重启 Workers（删除旧 Worker，让系统重新分配）
         ↓
  ④ 测试 API 调用
```

### Step 1: 先更新 Git 仓库的注册表（⚠️ 必须先做！）

> 🚨 **如果跳过这步直接改 Volume，下次 Docker 镜像发版后你的改动会被覆盖！**

在本地修改 `lora_style_registry.json`，添加新 LoRA 条目：

```json
{
  "none": { "high": "none", "low": "none" },
  "anime_cumshot": {
    "high": "23High_noise-Cumshot_Aesthetics.safetensors",
    "low": "56Low_noise-Cumshot_Aesthetics.safetensors"
  },
  "massage_tits": {
    "high": "mql_massage_tits_wan22_i2v_v1_high_noise.safetensors",
    "low": "mql_massage_tits_wan22_i2v_v1_low_noise.safetensors"
  },
  "closeup_spread": {
    "high": "CloseUpSpreadCreamPai_H_Wan2-2_i2v_A14B.safetensors",
    "low": "CloseUpSpreadCreamPai_L_Wan2-2_i2v_A14B.safetensors"
  },
  "your_new_style": {
    "high": "YourLora_High.safetensors",
    "low": "YourLora_Low.safetensors"
  }
}
```

然后提交推送：

```bash
git add lora_style_registry.json
git commit -m "feat: add your_new_style LoRA"
git push
```

### Step 2: SSH 到 Pod 一条龙操作（下载文件 + 注册）

> Wan2.2 的 LoRA 通常有 **两个文件**：High Noise 和 Low Noise

1. 在 RunPod 开一台 **CPU Pod**（最便宜），挂载 Network Volume `unhappy_black_raven`
2. 在 Pod Terminal 中**一条龙执行**：

```bash
cd /workspace/my_stable_models/loras/

# ===== 1. 下载 LoRA 文件 =====
# 替换 XXXXX/YYYYY 为 CivitAI Model Version ID，TOKEN 为 CivitAI API Token
wget -O "YourLora_High.safetensors" "https://civitai.com/api/download/models/XXXXX?token=YOUR_CIVITAI_TOKEN"
wget -O "YourLora_Low.safetensors" "https://civitai.com/api/download/models/YYYYY?token=YOUR_CIVITAI_TOKEN"

# 验证文件
ls -lh *.safetensors

# ===== 2. 顺手注册到 Volume 的 registry（与 Git 仓库保持一致）=====
# ⚠️ 内容必须和 Git 仓库的 lora_style_registry.json 完全一致！
cat > /workspace/my_stable_models/lora_style_registry.json << 'EOF'
{
  "none": { "high": "none", "low": "none" },
  "anime_cumshot": {
    "high": "23High_noise-Cumshot_Aesthetics.safetensors",
    "low": "56Low_noise-Cumshot_Aesthetics.safetensors"
  },
  "massage_tits": {
    "high": "mql_massage_tits_wan22_i2v_v1_high_noise.safetensors",
    "low": "mql_massage_tits_wan22_i2v_v1_low_noise.safetensors"
  },
  "closeup_spread": {
    "high": "CloseUpSpreadCreamPai_H_Wan2-2_i2v_A14B.safetensors",
    "low": "CloseUpSpreadCreamPai_L_Wan2-2_i2v_A14B.safetensors"
  },
  "your_new_style": {
    "high": "YourLora_High.safetensors",
    "low": "YourLora_Low.safetensors"
  }
}
EOF

# 验证 registry
echo "✅ Registry:"
cat /workspace/my_stable_models/lora_style_registry.json
```

> 💡 **为什么要在 Volume 上也更新？** 因为这样**不需要等 Docker 镜像重新构建**就能立即使用新 LoRA。
> Worker 启动时会用 Docker 镜像内的 registry 覆盖 Volume 上的，所以只要 Git 仓库已同步，就不会丢失。

### Step 3: 重启 Workers

在 RunPod Endpoint → Workers 页面：
1. 删除所有现有 Workers
2. 等系统自动分配新 Worker
3. 新 Worker 启动时会自动同步 registry 到 Volume（从 Docker 镜像内）

### Step 4: 测试

```bash
python3 test_serverless_remote.py
```

### Step 5: 更新本文档

在上方 [已安装 LoRA 一览](#已安装-lora-一览) 表格中添加新行，并添加对应的详细说明章节。

> **📋 Registry 同步机制总结：**
> 
> | 来源 | 路径 | 角色 |
> |------|------|------|
> | Git 仓库 | `lora_style_registry.json` | 🏠 **主版本**（打包进 Docker 镜像）|
> | Docker 镜像 | `/workspace/lora_style_registry.json` | 📦 构建时从 Git 复制 |
> | Network Volume | `/runpod-volume/my_stable_models/lora_style_registry.json` | 🔄 运行时由 Worker 自动从镜像同步 |
> 
> **数据流向：** Git → Docker 镜像 → Worker 启动时自动覆盖 Volume

---

## ⚙️ 技术规格

| 项目 | 规格 |
|------|------|
| 基础模型 | Wan2.2 NSFW FastMove V2 (14B fp8) |
| GPU | RTX 5090 / RTX 4090 / L4 / A6000（均兼容）|
| CUDA | 12.8.1 |
| PyTorch | 2.8.0 |
| 输出格式 | MP4 (H.264, yuv420p) |
| 帧率 | 16 FPS |
| 视频存储 | Cloudflare R2（永久存储）|
| Docker 镜像 | `ghcr.io/metaloan/okbox-comfy:serverless-multilora-v1.01` |
| Network Volume | `unhappy_black_raven` (EU-RO-1) |
| Worker 版本 | v2.0-multilora |

---

## 🚀 首次部署指南

### 1. 准备 Network Volume

```bash
# 在 RunPod 创建 Network Volume，然后开一台 Pod 挂载它
# 在 Pod Terminal 里运行模型下载脚本
curl -sL https://raw.githubusercontent.com/MetaLoan/okbox-comfy/main/download_models_to_volume.sh | bash
```

### 2. 创建 Serverless Endpoint

- **Container Image**: `ghcr.io/metaloan/okbox-comfy:serverless-multilora-v1.01`
- **Network Volume**: 挂载到 `/runpod-volume`
- **环境变量**（可选）：
  ```
  R2_ACCOUNT_ID = your_account_id
  R2_ACCESS_KEY_ID = your_access_key
  R2_ACCESS_KEY_SECRET = your_secret_key
  R2_BUCKET = your_bucket
  R2_PUBLIC_URL = https://your-cdn.example.com
  ```

### 3. 升级 Docker 镜像

修改 `.github/workflows/docker-build.yml` 中的 tag 版本号，push 到 main 分支会自动触发 GitHub Actions 打包。

---

## 🆕 v2.0 更新日志

### Multi-LoRA 叠加 (serverless-multilora-v1.01)

**新特性：**
- ✅ 支持多 LoRA 叠加：`style="A(0.7,0.9),B(0.2,0.3),C(0.1,0.2)"`
- ✅ 每个 LoRA 可独立设置 High Noise 和 Low Noise 强度
- ✅ 无限叠加支持（按顺序串联 LoraLoaderModelOnly 节点）
- ✅ 完全向后兼容 v1 单 LoRA 格式：`style="anime_cumshot"`
- ✅ 响应中新增 `lora_stack` 字段，显示 LoRA 叠加详情

**技术实现：**
- High Noise 路径和 Low Noise 路径分别独立叠加
- 使用 `LoraLoaderModelOnly` 节点（非普通 LoraLoader）
- 动态生成节点 ID（200+），避免与固定节点冲突
- 解析器支持正则匹配：`stylename(high,low)` 格式

---

## ❌ 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------| 
| `No input image provided` | 未提供参考图 | 添加 `image_url` 或 `image_base64` |
| `Style 'xxx' not found` | LoRA 未注册 | 检查 Volume 上的 `lora_style_registry.json` |
| `Invalid LoRA style format` | style 格式错误 | 检查格式：`name(high,low)` |
| `lora_name: 'xxx' not in []` | LoRA 文件未下载到 Volume | 下载 .safetensors 到 loras 目录 |
| `ComfyUI rejected the workflow` | 工作流验证失败 | 检查 RunPod Logs |
| `CUDNN_STATUS_NOT_SUPPORTED` | GPU 不兼容 | 使用 multilora-v1+ 镜像（CUDA 12.8）|
