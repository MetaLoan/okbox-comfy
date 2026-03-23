import os
import json
import time
import base64
import urllib.request
import subprocess
import urllib.error
import uuid
import runpod
import websocket

COMFY_URL = "127.0.0.1:8188"
API_JSON_PATH = "/workspace/dual_wan_i2v_api.json"
REGISTRY_PATH = "/runpod-volume/my_stable_models/lora_style_registry.json"
OUTPUT_DIR = "/workspace/ComfyUI/output"

def start_comfyui():
    print("Starting ComfyUI server in the background...", flush=True)
    process = subprocess.Popen(
        ["python", "-u", "main.py", "--dont-print-signature", "--port", "8188"],
        cwd="/workspace/ComfyUI",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    import threading
    def stream_logs():
        for line in process.stdout:
            print(f"[ComfyUI] {line.strip()}", flush=True)
    threading.Thread(target=stream_logs, daemon=True).start()
    
    # Wait for the API to be ready
    while True:
        if process.poll() is not None:
            print(f"FATAL: ComfyUI process died unexpectedly with code {process.returncode}!", flush=True)
            break
        try:
            req = urllib.request.Request(f"http://{COMFY_URL}/system_stats")
            urllib.request.urlopen(req, timeout=1)
            print("ComfyUI API is responsive and ready!", flush=True)
            break
        except urllib.error.URLError:
            time.sleep(1)
            print("Waiting for ComfyUI to start...", flush=True)

def queue_prompt(workflow):
    client_id = str(uuid.uuid4())
    payload = {"prompt": workflow, "client_id": client_id}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(f"http://{COMFY_URL}/prompt", data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read())
            return res.get('prompt_id'), client_id
    except urllib.error.URLError as e:
        print(f"Error queueing prompt: {e}")
        return None, None

def wait_for_execution(client_id, prompt_id):
    ws = websocket.WebSocket()
    ws.connect(f"ws://{COMFY_URL}/ws?clientId={client_id}")
    while True:
        out = ws.recv()
        if isinstance(out, str):
            msg = json.loads(out)
            if msg.get('type') == 'executing':
                data = msg.get('data', {})
                if data.get('node') is None and data.get('prompt_id') == prompt_id:
                    print("Execution finished!")
                    break
    ws.close()

def fetch_history(prompt_id):
    req = urllib.request.Request(f"http://{COMFY_URL}/history/{prompt_id}")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())

def process_job(job):
    job_input = job.get('input', {})
    print(f"Received Serverless payload: {job_input}")
    
    pos_prompt = job_input.get('positive_prompt', "High quality anime style, masterpiece")
    neg_prompt = job_input.get('negative_prompt', "ugly, deformation")
    frames = job_input.get('frames', 81)
    width = job_input.get('width', 480)
    height = job_input.get('height', 832)
    style = job_input.get('style', 'none').lower()
    
    with open(API_JSON_PATH, 'r', encoding='utf-8') as f:
        graph = json.load(f)
        
    graph["6"]["inputs"]["text"] = pos_prompt
    graph["7"]["inputs"]["text"] = neg_prompt
    graph["50"]["inputs"]["length"] = frames
    graph["50"]["inputs"]["width"] = width
    graph["50"]["inputs"]["height"] = height
    
    if style == "none" or style == "":
        graph["54"]["inputs"]["model"] = ["37", 0]
        graph["101"]["inputs"]["model"] = ["100", 0]
        if "150" in graph: del graph["150"]
        if "151" in graph: del graph["151"]
    else:
        try:
            with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            if style in registry:
                graph["150"]["inputs"]["lora_name"] = registry[style]['high']
                graph["151"]["inputs"]["lora_name"] = registry[style]['low']
            else:
                return {"error": f"Style '{style}' is not found in the network volume registry."}
        except Exception as e:
            return {"error": f"Failed to open registry at {REGISTRY_PATH}: {str(e)}"}

    prompt_id, client_id = queue_prompt(graph)
    if not prompt_id:
        return {"error": "Failed to submit workflow."}
        
    print(f"Queued ID: {prompt_id}. Awaiting completion...")
    wait_for_execution(client_id, prompt_id)
    
    history = fetch_history(prompt_id)
    outputs = history.get(prompt_id, {}).get('outputs', {})
    encoded_videos = []
    
    if "47" in outputs and "gifs" in outputs["47"]:
        for video_info in outputs["47"]["gifs"]:
            filepath = os.path.join(OUTPUT_DIR, video_info.get("subfolder", ""), video_info["filename"])
            if os.path.exists(filepath):
                with open(filepath, "rb") as vf:
                    encoded_str = base64.b64encode(vf.read()).decode('utf-8')
                    encoded_videos.append(f"data:video/webm;base64,{encoded_str}")
                os.remove(filepath)
                
    return {
        "status": "success",
        "parameters_used": job_input,
        "video_count": len(encoded_videos),
        "video_base64_array": encoded_videos
    }

if __name__ == "__main__":
    start_comfyui()
    print("Handing over to RunPod Serverless SDK...")
    runpod.serverless.start({"handler": process_job})
