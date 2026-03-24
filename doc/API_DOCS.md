# Okbox ComfyUI Serverless API 文档

> 基于 RunPod Serverless 的 Wan2.2 视频生成 API
>
> 最后更新: 2026-03-23

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
    "style": "none",
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
| `style` | string | 否 | `"none"` | LoRA 风格名称，见 [风格列表](#-可用-lora-风格列表) |
| `seed` | int | 否 | 随机 | 随机种子，固定值可复现结果 |

> ⚠️ `image_url` 和 `image_base64` 必须提供其中一个作为参考图

---

## 🎨 可用 LoRA 风格列表

### 已安装 LoRA 一览

| `style` 参数值 | 作用描述 | 来源 | 兼容性 |
|---|---|---|---|
| `"none"` | 不使用 LoRA（默认）| 内置 | 所有场景 |
| `"anime_cumshot"` | 增强动漫风格射精场景的密度、精度、冲击力和美学真实感 | [CivitAI #1869475](https://civitai.com/models/1869475) | ⚠️ 仅兼容 Wan2.2 官方 Base Model |
| `"massage_tits"` | 从背后按摩/揉捏胸部动作，支持隔衣/内衣/直接接触 | [CivitAI #1952945](https://civitai.com/models/1952945) | ⚠️ 仅兼容 Wan2.2 官方 Base Model |

### 各 LoRA 详细说明

---

#### `anime_cumshot` — Anime Cumshot Aesthetics Precision Load (I2V Beta)

**模型文件：**
- High Noise: `23High_noise-Cumshot_Aesthetics.safetensors`
- Low Noise: `56Low_noise-Cumshot_Aesthetics.safetensors`

**调用方式：**
```json
{ "input": { "style": "anime_cumshot", "positive_prompt": "...", "image_url": "..." } }
```

**⚠️ 注意事项：**
- 仅兼容 Wan2.2 官方 Base Model（不兼容 AIO / 合并模型）
- LoRA Strength 固定为 1.0
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

**调用方式：**
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

## 📤 响应格式

### 提交任务（POST `/run`）
```json
{ "id": "job-uuid-here", "status": "IN_QUEUE" }
```

### 成功（URL 方式，配置了 VIDEO_UPLOAD_URL 时）
```json
{
  "status": "COMPLETED",
  "output": {
    "status": "success",
    "video_url": "https://okbox-video-storage.fly.dev/v/xxxxx.mp4",
    "video_count": 1,
    "image_count": 41,
    "parameters_used": { "style": "anime_cumshot", "frames": 42, ... }
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
    "parameters_used": { ... }
  }
}
```

### 失败
```json
{ "status": "FAILED", "error": "错误详情..." }
```

---

## 💻 实际调用案例

> 以下案例基于当前已部署的 Endpoint `dql6hm5rdakt22`

### 案例 1: 无 LoRA 基础生成（42帧）

```bash
# 提交任务
curl -X POST "https://api.runpod.ai/v2/dql6hm5rdakt22/run" \
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

# 响应
# {"id": "4a2c423d-61f4-48b7-8e38-659c5aea2baa-e2", "status": "IN_QUEUE"}

# 轮询状态
curl "https://api.runpod.ai/v2/dql6hm5rdakt22/status/4a2c423d-61f4-48b7-8e38-659c5aea2baa-e2" \
  -H "Authorization: Bearer $RUNPOD_API_KEY"

# 成功响应
# {
#   "status": "COMPLETED",
#   "output": {
#     "status": "success",
#     "video_count": 1,
#     "image_count": 41,
#     "parameters_used": {
#       "frames": 42, "width": 480, "height": 832,
#       "style": "none", "seed": 4469877177201263,
#       "positive_prompt": "...", "negative_prompt": "..."
#     },
#     "video_base64_array": ["data:video/mp4;base64,AAAAIGZ0eXBpc29t..."]
#   }
# }
```

**实测耗时：** ~20 秒（RTX 5090），~30 秒（RTX 4090）

---

### 案例 2: Anime Cumshot LoRA（42帧）

```bash
curl -X POST "https://api.runpod.ai/v2/dql6hm5rdakt22/run" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "positive_prompt": "A girl is kneeling. A mans penis enters from below. The man is stroking his penis. He ejaculates on her face. The cum is thick and sticky, clinging like paste before sliding off. As her face is hit, she flinches, recoiling slightly, eyes widening in confusion.",
      "negative_prompt": "ugly, blurry, low resolution, bad hands, deformation",
      "image_url": "https://files.catbox.moe/9yx65r.png",
      "style": "anime_cumshot",
      "frames": 42,
      "width": 480,
      "height": 832
    }
  }'

# 成功响应（实测）
# {
#   "status": "COMPLETED",
#   "executionTime": 18044,
#   "output": {
#     "status": "success",
#     "video_count": 1, "image_count": 41,
#     "parameters_used": {
#       "style": "anime_cumshot", "seed": 72060170292103,
#       "frames": 42, "width": 480, "height": 832
#     }
#   }
# }
```

**实测耗时：** ~18 秒

---

### 案例 3: Massage Tits LoRA（42帧）

```bash
curl -X POST "https://api.runpod.ai/v2/dql6hm5rdakt22/run" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "positive_prompt": "A woman is standing naked. A man walks in from the right edge of screen. The man stands behind the woman. The man has his hands around the woman from behind and massages her breasts with his hands directly.",
      "negative_prompt": "ugly, blurry, low resolution, bad hands, deformation",
      "image_url": "https://files.catbox.moe/9yx65r.png",
      "style": "massage_tits",
      "frames": 42,
      "width": 480,
      "height": 832
    }
  }'

# 成功响应（实测）
# {
#   "status": "COMPLETED",
#   "output": {
#     "status": "success",
#     "video_count": 1, "image_count": 41,
#     "parameters_used": {
#       "style": "massage_tits", "seed": 7927525759742314,
#       "frames": 42, "width": 480, "height": 832
#     }
#   }
# }
```

**实测耗时：** ~30 秒

---

### 案例 4: Python 完整调用脚本

```python
import requests, time, base64, os

API_KEY = os.environ.get("RUNPOD_API_KEY", "")
ENDPOINT_ID = "dql6hm5rdakt22"
BASE = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 1. 提交
resp = requests.post(f"{BASE}/run", headers=HEADERS, json={
    "input": {
        "positive_prompt": "A woman dancing gracefully, cinematic",
        "negative_prompt": "ugly, blurry",
        "image_url": "https://files.catbox.moe/9yx65r.png",
        "style": "none",
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
        # 视频 URL 方式（配置了 Fly.io 时）
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

> ⚠️ **添加 LoRA 需要三个地方同步更新，缺一不可！**

### 完整流程图

```
CivitAI 下载 LoRA 文件
        ↓
  ① Network Volume: /runpod-volume/my_stable_models/loras/  ← 放 .safetensors 文件
  ② Network Volume: /runpod-volume/my_stable_models/lora_style_registry.json  ← 注册 style 名
  ③ Git 仓库: lora_style_registry.json  ← 同步更新（新 Worker 启动时用）
        ↓
  重启 Workers（删除旧 Worker，让系统重新分配）
        ↓
  测试 API 调用
```

### Step 1: 下载 LoRA 文件到 Network Volume

> Wan2.2 的 LoRA 通常有 **两个文件**：High Noise 和 Low Noise

1. 在 RunPod 开一台 **CPU Pod**（最便宜），挂载 Network Volume `unhappy_black_raven`
2. 在 Pod Terminal 中执行：

```bash
cd /workspace/my_stable_models/loras/

# 下载（替换 XXXXX/YYYYY 为 CivitAI Model Version ID，TOKEN 为 CivitAI API Token）
wget -O "YourLora_High.safetensors" "https://civitai.com/api/download/models/XXXXX?token=YOUR_CIVITAI_TOKEN"
wget -O "YourLora_Low.safetensors" "https://civitai.com/api/download/models/YYYYY?token=YOUR_CIVITAI_TOKEN"

# 验证
ls -lh *.safetensors
```

> 💡 **如何获取 Model Version ID？** 在 CivitAI 模型页面的下载链接中，`/models/XXXXX` 中的数字就是。或用 API：
> `curl -s "https://civitai.com/api/v1/models/MODEL_ID" | python3 -c "import json,sys; [print(f'{v[\"name\"]}: {v[\"id\"]}') for v in json.load(sys.stdin)['modelVersions']]"`

### Step 2: 更新 Network Volume 上的注册表

```bash
# 在同一个 Pod 里编辑
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
  "your_new_style": {
    "high": "YourLora_High.safetensors",
    "low": "YourLora_Low.safetensors"
  }
}
EOF
```

### Step 3: 同步更新 Git 仓库的注册表

在本地修改 `lora_style_registry.json`（与 Volume 上保持一致），然后：

```bash
git add lora_style_registry.json
git commit -m "feat: add your_new_style LoRA"
git push
```

> ⚠️ **为什么要两处都更新？**
> - Volume 上的注册表 = 运行中的 Worker 实时读取
> - Git 仓库的注册表 = 新 Docker 镜像打包时嵌入，作为 fallback

### Step 4: 重启 Workers

在 RunPod Endpoint → Workers 页面：
1. 删除所有现有 Workers
2. 等系统自动分配新 Worker
3. 新 Worker 启动后会扫描 `/runpod-volume/my_stable_models/loras/` 发现新文件

### Step 5: 测试

```bash
python3 test_serverless_remote.py
# 或修改 test_serverless_remote.py 中的 style 和 prompt 直接测试
```

### Step 6: 更新本文档

在上方 [已安装 LoRA 一览](#已安装-lora-一览) 表格中添加新行，并添加对应的详细说明章节。

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
| 视频存储 | Fly.io（72小时自动清理）|
| Docker 镜像 | `ghcr.io/metaloan/okbox-comfy:serverless-v8` |
| Network Volume | `unhappy_black_raven` (EU-RO-1) |

---

## 🚀 首次部署指南

### 1. 准备 Network Volume

```bash
# 在 RunPod 创建 Network Volume，然后开一台 Pod 挂载它
# 在 Pod Terminal 里运行模型下载脚本
curl -sL https://raw.githubusercontent.com/MetaLoan/okbox-comfy/main/download_models_to_volume.sh | bash
```

### 2. 创建 Serverless Endpoint

- **Container Image**: `ghcr.io/metaloan/okbox-comfy:serverless-v8`
- **Network Volume**: 挂载到 `/runpod-volume`
- **环境变量**（可选，启用视频 URL 回传）：
  ```
  VIDEO_UPLOAD_URL = https://your-video-storage-app.fly.dev/upload
  VIDEO_UPLOAD_TOKEN = 你生成的随机token
  ```

### 3. 升级 Docker 镜像

修改 `.github/workflows/docker-build.yml` 中的 tag 版本号，push 到 main 分支会自动触发 GitHub Actions 打包。

---

## ❌ 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `No input image provided` | 未提供参考图 | 添加 `image_url` 或 `image_base64` |
| `Style 'xxx' not found` | LoRA 未注册 | 检查 Volume 上的 `lora_style_registry.json` |
| `lora_name: 'xxx' not in []` | LoRA 文件未下载到 Volume | 下载 .safetensors 到 loras 目录 |
| `ComfyUI rejected the workflow` | 工作流验证失败 | 检查 RunPod Logs |
| `CUDNN_STATUS_NOT_SUPPORTED` | GPU 不兼容 | 使用 v8+ 镜像（CUDA 12.8）|
