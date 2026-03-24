# Wan 2.2 增强版模型介绍与使用指南

本文档旨在详细介绍 **Wan 2.2 Enhanced (NSFW / SVI / Camera Prompt Adherence / Lightning Edition I2V & T2V)** 这一多功能且功能强大的模型。该模型针对不同的使用场景（如 SVI 长视频、NSFW 内容生成、动态运镜等）衍生出了多个专属优化版本，并在大部分版本中内置了 Lightning LoRA 加速机制。

---

## ⚠️ 重要注意事项 (必读)

1. **Lightning LoRA 内置情况**：**除 SVI 模型外**，所有模型均已**内置** Lightning LoRA 加速。
2. **切勿重复叠加**：对于已经内置 Lightning 的模型，**绝对不要**再额外加载 Lightning LoRA，否则会导致视频画质严重下降。
3. **针对 SVI**：SVI 模型未内置 Lightning。如果您希望在生成长视频时加快速度，或者解决慢动作问题，可以手动加载 Lightning LoRAs。

---

## 核心版本分类与特性

### 1. 🟣 SVI (Stable-Video-Infinity) 兼容版
此版本专门为兼容 SVI LoRA 打造，非常适合生成**长视频**并保持角色高度一致性。

* **双版本可选**：
  * **Fast Move (FM - 快速移动)**：动作更快、更动态。其 NSFW 场景表现与 CF 版有所不同。
  * **Consistent Face (CF - 稳定面部)**：画质略胜一筹，特别适合**动漫风格 (Anime)**。
* **高低频混合 (High/Low)**：为了更灵活地控制，您可以混合使用：
  * FM (High) + CF (Low)
  * CF (High) + FM (Low)
* **优缺点分析**：
  * **优点 (Strengths)**：生成长视频的最佳方案、非凡的视频片段过渡、画质退化大幅减少、由于模型能记住上一段视频信息，因此能保持极强的角色一致性。
  * **缺点 (Weaknesses)**：对提示词和运镜的理解偏弱、视频动态感较少、容易出现慢动作效果（可通过搭配 Lightning LoRA 或三步 KSampler 工作流改善）。

### 2. 🟣 Lightning 版 - NSFW I2V V2
此版本注重人物动态及 NSFW 场景下的表现，分为两个子版本供不同需求选择。

* **NSFW Fast Move V2**：
  * 更好的提示词和摄像机运镜理解。
  * 大幅减少了在非性暗示场景下身体无意义的来回摇摆。
  * 改进了局部的物理弹跳效果。
  * 为那些需要更强动态效果和更多动作场景的用户设计。
* **NSFW V2**：
  * 相较于 Fast Move 版，较弱的运镜控制和理解。
  * 身体动作（如胸部和臀部）更加收敛。
  * 保留了 V1 版本的精髓，适合偏好 V1 表现的用户。

### 3. 🟣 相机与提示词优化版 (Camera & Prompt Improvements)
针对运镜 (Camera) 和提示词连跑做了特别优化的大幅增强版本。

* 能极好地理解提示词及场景构图。
* **支持极其丰富的运镜**：
  * **缩放 (Zoom/Dolly)**: `zoom in`, `dolly out`, `crash zoom`...
  * **平移 (Pan)**: `pan left`, `sweeping pan right`...
  * **俯仰角 (Tilt)**: `tilt up`, `tilt down`...
  * **轨迹/环绕 (Tracking/Orbit)**: `360° orbit`, `tracking shot`, `arc shot`...
  * **其他**: `static shot` (静态), `handheld shot` (手持感运镜)...

---

## ⚙️ 推荐参数设置

为了获得最完美的生成效果，无论您使用哪个子版本（T2V也适用），强烈推荐以下基础参数：

* **Steps (步数)**: **2 + 2** （对于串联的双 KSampler），有用户也推荐 `2 (High) + 3 (Low)` 效果更佳。
* **Sampler (采样器)**: **Euler simple**
* **CFG (提示词引导系数)**: **1.0** （**非常重要：在CFG为1时，基础的负面提示词组件是失效的**）

---

## 🛠 高级操作与建议

### 关于负面提示词 (Negative Prompt)
**警告**：启用负面提示词会使生成时间**翻倍**。尽量只在必须避免某种画面出现时才启用。
由于官方推荐的 CFG 为 1，默认情况下无法使用负面提示词。
**如何开启**：
1. 通过 ComfyUI Manager 安装 `kjnode`。
2. 在工作流中添加 `WAN Nag` 节点。
3. 将该节点连接在 LoRA Loader 之后，并向其输入负面提示词。
4. 然后将其连接到第一个 kSampler (High)。

### 如何处理慢动作及增加动态感 (Dynamic Prompts)
1. **工作流层面**：使用 Triple KSampler (三步 KSampler) 工作流能使动作更丰富并避免慢动作，但代价是生成时间更长。
2. **动态提示词技巧**：
   使用时间轴格式的动态提示词能够非常有效地对动作轨迹进行控场，例如：
   ```text
   (At 0 seconds: Wide shot showing a man walking down a street...)
   (At 1 second: Suddenly, a giant dragon bursts from the sky...)
   (At 2 seconds: Medium shot from the side, the man stumbles backward...)
   ```
   **Tips**: 可以借助 ChatGPT (处理 SFW) 或 Grok (支持 NSFW) 以及 Qwen-VL 等大语言模型来帮忙编写、修改这种带有时间轴的动态提示词结构。

### SVI 搭配 Lightning LoRA 推荐组合 (可选)
如果使用 SVI 并希望提速或控制退化，可使用如下方案：
* **Combo 1 - 极致动态 (运动多但画质退化快)**:
  * High: Lightx2v I2V 14B 480p distill (权重: 4)
  * Low: Wan2.2-Lightning 4steps / Wan2.2 distill low noise (权重: 1.4)
* **Combo 2 - 画质优先 (减少退化)**:
  * High: Lightning-lora massive speed up (权重: 1)
  * Low: Wan2.2 distill low noise (权重: 1)
* **Combo 3 - 均衡配置**:
  * High: Lightx2v I2V 14B 480p distill (权重: 3)
  * Low: Lightx2v I2V 14B 480p distill (权重: 1.5)

### 动漫风格 (Anime Style) 提示
如果您致力于生成 Anime 风格，为了保持面部稳定性，强烈建议尝试以下 LoRA（**仅作用于 Low Noise 部分**，强度推荐控制在 `0.3` 左右，不要太高以免破坏面部）：
* Live-wallpaper-style
* Wan22-2d-animation-effects-2d
* Wan-22-live2d-background

---

## 🔗 相关工作流推荐 (ComfyUI Workflows)
* **适合 SVI 长视频**：推荐使用 Kijai 版本的 SVI Workflow，或更为简单的 fmlf 的版本。
* **常规与动态运镜**：社区里带有 2或3 个串接 KSampler 的定制工作流。
* **原生带有内联 LoRA 的版本体验**：可以使用作者提供的基础工作流搭载 First/Last Frame，通过放大算法和局部重绘达到极致分辨率。

> *如果您在生成特定动作时遇到人物形变问题，可以尝试提升初始图像的分辨率并进一步调整您的提示词。*
