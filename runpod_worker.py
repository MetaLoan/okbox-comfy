import os
# CRITICAL: Disable cuDNN before any torch import - RTX 5090 Blackwell compatibility
os.environ['TORCH_CUDNN_V8_API_DISABLED'] = '1'

import json
import time
import base64
import urllib.request
import subprocess
import urllib.error
import uuid
import random
import requests
import runpod
import websocket

# Disable cuDNN at runtime level for Blackwell GPU compatibility
try:
    import torch
    torch.backends.cudnn.enabled = False
    print(f"[INIT] cuDNN disabled for Blackwell GPU compatibility", flush=True)
    print(f"[INIT] PyTorch {torch.__version__}, CUDA {torch.version.cuda}", flush=True)
except Exception as e:
    print(f"[INIT] torch import note: {e}", flush=True)

COMFY_URL = "127.0.0.1:8188"
API_JSON_PATH = "/workspace/dual_wan_i2v_api.json"
REGISTRY_PATH = "/runpod-volume/my_stable_models/lora_style_registry.json"
COMFY_DIR = "/workspace/ComfyUI"
OUTPUT_DIR = f"{COMFY_DIR}/output"
INPUT_DIR = f"{COMFY_DIR}/input"

def start_comfyui():
    print("Starting ComfyUI server in the background...", flush=True)

    # Diagnostic: check models directory
    models_path = f"{COMFY_DIR}/models"
    if os.path.islink(models_path):
        target = os.readlink(models_path)
        print(f"[DIAG] models -> {target} (exists: {os.path.exists(target)})", flush=True)
    elif os.path.isdir(models_path):
        print(f"[DIAG] models is a real directory", flush=True)
    else:
        print(f"[DIAG] WARNING: models not found at {models_path}!", flush=True)

    # Diagnostic: check /runpod-volume
    if os.path.exists("/runpod-volume"):
        contents = os.listdir("/runpod-volume")
        print(f"[DIAG] /runpod-volume contents: {contents}", flush=True)
    else:
        print("[DIAG] WARNING: /runpod-volume does NOT exist!", flush=True)

    process = subprocess.Popen(
        ["python", "-u", "main.py", "--listen", "0.0.0.0", "--port", "8188",
         "--disable-cuda-malloc",
         "--extra-model-paths-config", f"{COMFY_DIR}/extra_model_paths.yaml"],
        cwd=COMFY_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    import threading
    def stream_logs():
        for line in process.stdout:
            print(f"[ComfyUI] {line.strip()}", flush=True)
    threading.Thread(target=stream_logs, daemon=True).start()

    # Wait for API with timeout
    max_wait = 300  # 5 minutes max
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            print(f"FATAL: ComfyUI did not start within {max_wait}s!", flush=True)
            break
        if process.poll() is not None:
            print(f"FATAL: ComfyUI process died with code {process.returncode}!", flush=True)
            break
        try:
            req = urllib.request.Request(f"http://{COMFY_URL}/system_stats")
            urllib.request.urlopen(req, timeout=2)
            print(f"ComfyUI API is responsive and ready! (took {elapsed:.0f}s)", flush=True)
            return True
        except urllib.error.URLError:
            time.sleep(1)
            if int(elapsed) % 10 == 0:
                print(f"Waiting for ComfyUI to start... ({elapsed:.0f}s)", flush=True)
    return False

def queue_prompt(workflow):
    client_id = str(uuid.uuid4())
    payload = {"prompt": workflow, "client_id": client_id}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f"http://{COMFY_URL}/prompt",
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read())
            print(f"Prompt queued successfully: {res}", flush=True)
            return res.get('prompt_id'), client_id
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        print(f"HTTP Error {e.code} queueing prompt: {error_body}", flush=True)
        return None, error_body
    except urllib.error.URLError as e:
        print(f"URL Error queueing prompt: {e}", flush=True)
        return None, str(e)

