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
import re
import copy
import requests
import runpod
import websocket
import boto3

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
BUNDLED_REGISTRY_PATH = "/workspace/lora_style_registry.json"  # Baked into Docker image
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

def qwen_faceswap_process(source_img, target_img, prompt, size_str="2048*2048"):
    print(f"[QWEN] Starting Qwen Faceswap API call with size {size_str}...", flush=True)
    url = "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    
    qwen_api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not qwen_api_key:
        print("[QWEN ERROR] DASHSCOPE_API_KEY environment variable is not set!", flush=True)
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {qwen_api_key}",
        "X-DashScope-DataInspection": '{"input":"disable", "output": "disable"}'
    }
    
    def format_img(img_val):
        if img_val.startswith("http"):
            return img_val
        elif img_val.startswith("data:"):
            return img_val
        else:
            return f"data:image/jpeg;base64,{img_val}"

    payload = {
        "model": "qwen-image-2.0-pro",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"image": format_img(source_img)},
                        {"image": format_img(target_img)},
                        {"text": prompt}
                    ]
                }
            ]
        },
        "parameters": {
            "n": 1,
            "negative_prompt": " ",
            "prompt_extend": True,
            "watermark": False,
            "size": size_str
        }
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res = json.loads(response.read().decode('utf-8'))
            if "output" in res and "choices" in res["output"]:
                img_url = res['output']['choices'][0]['message']['content'][0]['image']
                print(f"[QWEN SUCCESS] Got image: {img_url}", flush=True)
                return img_url
            else:
                print(f"[QWEN ERROR] Unexpected response format: {res}", flush=True)
                return None
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        print(f"[QWEN ERROR] HTTP {e.code}: {error_body}", flush=True)
        return None
    except Exception as e:
        print(f"[QWEN ERROR] {e}", flush=True)
        return None

def parse_multi_lora_style(style_str):
    """
    Parse multi-LoRA style string.
    
    Supported formats:
      - "none"                          → no LoRA
      - "anime_cumshot"                 → single LoRA, default strength 1.0/1.0 (backward compat)
      - "anime_cumshot(0.7,0.9)"        → single LoRA with custom high=0.7, low=0.9
      - "anime_cumshot(0.7,0.9),massage_tits(0.2,0.3)"  → multi-LoRA stacking
    
    Returns a list of dicts:
      [{"name": "anime_cumshot", "high_strength": 0.7, "low_strength": 0.9}, ...]
    
    Returns None for style="none" or empty.
    """
    style_str = style_str.strip()
    if not style_str or style_str.lower() == "none":
        return None

    loras = []
    # Regex pattern: stylename(high,low) or just stylename
    # We split on commas that are NOT inside parentheses
    # First, split by '),' to handle multi-lora
    parts = re.split(r'\)\s*,\s*', style_str)
    
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        
        # If not the last part, we stripped the closing ), add it back for uniform parsing
        # Actually, let's parse more carefully
        # pattern: name(high,low) or just name
        match = re.match(r'^([a-zA-Z0-9_]+)\s*\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)?$', part)
        if match:
            name = match.group(1).lower()
            high_s = float(match.group(2))
            low_s = float(match.group(3))
            loras.append({"name": name, "high_strength": high_s, "low_strength": low_s})
        else:
            # Could be just a name without parentheses (backward compat for single style)
            clean = part.strip().rstrip(')').lower()
            if re.match(r'^[a-zA-Z0-9_]+$', clean):
                loras.append({"name": clean, "high_strength": 1.0, "low_strength": 1.0})
            else:
                raise ValueError(f"Invalid LoRA style format: '{part}'. Expected format: stylename(high,low)")
    
    return loras if loras else None


