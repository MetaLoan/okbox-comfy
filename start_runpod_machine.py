import os
import sys

# Try to import runpod, exit if not found
try:
    import runpod
except ImportError:
    print("runpod module is missing. Please run: pip install runpod")
    sys.exit(1)

api_key = None
try:
    with open("/Users/leo/runpod/key.env", "r") as f:
        for line in f:
            if line.startswith("runpodapikey="):
                api_key = line.split("=")[1].strip()
except Exception as e:
    print("Failed to read API key from key.env:", e)
    sys.exit(1)

if not api_key:
    print("RUNPOD API KEY not found in key.env")
    sys.exit(1)

runpod.api_key = api_key

try:
    print("🚀 Requesting to spawn a new ComfyUI rig (RTX 4090) on RunPod...")
    # Reference for GPU IDs: 'NVIDIA GeForce RTX 4090' or 'NVIDIA RTX 4090'
    new_pod = runpod.create_pod(
        name="Wan2.2-ComfyUI-Deployment",
        image_name="runpod/comfyui:latest",
        gpu_type_id="NVIDIA GeForce RTX 4090",
        cloud_type="SECURE",
        gpu_count=1,
        volume_in_gb=100,             # Based on 30GB models + padding
        container_disk_in_gb=50,
        ports="8188/http,22/tcp",
        env={"TZ": "Asia/Shanghai"}
    )
    print("✅ Pod successfully deployed!")
    print("Pod ID:", new_pod.get("id"))
    print("It might take a few minutes to pull the image and start.")
except runpod.error.QueryError as e:
    print("Query error. Retrying with 'NVIDIA GeForce RTX 4090'...")
    try:
        new_pod = runpod.create_pod(
            name="Wan2.2-ComfyUI-Deployment",
            image_name="runpod/comfyui:latest",
            gpu_type_id="NVIDIA GeForce RTX 4090",
            cloud_type="SECURE",
            gpu_count=1,
            volume_in_gb=100,
            container_disk_in_gb=50,
            ports="8188/http,22/tcp"
        )
        print("✅ Pod successfully deployed!")
        print("Pod ID:", new_pod.get("id"))
    except Exception as e2:
         print("❌ Failed to create pod:", e2)
except Exception as e:
    print("❌ Failed to create pod:", e)
