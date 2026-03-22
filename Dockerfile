FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04

# System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgl1-mesa-glx git wget curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# App Directory
WORKDIR /src

# Copy Handler and Build Scripts
COPY builder.sh /src/builder.sh
COPY handler.py /src/handler.py
COPY start.sh /src/start.sh

# Make Scripts Executable
RUN chmod +x /src/builder.sh /src/start.sh

# Run the builder script to pre-install ComfyUI and extensions (Minus models!)
RUN /src/builder.sh

# Set the Startup Command
CMD ["/src/start.sh"]