def build_multi_lora_graph(graph, lora_list, registry):
    """
    Dynamically build multi-LoRA chain in the ComfyUI API workflow.
    
    Architecture:
      High Noise path: UNETLoader(37) → LoRA_A_H → LoRA_B_H → ... → ModelSamplingSD3(54)
      Low Noise path:  UNETLoader(100) → LoRA_A_L → LoRA_B_L → ... → ModelSamplingSD3(101)
    
    Each LoRA uses LoraLoaderModelOnly node with separate strength for high/low noise.
    """
    # Remove old single-LoRA nodes if present
    if "150" in graph:
        del graph["150"]
    if "151" in graph:
        del graph["151"]
    
    # Starting node ID for dynamic LoRA nodes (use 200+ range to avoid conflicts)
    next_node_id = 200
    
    # === HIGH NOISE PATH ===
    # Chain: 37 → lora_h_1 → lora_h_2 → ... → 54
    prev_high_ref = ["37", 0]  # Start from UNETLoader HIGH output
    
    for i, lora in enumerate(lora_list):
        style_name = lora["name"]
        if style_name not in registry:
            available = [k for k in registry.keys() if k != "none"]
            raise ValueError(f"Style '{style_name}' not found. Available styles: {available}")
        
        high_file = registry[style_name]["high"]
        if high_file == "none":
            continue  # Skip if this style has no high noise LoRA
        
        node_id = str(next_node_id)
        next_node_id += 1
        
        graph[node_id] = {
            "inputs": {
                "lora_name": high_file,
                "strength_model": lora["high_strength"],
                "model": prev_high_ref
            },
            "class_type": "LoraLoaderModelOnly"
        }
        prev_high_ref = [node_id, 0]
        print(f"[LORA] HIGH chain [{i+1}]: {style_name} (strength={lora['high_strength']}) → node {node_id}", flush=True)
    
    # Wire the last HIGH LoRA output → ModelSamplingSD3 node 54
    graph["54"]["inputs"]["model"] = prev_high_ref
    
    # === LOW NOISE PATH ===
    # Chain: 100 → lora_l_1 → lora_l_2 → ... → 101
    prev_low_ref = ["100", 0]  # Start from UNETLoader LOW output
    
    for i, lora in enumerate(lora_list):
        style_name = lora["name"]
        low_file = registry[style_name]["low"]
        if low_file == "none":
            continue  # Skip if this style has no low noise LoRA
        
        node_id = str(next_node_id)
        next_node_id += 1
        
        graph[node_id] = {
            "inputs": {
                "lora_name": low_file,
                "strength_model": lora["low_strength"],
                "model": prev_low_ref
            },
            "class_type": "LoraLoaderModelOnly"
        }
        prev_low_ref = [node_id, 0]
        print(f"[LORA] LOW chain  [{i+1}]: {style_name} (strength={lora['low_strength']}) → node {node_id}", flush=True)
    
    # Wire the last LOW LoRA output → ModelSamplingSD3 node 101
    graph["101"]["inputs"]["model"] = prev_low_ref
    
    # Log total strength summary
    total_high = sum(l["high_strength"] for l in lora_list)
    total_low = sum(l["low_strength"] for l in lora_list)
    print(f"[LORA] Total strength - HIGH: {total_high:.2f}, LOW: {total_low:.2f} "
          f"(recommended max ~1.5-2.0 each)", flush=True)
    
    return graph


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
    style = job_input.get('style', 'none')
    image_url = job_input.get('image_url', '')
    image_base64 = job_input.get('image_base64', '')
    seed = job_input.get('seed', random.randint(1, 2**53))

    enable_faceswap = job_input.get('enable_faceswap', False)
    faceswap_source_img = job_input.get('faceswap_source_img', '')
    faceswap_target_img = job_input.get('faceswap_target_img', '')
    
    default_fs_prompt = """Image 1 may contain one or two people (one male and/or one female).
Image 2 contains two people: one male and one female.
Perform gender-matched replacement as follows:
* If Image 1 contains a male, replace the male person in Image 2 with the exact face identity and full outfit (clothing, hairstyle, hair color, accessories, and overall appearance) from the male in Image 1.
* If Image 1 contains a female, replace the female person in Image 2 with the exact face identity and full outfit (clothing, hairstyle, hair color, accessories, and overall appearance) from the female in Image 1.
* If Image 1 contains only one person, replace only the matching-gender person in Image 2 and leave the other person in Image 2 completely unchanged.
Strictly preserve from Image 2:
* Exact body poses, hand positions, body orientation, and relative positioning of the people
* Exact facial expressions, mouth states, eye openness, gaze directions, head angles, and emotional intensity for each replaced person
* Composition, background, lighting, camera distance, and the entire scene
Do not change the poses, gestures, interactions between people, or any part of the environment unless the corresponding person is being replaced. Keep the correct number of people. The clothing, hairstyle, hair color, and complete appearance of each replaced person must exactly match the corresponding gender person from Image 1.
Output a realistic, seamless, high-quality result with natural skin texture, accurate skin tone and lighting consistency, precise edge blending around faces, hairlines, necks, and clothing boundaries. The final image must look like a natural photograph with no visible artifacts or inconsistencies."""
    
    faceswap_prompt = job_input.get('faceswap_prompt', default_fs_prompt)

    # Handle input image
    input_filename = None
    if enable_faceswap:
        if not faceswap_source_img or not faceswap_target_img:
            return {"error": "Faceswap enabled but 'faceswap_source_img' or 'faceswap_target_img' is missing."}
        
        # Pass width and height to Qwen API so its output strictly matches target dimensions
        qwen_result_url = qwen_faceswap_process(
            faceswap_source_img, 
            faceswap_target_img, 
            faceswap_prompt, 
            size_str=f"{width}*{height}"
        )
        
        if not qwen_result_url:
            return {"error": "Qwen Faceswap API failed to generate the image."}
        
        print(f"[FACESWAP] Downloading result from Qwen...", flush=True)
        input_filename = download_input_image(qwen_result_url, filename=f"qwen_base_{uuid.uuid4().hex[:8]}.png")
    else:
        if image_base64:
            input_filename = save_base64_image(image_base64)
        elif image_url:
            input_filename = download_input_image(image_url)

    if not input_filename:
        return {"error": "No input image provided. Please supply 'image_url', 'image_base64' or enable 'faceswap' in the payload."}

    # [DEBUG & METADATA FIX] Check input image metadata, force RGB, and adapt resolution
    import PIL.Image
    import traceback
    try:
        input_path = os.path.join(INPUT_DIR, input_filename)
        with PIL.Image.open(input_path) as img:
            orig_w, orig_h = img.size
            orig_mode = img.mode
            orig_format = img.format
            print(f"[DEBUG-IMAGE] Downloaded image metadata: size={orig_w}x{orig_h}, mode={orig_mode}, format={orig_format}", flush=True)

            # Strip EXIF and Alpha channels. Ensure purely clean RGB without tricky metadata.
            if img.mode != 'RGB':
                print(f"[DEBUG-IMAGE] Converting mode from {img.mode} to RGB to prevent VAE decode corruption.", flush=True)
                img = img.convert('RGB')
            
            # Save it back strictly as a pure standard PNG
            img.save(input_path, format="PNG")
            print(f"[DEBUG-IMAGE] Image sanitized and saved as pure RGB PNG.", flush=True)

            # Extract the actual dimensions (snapped to nearest multiple of 16)
            actual_w = (orig_w // 16) * 16
            actual_h = (orig_h // 16) * 16
            
            # OVERRIDE the generation width/height to mathematically match the downloaded image!
            if actual_w != width or actual_h != height:
                print(f"[DEBUG-IMAGE] Overriding requested dimensions ({width}x{height}) with image's exact dimensions ({actual_w}x{actual_h}) to prevent latent misalignment / 花屏.", flush=True)
                width = actual_w
                height = actual_h
                
            if actual_w != orig_w or actual_h != orig_h:
                print(f"[DEBUG-IMAGE] WARNING: Input image size {orig_w}x{orig_h} is NOT a multiple of 16! Expect minor edge rounding.", flush=True)
    except Exception as e:
        print(f"[ERROR-IMAGE] Failed to intercept/parse image metadata: {e}", flush=True)
        traceback.print_exc()

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
        
    # The original Ali image directly feeds into the Wan2.2 conditioning!
    # Removing any programmatic ComfyUI ImageScale injections.

    # Set seed
    graph["102"]["inputs"]["noise_seed"] = seed
    graph["103"]["inputs"]["noise_seed"] = seed + 1

    # ========== Handle LoRA style (v2.0 multi-LoRA support) ==========
    try:
        lora_list = parse_multi_lora_style(style)
    except ValueError as e:
        return {"error": str(e)}

    if lora_list is None:
        # No LoRA: bypass LoRA nodes, wire UNET directly to ModelSampling
        graph["54"]["inputs"]["model"] = ["37", 0]
        graph["101"]["inputs"]["model"] = ["100", 0]
        if "150" in graph: del graph["150"]
        if "151" in graph: del graph["151"]
        print(f"[LORA] No LoRA applied (style='none')", flush=True)
    else:
        # Load registry
        try:
            if not os.path.exists(REGISTRY_PATH):
                print(f"Registry not found, auto-building default at {REGISTRY_PATH}", flush=True)
                os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
                default_registry = {
                    "none": {"high": "none", "low": "none"},
                    "anime_cumshot": {
                        "high": "23High_noise-Cumshot_Aesthetics.safetensors",
                        "low": "56Low_noise-Cumshot_Aesthetics.safetensors"
                    },
                    "massage_tits": {
                        "high": "mql_massage_tits_wan22_i2v_v1_high_noise.safetensors",
                        "low": "mql_massage_tits_wan22_i2v_v1_low_noise.safetensors"
                    }
                }
                with open(REGISTRY_PATH, 'w', encoding='utf-8') as rf:
                    json.dump(default_registry, rf, indent=2)

            with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                registry = json.load(f)

            graph = build_multi_lora_graph(graph, lora_list, registry)
            
            print(f"[LORA] Multi-LoRA chain built: {[l['name'] for l in lora_list]} "
                  f"({len(lora_list)} LoRAs stacked)", flush=True)

        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Registry/LoRA error: {str(e)}"}

    # Build style summary for response
    style_summary = style
    if lora_list:
        style_summary = ",".join(
            f"{l['name']}({l['high_strength']},{l['low_strength']})" for l in lora_list
        )

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

        # Upload to Cloudflare R2 (S3-compatible)
        r2_account_id = os.environ.get("R2_ACCOUNT_ID", "da42bda8b7dfcd7dfdffa0ae318cc810")
        r2_access_key = os.environ.get("R2_ACCESS_KEY_ID", "7cfe4bc0684285ebcd5a7b33925a5971")
        r2_secret_key = os.environ.get("R2_ACCESS_KEY_SECRET", "92a205e7a58c1a4f327c4d490330a95577396ab287dfe564b7c743861a98ca48")
        r2_bucket = os.environ.get("R2_BUCKET", "candyhub-s")
        r2_public_url = os.environ.get("R2_PUBLIC_URL", "https://vcdn.sprize.ai")

        video_exists = os.path.exists(output_video)
        print(f"[R2] Pre-upload check: video={output_video}, exists={video_exists}, r2_key_set={bool(r2_access_key)}", flush=True)

        if r2_access_key and video_exists:
            try:
                print(f"[R2] Connecting to https://{r2_account_id}.r2.cloudflarestorage.com ...", flush=True)
                s3 = boto3.client(
                    's3',
                    endpoint_url=f"https://{r2_account_id}.r2.cloudflarestorage.com",
                    aws_access_key_id=r2_access_key,
                    aws_secret_access_key=r2_secret_key,
                    region_name='auto'
                )
                r2_key = f"videos/{prompt_id}.mp4"
                print(f"[R2] Uploading {os.path.getsize(output_video)} bytes to {r2_bucket}/{r2_key} ...", flush=True)
                s3.upload_file(
                    output_video, r2_bucket, r2_key,
                    ExtraArgs={'ContentType': 'video/mp4'}
                )
                video_url = f"{r2_public_url}/{r2_key}"
                print(f"[R2] Upload SUCCESS: {video_url}", flush=True)
            except Exception as e:
                print(f"[R2] Upload FAILED: {type(e).__name__}: {e}", flush=True)
        else:
            print(f"[R2] SKIPPED: r2_access_key={bool(r2_access_key)}, video_exists={video_exists}", flush=True)

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
            "style": style_summary,
            "seed": seed
        },
        "video_count": 1 if video_url else len(encoded_videos),
        "image_count": len(image_files),
    }

    # Include LoRA details in response
    if lora_list:
        result["lora_stack"] = [
            {"name": l["name"], "high_strength": l["high_strength"], "low_strength": l["low_strength"]}
            for l in lora_list
        ]

    if video_url:
        result["video_url"] = video_url
    if encoded_videos:
        result["video_base64_array"] = encoded_videos

    return result

