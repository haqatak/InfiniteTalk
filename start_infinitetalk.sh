#!/bin/bash

# ============================================================================
# InfiniteTalk Server Startup Script
# ============================================================================
# This script handles complete setup and startup of the InfiniteTalk server
# including model downloads, environment setup, and server initialization.
# ============================================================================

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/root/projects/InfiniteTalk"
CONDA_ENV="multitalk"
SERVER_PORT="8000"
WEIGHTS_DIR="$PROJECT_DIR/weights"

# Model URLs and paths
MODELS=(
    "InfiniteTalk|https://huggingface.co/piyushgit011/InfiniteTalk_14B_checkpoint|$WEIGHTS_DIR/InfiniteTalk"
    "Wan2.1-I2V-14B-480P|https://huggingface.co/Lightricks/Wan2.1-I2V-14B-480P|$WEIGHTS_DIR/Wan2.1-I2V-14B-480P"
    "chinese-wav2vec2-base|https://huggingface.co/TencentGameMate/chinese-wav2vec2-base|$WEIGHTS_DIR/chinese-wav2vec2-base"
    "lightx2v_lora|https://huggingface.co/piyushgit011/InfiniteTalk_lightx2v_lora/resolve/main/lightx2v_lora.safetensors|$WEIGHTS_DIR/lightx2v_lora.safetensors"
)

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to check if conda environment exists
check_conda_env() {
    log "Checking conda environment: $CONDA_ENV"
    if conda env list | grep -q "^$CONDA_ENV "; then
        log "Conda environment '$CONDA_ENV' found"
        return 0
    else
        error "Conda environment '$CONDA_ENV' not found"
        return 1
    fi
}

# Function to activate conda environment
activate_conda() {
    log "Activating conda environment: $CONDA_ENV"
    source /root/miniconda3/etc/profile.d/conda.sh
    conda activate $CONDA_ENV
    log "Activated environment: $(conda info --envs | grep '*' | awk '{print $1}')"
}

# Function to check if git-lfs is installed
check_git_lfs() {
    if ! command -v git-lfs &> /dev/null; then
        warning "git-lfs not found, installing..."
        apt-get update && apt-get install -y git-lfs
        git lfs install
    else
        log "git-lfs is already installed"
    fi
}

# Function to download model using git clone
download_model_git() {
    local model_name="$1"
    local model_url="$2"
    local model_path="$3"
    
    log "Downloading model: $model_name"
    
    if [[ -d "$model_path" ]] && [[ -n "$(ls -A "$model_path" 2>/dev/null)" ]]; then
        log "Model $model_name already exists at $model_path"
        return 0
    fi
    
    info "Cloning $model_name from $model_url to $model_path"
    mkdir -p "$(dirname "$model_path")"
    
    if git clone "$model_url" "$model_path"; then
        log "Successfully downloaded $model_name"
        return 0
    else
        error "Failed to download $model_name"
        return 1
    fi
}

# Function to download file using wget
download_file() {
    local file_name="$1"
    local file_url="$2"
    local file_path="$3"
    
    log "Downloading file: $file_name"
    
    if [[ -f "$file_path" ]]; then
        log "File $file_name already exists at $file_path"
        return 0
    fi
    
    info "Downloading $file_name from $file_url to $file_path"
    mkdir -p "$(dirname "$file_path")"
    
    if wget -O "$file_path" "$file_url"; then
        log "Successfully downloaded $file_name"
        return 0
    else
        error "Failed to download $file_name"
        return 1
    fi
}

# Function to download all required models
download_models() {
    log "Starting model download process..."
    
    check_git_lfs
    
    for model_info in "${MODELS[@]}"; do
        IFS='|' read -r model_name model_url model_path <<< "$model_info"
        
        if [[ "$model_url" == *.safetensors ]]; then
            download_file "$model_name" "$model_url" "$model_path"
        else
            download_model_git "$model_name" "$model_url" "$model_path"
        fi
    done
    
    log "Model download process completed"
}

# Function to verify all models are present
verify_models() {
    log "Verifying model installations..."
    
    local all_models_present=true
    
    for model_info in "${MODELS[@]}"; do
        IFS='|' read -r model_name model_url model_path <<< "$model_info"
        
        if [[ "$model_url" == *.safetensors ]]; then
            if [[ ! -f "$model_path" ]]; then
                error "Missing file: $model_path"
                all_models_present=false
            else
                log "✓ Found: $model_name"
            fi
        else
            if [[ ! -d "$model_path" ]] || [[ -z "$(ls -A "$model_path" 2>/dev/null)" ]]; then
                error "Missing or empty directory: $model_path"
                all_models_present=false
            else
                log "✓ Found: $model_name"
            fi
        fi
    done
    
    if [[ "$all_models_present" == true ]]; then
        log "All models are present and verified"
        return 0
    else
        error "Some models are missing"
        return 1
    fi
}