def wait_for_execution(client_id, prompt_id, timeout=600):
    ws = websocket.WebSocket()
    ws.settimeout(timeout)
    ws.connect(f"ws://{COMFY_URL}/ws?clientId={client_id}")
    try:
        while True:
            out = ws.recv()
            if isinstance(out, str):
                msg = json.loads(out)
                msg_type = msg.get('type')
                if msg_type == 'executing':
                    data = msg.get('data', {})
                    node = data.get('node')
                    if node:
                        print(f"[Progress] Executing node: {node}", flush=True)
                    if node is None and data.get('prompt_id') == prompt_id:
                        print("Execution finished!", flush=True)
                        break
                elif msg_type == 'execution_error':
                    print(f"[ERROR] Execution error: {msg.get('data', {})}", flush=True)
                    break
    except websocket.WebSocketTimeoutException:
        print(f"WebSocket timeout after {timeout}s", flush=True)
    finally:
        ws.close()

def fetch_history(prompt_id):
    req = urllib.request.Request(f"http://{COMFY_URL}/history/{prompt_id}")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())

def download_input_image(image_url, filename="serverless_input.png"):
    """Download an image from URL and save it to ComfyUI's input directory."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    filepath = os.path.join(INPUT_DIR, filename)
    print(f"Downloading input image from {image_url}...", flush=True)
    try:
        req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(filepath, 'wb') as f:
                f.write(resp.read())
        size = os.path.getsize(filepath)
        print(f"Input image saved: {filepath} ({size} bytes)", flush=True)
        return filename
    except Exception as e:
        print(f"Failed to download input image: {e}", flush=True)
        return None

def save_base64_image(b64_string, filename="serverless_input.png"):
    """Save a base64 encoded image to ComfyUI's input directory."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    filepath = os.path.join(INPUT_DIR, filename)
    # Strip data URI prefix if present
    if ',' in b64_string:
        b64_string = b64_string.split(',', 1)[1]
    with open(filepath, 'wb') as f:
        f.write(base64.b64decode(b64_string))
    size = os.path.getsize(filepath)
    print(f"Base64 image saved: {filepath} ({size} bytes)", flush=True)
    return filename

