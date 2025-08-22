#!/bin/bash
# Startup script for InfiniteTalk API

echo "Starting InfiniteTalk API Server..."
echo "=========================================="

# Change to API directory
cd /root/projects/InfiniteTalk/api

# Activate the environment
source /root/miniconda3/etc/profile.d/conda.sh
conda activate multitalk

# Create required directories
mkdir -p uploads outputs

# Check if models are available
echo "Checking for InfiniteTalk models..."
if [ ! -d "../weights/Wan2.1-I2V-14B-480P" ]; then
    echo "Warning: InfiniteTalk models not found!"
    echo "Please ensure models are downloaded in the weights directory."
fi

# Start the FastAPI server
echo "Starting FastAPI server on http://0.0.0.0:8000"
echo "=========================================="

/root/miniconda3/envs/multitalk/bin/python app.py
