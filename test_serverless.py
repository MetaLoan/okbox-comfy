import base64
import time
import json
import os
import sys
import urllib.request
import urllib.error

# 读取绝密钥匙
env_vars = {}
try:
    with open("key.env", "r") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env_vars[k.strip()] = v.strip()
except Exception:
    pass

ENDPOINT_ID = env_vars.get("SERVERLESSENDPOINT", "").split("/")[-1]
RUNPOD_API_KEY = env_vars.get("RUNPODAPIKEY", "")

if not ENDPOINT_ID or not RUNPOD_API_KEY:
    print("❌ key.env 填写有误，读取不到 RUNPODAPIKEY 和 SERVERLESSENDPOINT！")
    sys.exit(1)

API_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/run"

def get_baseimg(image_url):
    print("⬇️ 正在拉取网络图片转换为光波电码...")
    req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    return base64.b64encode(response.read()).decode("utf-8")

def submit_job(prompt, base_image_b64):
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"input": {"prompt": prompt, "base_image": base_image_b64}}
    data = json.dumps(payload).encode('utf-8')
    
    print("🚀 [1/3] 发送作业给 Serverless 航母舰队...")
    req = urllib.request.Request(API_URL, data=data, headers=headers)
    try:
        resp = urllib.request.urlopen(req)
        resp_data = json.loads(resp.read().decode('utf-8'))
        job_id = resp_data.get("id")
        print(f"✅ 任务立案成功! 拿到了凭证号: {job_id}")
        return job_id
    except urllib.error.URLError as e:
        print("❌ 任务发射失败:", e.read().decode('utf-8') if hasattr(e, 'read') else str(e))
        sys.exit(1)

def poll_job(job_id):
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    status_url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{job_id}"
    
    print("⏳ [2/3] 挂载网盘、唤醒显卡需要约 1~3 分钟的无声前摇...")
    print("⏳ ...进入轮询模式...")
    
    while True:
        req = urllib.request.Request(status_url, headers=headers)
        try:
            resp = urllib.request.urlopen(req)
            data = json.loads(resp.read().decode('utf-8'))
            status = data.get("status")
            
            if status == "COMPLETED":
                print("\n🎉 [3/3] 渲染完成！开始下载这绝世佳作...")
                return data["output"]
            elif status == "FAILED":
                print("\n💥 模型报错闪退！原因可能是节点版本错配或者图片尺寸拉伸过度:", data.get("error"))
                break
            elif status == "IN_QUEUE":
                print("🛏️ 服务器还在深度唤醒/排队队列中，稳住气等待点火...")
            elif status == "IN_PROGRESS":
                print("🔥 48G 显卡正在咆哮运转，双引擎进行 4 步极速降噪渲染... 请稍作几十秒等待...")
                
        except urllib.error.URLError as e:
            print("⚠️ 网络拉取进度小卡巴了一下，没事继续等...")
        
        time.sleep(10)

if __name__ == "__main__":
    # 你指定的网图作为首帧
    my_test_img_url = "https://files.catbox.moe/vrsvn0.jpg"
    
    # 核心动效镜头语言，不加也会自己根据图脑补
    my_prompt = "(A girl elegantly moving her body in dim cyberpunk light, ultra detailed realistic photography)"
    
    try:
        b64 = get_baseimg(my_test_img_url)
    except Exception as e:
        print("⚠️ 网络图片拉挂了！报错:", e)
        b64 = None

    job_id = submit_job(my_prompt, b64)
    result = poll_job(job_id)
    
    if result and "video_base64" in result:
        video_bytes = base64.b64decode(result["video_base64"])
        with open("final_nsfw_movie.webm", "wb") as f:
            f.write(video_bytes)
        print("🎬 太神了！视频已经被完美存盘成 final_nsfw_movie.webm 啦！可以关掉你的黑框界面去看了！")