# Function to check Python dependencies
check_dependencies() {
    log "Checking Python dependencies..."
    
    activate_conda
    
    # Check if required packages are installed
    local required_packages=("torch" "fastapi" "uvicorn" "jinja2" "pillow" "librosa" "transformers")
    
    for package in "${required_packages[@]}"; do
        if python -c "import $package" 2>/dev/null; then
            log "✓ $package is installed"
        else
            error "✗ $package is not installed"
            info "Installing $package..."
            pip install "$package"
        fi
    done
}

# Function to stop existing server
stop_server() {
    log "Stopping any existing InfiniteTalk server..."
    pkill -f "python.*api/app.py" 2>/dev/null || true
    pkill -f "uvicorn.*api.app" 2>/dev/null || true
    sleep 2
    log "Existing servers stopped"
}

# Function to start the server
start_server() {
    log "Starting InfiniteTalk server..."
    
    cd "$PROJECT_DIR"
    activate_conda
    
    # Create necessary directories
    mkdir -p "$PROJECT_DIR/api/uploads"
    mkdir -p "$PROJECT_DIR/api/outputs"
    mkdir -p "$PROJECT_DIR/save_audio"
    
    # Set environment variables
    export CUDA_VISIBLE_DEVICES=0
    export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
    
    # Start the server
    info "Server starting on http://0.0.0.0:$SERVER_PORT"
    info "Access the web interface at: http://localhost:$SERVER_PORT"
    
    # Start in background and capture PID
    nohup python api/app.py > server.log 2>&1 &
    SERVER_PID=$!
    
    # Wait a moment and check if server started successfully
    sleep 3
    
    if kill -0 $SERVER_PID 2>/dev/null; then
        log "Server started successfully! PID: $SERVER_PID"
        log "Server logs are available in: $PROJECT_DIR/server.log"
        info "WebSocket endpoint: ws://localhost:$SERVER_PORT/ws"
        info "API documentation: http://localhost:$SERVER_PORT/docs"
        return 0
    else
        error "Server failed to start. Check server.log for details"
        return 1
    fi
}

# Function to show server status
show_status() {
    log "Checking server status..."
    
    if pgrep -f "python.*api/app.py" > /dev/null; then
        local pid=$(pgrep -f "python.*api/app.py")
        log "Server is running (PID: $pid)"
        info "Access URL: http://localhost:$SERVER_PORT"
        return 0
    else
        warning "Server is not running"
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  start         Start the InfiniteTalk server (default)"
    echo "  stop          Stop the InfiniteTalk server"
    echo "  restart       Restart the InfiniteTalk server"
    echo "  status        Show server status"
    echo "  download      Download/verify models only"
    echo "  setup         Complete setup (download models + dependencies)"
    echo "  help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                # Start server (download models if needed)"
    echo "  $0 start          # Start server"
    echo "  $0 restart        # Restart server"
    echo "  $0 download       # Download models only"
    echo "  $0 setup          # Complete setup"
}

# Main execution
main() {
    local action="${1:-start}"
    
    case "$action" in
        "start")
            log "Starting InfiniteTalk server with model verification..."
            
            # Check conda environment
            if ! check_conda_env; then
                error "Please create the conda environment first:"
                error "conda create -n $CONDA_ENV python=3.10 -y"
                exit 1
            fi
            
            # Check and download models if needed
            if ! verify_models; then
                warning "Some models are missing. Starting download..."
                download_models
                verify_models || exit 1
            fi
            
            # Check dependencies
            check_dependencies
            
            # Stop existing server and start new one
            stop_server
            start_server
            ;;
            
        "stop")
            stop_server
            ;;
            
        "restart")
            log "Restarting InfiniteTalk server..."
            stop_server
            main "start"
            ;;
            
        "status")
            show_status
            ;;
            
        "download")
            log "Downloading and verifying models..."
            download_models
            verify_models
            ;;
            
        "setup")
            log "Running complete setup..."
            
            if ! check_conda_env; then
                error "Please create the conda environment first:"
                error "conda create -n $CONDA_ENV python=3.10 -y"
                exit 1
            fi
            
            download_models
            verify_models
            check_dependencies
            log "Setup completed successfully!"
            ;;
            
        "help"|"-h"|"--help")
            show_usage
            ;;
            
        *)
            error "Unknown option: $action"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
