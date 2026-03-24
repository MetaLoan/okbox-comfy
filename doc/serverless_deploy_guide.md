# ☁️ Wan 2.2 Serverless (无服务器) 部署与调用指南

为了把这个双擎版 Wan 2.2 工作流变成一个随叫随到、按需计费的云端 API（Serverless），你需要经历一次标准的“工业化打包”过程。
因为 Serverless 每次收到请求时都是处于“全新开机”状态，这就意味着我们不能把所有的 30GB 模型和代码乱放，必须把它们封存在一个标准的调用接口内。

---

## 💡 核心路线选择（影响你的成本与调用速度）

**方案 A：网络磁盘挂载法（Network Volume）—— 推荐新手**
- **原理**：用原版跑 ComfyUI 的 Serverless 官方基础镜像（空壳），去挂载一个存放着全部 30GB 大模型的云盘。
- **优点**：随时可以进盘里换模型，不用搞烦人的 Docker 封包打包。
- **缺点**：每次 Serverless 实例从冷启动唤醒时，要读盘进显存（加载 30GB），第一次启动可能要等好几分钟。

**方案 B：全量 Docker 巨包法（Bake Into Image）—— 推荐老手/商用**
- **原理**：自己在本机写一个 `Dockerfile`，把那 30GB 的 `H.safetensors` 和 `L.safetensors` 和所有的 Python 环境全盘压缩进去，推送到 Docker Hub 等镜像仓库，给 RunPod Serverless 读取。
- **优点**：启动极快，随用随起，完全工业级的吞吐量。
- **缺点**：你要推/拉一个 35GB 左右的巨无霸 Docker 镜像。

---

## 🛠️ 第一步：获取你的“程序级”接口 JSON！

咱们之前改好的那个 `dual_wan_i2v.json` 只是为了让人手能拖进网页里看的**画板格式**，并不适合作为后台代码投喂给 Serverless 接口。
你的首要任务是导出“纯代码API”版本：

1. 打开你正在运行的 ComfyUI 网页。
2. 点击右边面板最下方的 **`[小齿轮设置图标 Settings]`**。
3. 在弹出的设置列表中，勾选 **`Enable Dev mode Options (启用开发者模式选项)`**。
4. 关闭设置回到右侧主面板，你会发现多了一个叫 **`Save (API Format)`** 的新按钮。
5. 点击它，就可以另存为一份名为 `workflow_api.json` 的程序级文件！把它发给我，以后我们写 Python 代码就靠这个来动态修改里面的图和提示词。

---

## 🛠️ 第二步：准备 Serverless 的黄金处理代码 (Python)

如果你走原生的 RunPod Serverless 自建 Handler，需要写一个类似于如下架构的 `handler.py` 来承担：接受用户请求 -> 调起 ComfyUI API -> 返回视频链接。
（此部分代码如果需要全自动构建，请告诉我你选择的路线，我会随时自动帮你编写 `Dockerfile` 与这段启动代码）。

```python
import runpod
import json
import urllib.request
import urllib.parse
from PIL import Image
import base64

def handler(job):
    job_input = job['input'] # 这里会接收你的外界请求
    prompt_text = job_input.get('prompt', 'A default NSFW video prompt...')
    image_url = job_input.get('base_image_url')
    
    # 我们将会在下面这步，把你的 workflow_api.json 里的节点 ID 强制替换成上面收到的图和文本
    # 详见下文深度代码...
    
    return {"video_url": "xxxxx.mp4"}

runpod.serverless.start({"handler": handler})
```

---

## 🚀 接下来我需要怎么配合你？
由于你还在开着刚才的那台 `pvq3iw4mfsuwlx` 主机，而且那 30GB 的天价资源全部存在那个临时磁盘（`/root/ComfyUI/models`）里！如果你现在把它关了，这些刚下的模型全都没了！

**👉 告诉我你的选择：**
1. **“帮我把这些模型转移到一个永久网络盘（Network Volume），我要做基础挂载版的 Serverless！”**
2. **“我现在就要开始全量打包！给我写 Docker 步骤！”**
