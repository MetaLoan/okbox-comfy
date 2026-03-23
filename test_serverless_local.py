import runpod_worker
import sys
import os

print("🚀 模拟启动 RunPod Serverless 调用...")

# 检查测试环境是否为本地调试环境，重定位路径
if not os.path.exists(runpod_worker.API_JSON_PATH):
    print("本地调试模式：重定向路径")
    runpod_worker.API_JSON_PATH = "dual_wan_i2v_api.json"
    runpod_worker.REGISTRY_PATH = "/runpod-volume/my_stable_models/loras/lora_style_registry.json" # local dev map
    runpod_worker.OUTPUT_DIR = "/workspace/runpod-slim/ComfyUI/output"

job = {
    "input": {
        "positive_prompt": "(At 0 seconds: Close up of a beautiful anime styled cumshot, masterpiece, highly detailed face...)",
        "negative_prompt": "ugly, blurry, low resolution, bad hands",
        "style": "anime_cumshot", 
        "frames": 16, # 短视频仅作快速连通性测试
        "width": 480,
        "height": 832
    }
}

print(f"发送负载 (Payload): {job['input']}\n")

result = runpod_worker.process_job(job)

if result.get("status") == "success":
    print("\n✅ API 返回成功！")
    print(f"生成的 Base64 视频长度: {len(result['video_base64_array'][0])} 字节")
    print("保存预览... (test_output.webm)")
    
    # 抽取 base64 中的真实数据并存成真实播放文件
    import base64
    b64_data = result['video_base64_array'][0].split(",")[1]
    with open("test_output.webm", "wb") as f:
        f.write(base64.b64decode(b64_data))
    print("✅ 测试视频已保存至当前目录！Serverless 容器封包可用！")
else:
    print("\n❌ 发生错误:")
    print(result)
    sys.exit(1)
