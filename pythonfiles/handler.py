import runpod
import os
import sys
import subprocess
import time
import requests
import json
import base64
import uuid

# Define paths for the Serverless ComfyUI
COMFY_DIR = "/workspace/ComfyUI_serverless"
API_WORKFLOW_PATH = "/workspace/workflow_api.json"
sys.path.append(COMFY_DIR)

print("Starting internal ComfyUI server for Wan 2.2 processing...")
comfy_process = subprocess.Popen(
    ["python3", "main.py", "--port", "8188", "--disable-auto-launch"],
    cwd=COMFY_DIR,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

def wait_for_comfyui():
    """Poll the system_stats endpoint until ComfyUI is fully booted and ready."""
    while True:
        try:
            r = requests.get("http://127.0.0.1:8188/system_stats", timeout=2)
            if r.status_code == 200:
                print("ComfyUI Serverless Endpoint Ready!")
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)

wait_for_comfyui()

def submit_prompt(workflow):
    """Sends the API graph to ComfyUI for execution."""
    p = {"prompt": workflow}
    data = json.dumps(p).encode('utf-8')
    req = requests.post("http://127.0.0.1:8188/prompt", data=data, headers={'Content-Type': 'application/json'})
    return req.json()

def get_history(prompt_id):
    """Fetches the state of a specific prompt execution."""
    res = requests.get(f"http://127.0.0.1:8188/history/{prompt_id}")
    return res.json()

def handler(job):
    """The main RunPod Serverless invocation handler."""
    job_input = job['input']
    
    # 1. Load the pristine API Workflow JSON saved dynamically from the server
    with open(API_WORKFLOW_PATH, 'r') as f:
        workflow = json.load(f)
        
    # 2. Parse User Input (base64 image, positive prompt string)
    base_image_b64 = job_input.get('base_image')
    custom_prompt = job_input.get('prompt')
    
    # 3. Dynamic Injection -> Overwrite the loaded API JSON
    if base_image_b64:
        img_data = base64.b64decode(base_image_b64)
        img_name = f"req_{uuid.uuid4().hex}.png"
        img_path = os.path.join(COMFY_DIR, "input", img_name)
        with open(img_path, "wb") as f:
            f.write(img_data)
            
        # Find LoadImage node and replace the image name dynamically
        for node_id, node in workflow.items():
            if node.get('class_type') == 'LoadImage':
                node['inputs']['image'] = img_name
                
    if custom_prompt:
        for node_id, node in workflow.items():
            if node.get('class_type') == 'CLIPTextEncode' and 'text' in node['inputs']:
                # The positive prompt features the long sequence (At 0 seconds...)
                if "At " in node['inputs']['text']:
                    node['inputs']['text'] = custom_prompt
                    
    # 4. Trigger Execution
    prompt_res = submit_prompt(workflow)
    if 'prompt_id' not in prompt_res:
        return {"error": "Failed to submit workflow to ComfyUI", "details": prompt_res}
        
    prompt_id = prompt_res['prompt_id']
    print(f"Executing Queue Prompt ID: {prompt_id}")
    
    # 5. Poll for Completion
    while True:
        history = get_history(prompt_id)
        if prompt_id in history:
            outputs = history[prompt_id]['outputs']
            # Search outputs for the .webm or .mp4 file
            for n_id, n_out in outputs.items():
                if 'images' in n_out:
                    for media in n_out['images']:
                        if media['filename'].endswith('.webm') or media['filename'].endswith('.mp4'):
                            media_path = os.path.join(COMFY_DIR, "output", media['filename'])
                            # Convert final video back to base64
                            with open(media_path, 'rb') as f:
                                encoded_video = base64.b64encode(f.read()).decode('utf-8')
                            return {"status": "success", "video_base64": encoded_video}
            return {"error": "Execution finished but no video output found in node outputs.", "raw_outputs": outputs}
        time.sleep(2)

print("RunPod Serverless Handler Init. Listening for jobs...")
runpod.serverless.start({"handler": handler})
