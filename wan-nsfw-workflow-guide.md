# WAN 2.2 角色图生视频 (I2V) 终极部署指南

> **目标需求**：传一张角色图片 + 分场景秒级提示词 -> 自动生成 6-12s 的 480P 真人写实 NSFW 视频

---

## 🏗️ 核心底层逻辑与镜像选择

最致命的踩坑：**不要尝试使用任何打包好 ComfyUI 的第三方神仙 Docker 镜像。**
RunPod 底层代理在连接 SSH 和 Web Terminal 时，会依赖标准系统的 bash 和 sshd。第三方过度精简会导致 TCP 秒断和“Permission denied”。

👉 这套方案已经验证：**只用官方原版 `RunPod Pytorch 2.1` 模板**，所有软件进去自己装！这是零崩溃、零闪退的不二法门。

### 0️⃣ 前期：SSH 公钥下发
必须先在通过 `ssh-keygen -t ed25519` 在你的 Mac 上生成好公钥。
带着 `~/.ssh/id_ed25519.pub` 的内容，登录 RunPod 控制台前往 `Settings -> SSH Keys` 保存，**然后再创建容器**，让新容器在初始化那一瞬间注入密钥。

---

## 🚀 1. 终极一键原生部署 (在你的 Mac 终端运行)

当容器启动后，去取得它的 Proxy SSH 串号（比如 `pvq3iw4mfsuwlx-64411458@ssh.runpod.io`）。
打开你的电脑自带黑框框（Terminal），执行下面这个带 `-tt` PTY 伪装的大脚本命令（它包含了原生搭建从头到尾的每一步！）：

```bash
ssh -tt -o StrictHostKeyChecking=no pvq3iw4mfsuwlx-xxxxxxxx@ssh.runpod.io -i ~/.ssh/id_ed25519
```

连进去显示 `root@xxxx:/#` 后，一鼓作气把下面这块“航母级”指令复制粘贴进去，按回车：

```bash
# 抓取原生控制面板和驱动
git clone https://github.com/comfyanonymous/ComfyUI.git /workspace/ComfyUI && cd /workspace/ComfyUI && \
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121 && \
pip install -r requirements.txt && \

# 安装针对性插件
cd custom_nodes && \
git clone https://github.com/kijai/ComfyUI-KJNodes.git && \
git clone https://github.com/rgthree/rgthree-comfy.git && \
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
git clone https://github.com/ashtar1984/comfyui-find-perfect-resolution.git && \
apt-get update && apt-get install -y ffmpeg libgl1-mesa-glx && \
pip install -r ComfyUI-KJNodes/requirements.txt && \
pip install imageio[ffmpeg] opencv-python accelerate && cd .. && \

# 开始验证授权，全速拉取 NSFW 各路主副件
mkdir -p models/diffusion_models && \
wget -q --show-progress --header="Authorization: Bearer 75fd40dee9af3b6dc8d40c5b6532338c" -O workflow_V2.1_NSFW.json "https://civitai.com/api/download/models/2562360" && \
wget -q --show-progress --header="Authorization: Bearer 75fd40dee9af3b6dc8d40c5b6532338c" -O models/diffusion_models/WAN2.2-NSFW-FastMove-V2-H.gguf "https://civitai.com/api/download/models/2477539" && \
wget -q --show-progress --header="Authorization: Bearer 75fd40dee9af3b6dc8d40c5b6532338c" -O models/diffusion_models/WAN2.2-NSFW-FastMove-V2-L.gguf "https://civitai.com/api/download/models/2477618" && \
echo "✅ 恭喜！下载组装全部完成！"
```

等控制台打印完勾号，敲入启动命令：`python main.py --listen` ，就彻底好了！没有任何系统环境能比这套自己搭出来更纯净！

---

## 🎬 2. 核心工作流跑法与配置（干货）

在浏览器打开你的机器（例 `https://pvq3iw4mfsuwlx-8188.proxy.runpod.net`）。点击 `Load` 把机器里的 `/workspace/ComfyUI/workflow_V2.1_NSFW.json` 导进来。

### 模型参数生死线：
- **Checkpoint（High）**: `WAN2.2-NSFW-FastMove-V2-H.gguf`
- **Checkpoint（Low）**: `WAN2.2-NSFW-FastMove-V2-L.gguf`
- **CFG Scale（强提醒）**: 必须设为 **1.0**！稍微偏高画面直接扭曲炸裂。
- **Steps**: High 设为 `2`，Low 设为 `2` 或 `3`。
- **Lightning LoRA**：千万**不要**私自叠放 Lighting LoRA（像 Combo1、Combo2 什么的），因为主模型已经**内建（烘焙）**了提速模组！叠加会变得非常模糊。

### 怎么写 Prompt，怎样动作不出框？
利用非常强的秒级时空分隔控制写法。在针对性渲染 H 场景时非常平滑：

```text
(At 0 seconds: Medium close-up, cozy bedroom, soft lighting. Anime style skin with realistic body lighting.)
(At 1 second: He slowly positions himself, dynamic perspective.)
(At 2 seconds: The skin reacting rhythmically to the thrusting motion, tiny hearts floating above to emphasize pleasure.)
(At 4 seconds: Smooth penetration, she arches her back tightly.)
```

### 反重影与防畸变处理
如果在 CFG=1 情况下发生了“身体乱扭”、“臀部夸张乱抖”、“人长三条腿”，需要动用专门安装的 `kjnode` 中的神器：**WAN Nag**：
1. 把它接到 LoRA 加载器后面。
2. 填入官方除重专用负面词组：
   > `motion artifacts, animation artifacts, movement blur, motion distortion, shifting shapes, wobbling effect, exaggerated butt movement, jiggle, unnatural butt motion...`
3. 输出给第一个 `KSampler (High)`，生成时长会略长一点，但残影立消。
