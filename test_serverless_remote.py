import os
import time
import requests
import base64

API_KEY = os.environ.get("RUNPOD_API_KEY", "")
# ⬇️ 已经为您自动填入您的专属 Endpoint ID！
ENDPOINT_ID = "t2o8t6ksie6npm"

# 发起异步长视频生成请求
url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/run"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
payload = {
    "input": {
        "positive_prompt": "(At 0 seconds: Medium close-up, a woman with realistic skin lying on a bed...) (At 2 seconds: rhythmic movement...)",
        "negative_prompt": "ugly, blurry, low resolution, bad hands",
        "style": "none",
        "frames": 21,
        "width": 480,
        "height": 832,
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png"
    }
}

print(f"🚀 发送视频生成请求到 RunPod Serverless API: {ENDPOINT_ID} ...")
resp = requests.post(url, headers=headers, json=payload)
data = resp.json()

job_id = data.get("id")
if not job_id:
    print("❌ 启动任务失败:", data)
    exit(1)

print(f"✅ 任务被云端接收成功！分配到的 Job ID: {job_id}")
print("⏳ 正在长轮询等待生成视频 (耐心等待 1-5 分钟)...")

# 5秒轮询查询任务状态
status_url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{job_id}"
while True:
    time.sleep(5)
    s_resp = requests.get(status_url, headers=headers)
    s_data = s_resp.json()
    status = s_data.get("status")

    print(f"[{time.strftime('%H:%M:%S')}] 云端计算节点当前状态: {status}")

    if status == "COMPLETED":
        output = s_data.get("output", {})
        if output.get("status") == "success":
            print(f"\n🎉 云端生成完毕！参数回传: {output.get('parameters_used', {})}")
            print(f"   视频数量: {output.get('video_count', 0)}, 帧图片数: {output.get('image_count', 0)}")

            # Check for URL-based output (fly.io OSS)
            video_url = output.get("video_url", "")
            if video_url:
                print(f"🔗 视频下载链接: {video_url}")
                # Download from URL
                import urllib.request
                urllib.request.urlretrieve(video_url, "final_serverless_output.mp4")
                print(f"💾 视频已下载保存: final_serverless_output.mp4")
            else:
                # Fallback to base64
                videos = output.get("video_base64_array", [])
                if videos:
                    b64_data = videos[0].split(",")[1] if "," in videos[0] else videos[0]
                    with open("final_serverless_output.mp4", "wb") as f:
                        f.write(base64.b64decode(b64_data))
                    print(f"💾 视频已保存: final_serverless_output.mp4")
                else:
                    print("⚠️ 成功但没有视频输出（查看 RunPod Logs 搜索 [OUTPUT] 获取调试信息）")
        else:
            print("\n❌ 内部错误:", output)
        break

    elif status in ["FAILED", "CANCELLED", "TIMED_OUT"]:
        print(f"\n❌ 任务失败: {s_data}")
        break
