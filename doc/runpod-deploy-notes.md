# WAN 2.2 角色图生视频 (I2V) 终极部署指南

> **目标需求**：传一张角色图片 + 分场景秒级提示词 -> 自动生成 6-12s 的 480P 真人写实 NSFW 视频

---

## ⚡️ 进阶：真·一键无人值守终极部署指令 (RunPod 专供)

为了彻底解决繁琐的环境配置、填平主盘爆满大坑，以及硬核穿透 C 站 (Civitai) 刁钻的 API Key 拦截与 Cloudflare 防爬虫机制，我们已经把所有部署逻辑彻底黑盒化。

在新开的 RunPod 终端（Web Terminal）内，您什么都不用配置，**只需要复制并运行以下这段指令，即可放手不管、全自动完工**：

```bash
curl -s -L "https://raw.githubusercontent.com/MetaLoan/okbox-comfy/main/ultimate_setup.sh?v=\$RANDOM" | bash
```

> **🌟 温馨提示**：
> 这个长线脚本内置了**动态副盘嗅探、灾难级错误重试、和底层自动避障重定向挂载**。不论是刚租的纯净机器，还是被装废了的旧环境，跑完后把配套打磨好的 `zzzz_last-60FPS-wan22_workflow_FIXED_V5.json` 甩进去就能点亮全部绿灯，直接开出 60FPS 极速成片！

---

## 🚀 极简骨架版：Dual Wan I2V 专用部署指令

如果您仅仅只使用化繁为简的纯净版工作流 `dual_wan_i2v.json`（仅仅保留主副双节点，去掉了所有干扰的高级 LoRA 和多余第三方查偏节点），请使用下面这个**超级轻量级脱水版脚本**！

👉 **它剥离了几十个 G 的非必要环境包，只精准下达最核心的几个张量引擎！速度快三倍！且内部已经集成了一键升级内核以防止旧版 FP8 解码器崩溃崩爆显存的终极防护代码：**

```bash
curl -s -L "https://raw.githubusercontent.com/MetaLoan/okbox-comfy/main/setup_dual_wan_i2v.sh?v=\$RANDOM" | bash
```
> **🌟 注意事项**：执行完毕以后，如果是旧容器一定记得按下 Web 界面的 **Restart（重启核心）** 按钮，让底层的 FP8 自动升级代码生效。

---

## 🏗️ 核心底层逻辑与镜像选择

最致命的踩坑：**不要尝试使用任何打包好 ComfyUI 的第三方神仙 Docker 镜像。**
跑视频的核心是环境纯净，如果必须用包，推荐内置了 Manager 等依赖的完整包，但在跑双路流的时候，需要注意自己补充官方原版模型。

👉 这套方案已经验证：**使用官方或 `cu126-megapak`**，补齐所有的特定依赖。必须配 24GB 显存（如 RTX 4090）。

### 0️⃣ 前期：需要补充的缺失模型（必须下载）
如果你使用的是第三方打包库或者空白机器，除了主干模型，这个图生视频工作流 **严格依赖** 以下三个基础组件：
1. **VAE 解码器**: `wan_2.1_vae.safetensors` (放入 `/models/vae/`)
2. **Text Encoder (T5)**: `umt5_xxl_fp8_e4m3fn_scaled.safetensors` (放入 `/models/text_encoders/`)
3. **视觉眼模型 (Image2Video 强依赖)**: `clip_vision_h.safetensors` (放入 `/models/clip_vision/`)
*（可直接在 ComfyUI Manager 中点 Install Models 下载，或者从 `Comfy-Org` 的 HuggingFace 直链全部 wget 下载。）*

---

## 🚀 1. 主副模型（H & L）真实下载防坑指南

要跑出极致丝滑防崩坏的色色运镜，必须使用双路（Dual KSampler）架构，同时需要载入 14GB 的 `High` 模型和 14GB 的 `Low` 模型。

**⚠️ 致命踩坑 1：下载到的文件只有 26 字节？**
在 CivitAI 下载时，主模型（H）可以直接通过网页主下载按钮的后台版本号 API 抓取（ID: 2477539），但 **副模型（L）的后台版本号是被隐藏在另一个下拉选项里的，真实 ID 是 2477548！**
如果下载代码写错，只会下载到一个 `{"error": "Model not found"}` 的 26 字节空壳。这会导致之后 ComfyUI 读取抛出 `GGUF magic invalid` 魔数错误！

**⚠️ 致命踩坑 2：是 Safetensors 还是 GGUF？**
官方直链下载的高清满血原版，格式为 `.safetensors`。
千万**不要**使用原作者 JSON 里内置的外部非标 `UnetLoaderGGUF` 节点去读！如果你的文件是纯血的 `.safetensors`，请直接在 ComfyUI 里调出最官方标准的 **`Load Diffusion Model (UNETLoader)`** 节点去挂载它们。

---

## 🎬 2. 核心双模工作流（Dual KSampler）生死顺序

要在仅 4 步内压榨出极点画质，原作者采取的“闪电版双拼”逻辑**彻底违背常理**！普通画师极容易接反管线导致输出四分五裂的“花屏”或乱码：

### 🩸 正确的双路交接模型顺序：
1. **第一发（HIGH 模）上大底噪：** 
   - 必须先上 `WAN2.2-NSFW-FastMove-V2-H`。
   - `KSampler Advanced` 设定：`add_noise: enable`，`start_at_step: 0`，`end_at_step: 2`。
   - 作用：带着剧烈的高斯噪声，重手砸下整个视频的每一帧物理大框架结构。

2. **第二发（LOW 模）跑平滑：**
   - 接过 HIGH 生成的带噪 Latent。
   - 换成 `WAN2.2-NSFW-FastMove-V2-L` 模型。
   - `KSampler Advanced` 设定：`add_noise: disable`，`start_at_step: 2`，`end_at_step: 4`。
   - 作用：不要加新噪声，在此基础上去锯齿、降噪、平滑动作进行收尾。

### 模型基础参数生死线：
- **CFG Scale（强提醒）**: 必须设为 **1.0**！数值一旦超出 1.0，画面当场扭曲炸裂。
- **Lightning LoRA**：千万**不要**私自叠放提速 LoRA，主副模型内核已全盘烘焙自带！再加即糊。

---

## 💡 3. “花屏”与“极度对抗”终极除错手段

1. **画面变成红绿块、或是大灰板马赛克（花屏）**：
   - 100% 是你在第一个 KSampler 处，错误地关闭了底噪（填了 `add_noise: disable`）。必须要 `enable` 让扩散模型生成正确的起始雪花！
2. **画面四分五裂、人和床融合变形（特征撕裂）**：
   - 因为只允许生成短短 4 步算力，如果**你的起始垫图特征**（如日系二次元图片）和**你的 0 秒提示词**（如要求 realistic real skin 等真发）发生了牛头不对马嘴的对抗，模型算力瞬间崩溃。
   - **解决**：在你的提示词打头阵处补充 `anime style`，并确保初始提示词严格包合垫图的动作基准。
3. **想要加防畸变的“负面提示词”**：
   - 因为 CFG 被我们锁死了 1，ComfyUI 自带的负面提示词全自动**失效**！必须使用 `kjnodes` 里的神器 **`WAN Nag`** 节点接在前面，才能输入例如 `wobbling effect, exaggerated butt movement...` 等专用排错咒语。
