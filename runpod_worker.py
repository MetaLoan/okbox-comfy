import os
import json
import time
import base64
import urllib.request
import subprocess
import urllib.error
import uuid
import random
import runpod
import websocket

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
        ["python", "-u", "main.py", "--listen", "0.0.0.0", "--port", "8188"],
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

    # Collect outputs
    history = fetch_history(prompt_id)
    outputs = history.get(prompt_id, {}).get('outputs', {})
    encoded_videos = []

    # Try multiple output node formats
    for node_id in ["47", "8"]:
        if node_id in outputs:
            node_out = outputs[node_id]
            # Check for video files (gifs key used by VHS and others)
            for key in ["gifs", "videos", "images"]:
                if key in node_out:
                    for file_info in node_out[key]:
                        fname = file_info.get("filename", "")
                        subfolder = file_info.get("subfolder", "")
                        filepath = os.path.join(OUTPUT_DIR, subfolder, fname)
                        if os.path.exists(filepath):
                            with open(filepath, "rb") as vf:
                                encoded_str = base64.b64encode(vf.read()).decode('utf-8')
                                ext = fname.rsplit('.', 1)[-1] if '.' in fname else 'webm'
                                encoded_videos.append(f"data:video/{ext};base64,{encoded_str}")
                            os.remove(filepath)

    # Cleanup input image
    input_path = os.path.join(INPUT_DIR, input_filename)
    if os.path.exists(input_path):
        os.remove(input_path)

    return {
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
        "video_count": len(encoded_videos),
        "video_base64_array": encoded_videos
    }

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