def process_job(job):
    job_input = job.get('input', {})
    print(f"Received Serverless payload: {json.dumps(job_input, ensure_ascii=False)[:500]}", flush=True)

    # Inline volume diagnostic - runs with every job
    vol = "/runpod-volume"
    if os.path.exists(vol):
        print(f"[VOL-DIAG] /runpod-volume exists! Top-level: {os.listdir(vol)}", flush=True)
        msm = os.path.join(vol, "my_stable_models")
        if os.path.exists(msm):
            for subdir in sorted(os.listdir(msm)):
                full = os.path.join(msm, subdir)
                if os.path.isdir(full):
                    files = os.listdir(full)
                    print(f"[VOL-DIAG]   {subdir}/: {files}", flush=True)
        else:
            print(f"[VOL-DIAG] WARNING: my_stable_models NOT found! Contents: {os.listdir(vol)}", flush=True)
    else:
        print("[VOL-DIAG] CRITICAL: /runpod-volume does NOT exist!", flush=True)

    # Extract parameters
    pos_prompt = job_input.get('positive_prompt', "High quality anime style, masterpiece")
    neg_prompt = job_input.get('negative_prompt', "ugly, deformation")
    frames = job_input.get('frames', 81)
    width = job_input.get('width', 480)
    height = job_input.get('height', 832)
    style = job_input.get('style', 'none').lower()
    image_url = job_input.get('image_url', '')
    image_base64 = job_input.get('image_base64', '')
    seed = job_input.get('seed', random.randint(1, 2**53))

    # Handle input image
    input_filename = None
    if image_base64:
        input_filename = save_base64_image(image_base64)
    elif image_url:
        input_filename = download_input_image(image_url)

    if not input_filename:
        return {"error": "No input image provided. Please supply 'image_url' or 'image_base64' in the payload."}

    # Load workflow template
    with open(API_JSON_PATH, 'r', encoding='utf-8') as f:
        graph = json.load(f)

    # Inject dynamic parameters
    graph["6"]["inputs"]["text"] = pos_prompt
    graph["7"]["inputs"]["text"] = neg_prompt
    graph["50"]["inputs"]["length"] = frames
    graph["50"]["inputs"]["width"] = width
    graph["50"]["inputs"]["height"] = height

    # Set input image
    graph["52"]["inputs"]["image"] = input_filename
    if "upload" in graph["52"]["inputs"]:
        del graph["52"]["inputs"]["upload"]

    # Set seed
    graph["102"]["inputs"]["noise_seed"] = seed
    graph["103"]["inputs"]["noise_seed"] = seed + 1

    # Handle LoRA style
    if style == "none" or style == "":
        graph["54"]["inputs"]["model"] = ["37", 0]
        graph["101"]["inputs"]["model"] = ["100", 0]
        if "150" in graph: del graph["150"]
        if "151" in graph: del graph["151"]
    else:
        try:
            if not os.path.exists(REGISTRY_PATH):
                print(f"Registry not found, auto-building default at {REGISTRY_PATH}", flush=True)
                os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
                default_registry = {
                    "anime_cumshot": {
                        "high": "23High_noise-Cumshot_Aesthetics.safetensors",
                        "low": "56Low_noise-Cumshot_Aesthetics.safetensors"
                    }
                }
                with open(REGISTRY_PATH, 'w', encoding='utf-8') as rf:
                    json.dump(default_registry, rf, indent=2)

            with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                registry = json.load(f)

            if style in registry:
                graph["150"]["inputs"]["lora_name"] = registry[style]['high']
                graph["151"]["inputs"]["lora_name"] = registry[style]['low']
            else:
                available = list(registry.keys())
                return {"error": f"Style '{style}' not found. Available styles: {available}"}
        except Exception as e:
            return {"error": f"Registry error: {str(e)}"}

    # Submit to ComfyUI
    prompt_id, client_id = queue_prompt(graph)
    if not prompt_id:
        return {"error": f"ComfyUI rejected the workflow: {client_id}"}

    print(f"Queued ID: {prompt_id}. Awaiting completion...", flush=True)
    wait_for_execution(client_id, prompt_id)

    # Collect outputs - SaveImage produces PNG frames
    history = fetch_history(prompt_id)
    print(f"[OUTPUT] Full history keys: {list(history.keys())}", flush=True)

    prompt_output = history.get(prompt_id, {})
    outputs = prompt_output.get('outputs', {})
    print(f"[OUTPUT] Output node IDs: {list(outputs.keys())}", flush=True)
    for nid, nout in outputs.items():
        print(f"[OUTPUT] Node {nid}: keys={list(nout.keys())}, summary={str(nout)[:300]}", flush=True)

    # Collect all output images from any node
    image_files = []
    for node_id in outputs:
        node_out = outputs[node_id]
        if "images" in node_out:
            for img_info in node_out["images"]:
                fname = img_info.get("filename", "")
                subfolder = img_info.get("subfolder", "")
                filepath = os.path.join(OUTPUT_DIR, subfolder, fname)
                print(f"[OUTPUT] Found image: {filepath}, exists={os.path.exists(filepath)}", flush=True)
                if os.path.exists(filepath):
                    image_files.append(filepath)

    # Fallback: scan output directory directly
    if not image_files:
        print(f"[OUTPUT] No images from history, scanning {OUTPUT_DIR} directly...", flush=True)
        if os.path.exists(OUTPUT_DIR):
            all_files = sorted(os.listdir(OUTPUT_DIR))
            print(f"[OUTPUT] Files in output dir: {all_files}", flush=True)
            for f in all_files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    image_files.append(os.path.join(OUTPUT_DIR, f))

    print(f"[OUTPUT] Total image files collected: {len(image_files)}", flush=True)

    video_url = None
    if image_files:
        image_files.sort()
        output_video = os.path.join(OUTPUT_DIR, f"serverless_{prompt_id}.mp4")

        if len(image_files) == 1:
            # Single image - still convert to short video
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", image_files[0],
                "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", output_video
            ]
        else:
            # Multiple frames - combine into video
            list_file = os.path.join(OUTPUT_DIR, "frames.txt")
            with open(list_file, 'w') as lf:
                for img_path in image_files:
                    lf.write(f"file '{img_path}'\n")
                    lf.write(f"duration {1.0/16}\n")  # 16fps for wan2.2
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_file,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", output_video
            ]

        print(f"[OUTPUT] Running ffmpeg: {' '.join(ffmpeg_cmd)}", flush=True)
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[OUTPUT] ffmpeg error: {result.stderr}", flush=True)
        else:
            print(f"[OUTPUT] ffmpeg success! Video size: {os.path.getsize(output_video)} bytes", flush=True)

        # Upload to external storage if configured
        upload_url = os.environ.get("VIDEO_UPLOAD_URL", "")
        upload_token = os.environ.get("VIDEO_UPLOAD_TOKEN", "")
        if upload_url and os.path.exists(output_video):
            try:
                with open(output_video, "rb") as vf:
                    video_filename = f"{prompt_id}.mp4"
                    headers = {}
                    if upload_token:
                        headers["Authorization"] = f"Bearer {upload_token}"
                    upload_resp = requests.post(
                        upload_url,
                        files={"file": (video_filename, vf, "video/mp4")},
                        headers=headers,
                        timeout=120
                    )
                    if upload_resp.status_code == 200:
                        resp_data = upload_resp.json()
                        video_url = resp_data.get("url", "")
                        print(f"[OUTPUT] Uploaded to: {video_url}", flush=True)
                    else:
                        print(f"[OUTPUT] Upload failed: {upload_resp.status_code} {upload_resp.text}", flush=True)
            except Exception as e:
                print(f"[OUTPUT] Upload error: {e}", flush=True)

        # Fallback: base64 encode if no upload URL
        encoded_videos = []
        if not video_url and os.path.exists(output_video):
            with open(output_video, "rb") as vf:
                encoded_str = base64.b64encode(vf.read()).decode('utf-8')
                encoded_videos.append(f"data:video/mp4;base64,{encoded_str}")

        # Cleanup
        if os.path.exists(output_video):
            os.remove(output_video)
        for img_path in image_files:
            if os.path.exists(img_path):
                os.remove(img_path)
        list_file_path = os.path.join(OUTPUT_DIR, "frames.txt")
        if os.path.exists(list_file_path):
            os.remove(list_file_path)
    else:
        encoded_videos = []

    # Cleanup input image
    input_path = os.path.join(INPUT_DIR, input_filename)
    if os.path.exists(input_path):
        os.remove(input_path)

    result = {
        "status": "success",
        "parameters_used": {
            "positive_prompt": pos_prompt,
            "negative_prompt": neg_prompt,
            "frames": frames,
            "width": width,
            "height": height,
            "style": style,
            "seed": seed
        },
        "video_count": 1 if video_url else len(encoded_videos),
        "image_count": len(image_files),
    }

    if video_url:
        result["video_url"] = video_url
    if encoded_videos:
        result["video_base64_array"] = encoded_videos

    return result

if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("RunPod Serverless ComfyUI Worker v3", flush=True)
    print("=" * 60, flush=True)

    ok = start_comfyui()
    if ok:
        print("Handing over to RunPod Serverless SDK...", flush=True)
        runpod.serverless.start({"handler": process_job})
    else:
        print("FATAL: Cannot start - ComfyUI failed to initialize.", flush=True)
