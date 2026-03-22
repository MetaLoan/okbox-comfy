#!/bin/bash
set -e

# Install RunPod Serverless SDK and necessary video dependencies
pip install --no-cache-dir runpod imageio[ffmpeg] opencv-python accelerate

# Optional: Since the heavy 30GB Model is mounted via Network Volume at /workspace/ComfyUI_serverless
# We don't download them here. We just leave the container stripped and ready to link!
echo "Builder setup complete."