if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("RunPod Serverless ComfyUI Worker v2.0-multilora", flush=True)
    print("=" * 60, flush=True)

    # GPU driver diagnostic
    try:
        smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=10)
        print(smi.stdout, flush=True)
        if smi.returncode != 0:
            print(f"[DIAG] nvidia-smi failed: {smi.stderr}", flush=True)
    except Exception as e:
        print(f"[DIAG] nvidia-smi error: {e}", flush=True)

    # Auto-sync: copy bundled registry to Network Volume
    if os.path.exists(BUNDLED_REGISTRY_PATH):
        try:
            os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
            import shutil
            shutil.copy2(BUNDLED_REGISTRY_PATH, REGISTRY_PATH)
            with open(REGISTRY_PATH, 'r') as f:
                reg = json.load(f)
            styles = [k for k in reg.keys() if k != 'none']
            print(f"[SYNC] Registry synced to Volume: {len(styles)} styles → {styles}", flush=True)
        except Exception as e:
            print(f"[SYNC] Registry sync failed: {e}", flush=True)

    ok = start_comfyui()
    if ok:
        print("Handing over to RunPod Serverless SDK...", flush=True)
        runpod.serverless.start({"handler": process_job})
    else:
        print("FATAL: Cannot start - ComfyUI failed to initialize.", flush=True)
