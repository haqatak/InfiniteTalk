# InfiniteTalk API

A FastAPI-based web service for audio-driven video generation using InfiniteTalk with LightX2V acceleration.

## Features

- 🎥 **Audio-driven video generation** with single person lip-sync
- ⚡ **LightX2V acceleration** - 4-step inference (vs standard 40 steps)
- 📊 **Real-time queue management** with WebSocket updates
- 🔄 **Concurrent processing** - up to 3 videos simultaneously
- 📱 **Modern web interface** with drag-and-drop file upload
- 🎯 **Request tracking** with unique IDs and status updates

## Quick Start

### 1. Prerequisites

Ensure InfiniteTalk models are downloaded and available:
```bash
# Models should be in /root/projects/InfiniteTalk/weights/
- Wan2.1-I2V-14B-480P/
- chinese-wav2vec2-base/
- InfiniteTalk/single/infinitetalk.safetensors
- lightx2v_lora.safetensors
```

### 2. Start the API Server

```bash
cd /root/projects/InfiniteTalk/api
./start_api.sh
```

Or manually:
```bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate multitalk
cd /root/projects/InfiniteTalk/api
python app.py
```

### 3. Access the Web Interface

Open your browser and go to: `http://localhost:8000`

## API Endpoints

### POST `/api/generate`
Submit a video generation request.

**Form Data:**
- `image`: Reference image file (max 10MB)
- `audio`: Audio file (max 50MB)

**Response:**
```json
{
  "request_id": "uuid",
  "status": "queued",
  "message": "Request added to queue",
  "timestamp": "2025-08-22T14:30:00",
  "position_in_queue": 1
}
```

### GET `/api/status/{request_id}`
Get the status of a specific request.

**Response:**
```json
{
  "request_id": "uuid",
  "status": "processing",
  "message": "Loading models...",
  "timestamp": "2025-08-22T14:30:00",
  "position_in_queue": null,
  "estimated_time": "3 minutes",
  "result_url": null
}
```

### GET `/api/queue`
Get current queue status.

**Response:**
```json
{
  "queue_size": 2,
  "processing_count": 1,
  "max_queue_size": 20,
  "max_concurrent": 3,
  "requests": [...]
}
```

### GET `/api/result/{request_id}`
Download the generated video (when status is "completed").

### WebSocket `/ws`
Real-time updates for queue status and processing progress.

**Message Types:**
- `queue_update`: Queue status changed
- `status_update`: Request status changed
- `progress_update`: Processing progress update

## Configuration

### Queue Settings
- **Max Queue Size**: 20 requests
- **Max Concurrent**: 3 simultaneous processing
- **File Size Limits**: 10MB images, 50MB audio

### Model Settings
- **Resolution**: 480p
- **Frame Rate**: 16 FPS
- **Inference Steps**: 4 (with LightX2V LoRA)
- **Mode**: Streaming for infinite-length videos

## File Structure

```
api/
├── app.py                 # Main FastAPI application
├── queue_manager.py       # Queue management system
├── video_processor.py     # InfiniteTalk integration
├── requirements.txt       # Python dependencies
├── start_api.sh          # Startup script
├── templates/
│   └── index.html        # Web interface
├── uploads/              # Temporary uploaded files
└── outputs/             # Generated videos
```

## Processing Flow

1. **Upload**: User uploads image and audio files
2. **Queue**: Request added to queue with unique ID
3. **Processing**: When slot available, InfiniteTalk starts:
   - Load T5 text encoder (11B params)
   - Load VAE decoder
   - Load CLIP vision encoder
   - Load DiT transformer (14B params)
   - Apply LightX2V LoRA
   - Generate video (4 steps)
4. **Complete**: Video available for download

## Monitoring

The web interface provides real-time monitoring of:
- Queue size and position
- Processing status and progress
- Model loading stages
- Error messages
- Download links for completed videos

## Development

### Adding New Features

1. **Custom LoRA**: Modify `video_processor.py` to support different LoRA files
2. **Resolution Options**: Add resolution parameters to the API
3. **Batch Processing**: Extend queue manager for batch requests
4. **Authentication**: Add user authentication for production use

### API Testing

```bash
# Test file upload
curl -X POST "http://localhost:8000/api/generate" \
  -F "image=@test_image.jpg" \
  -F "audio=@test_audio.wav"

# Check queue status
curl "http://localhost:8000/api/queue"

# Download result
curl "http://localhost:8000/api/result/{request_id}" -o video.mp4
```

## Troubleshooting

### Common Issues

1. **Models not found**: Ensure all model files are downloaded and in the correct paths
2. **CUDA memory error**: Reduce concurrent processing or enable model offloading
3. **Flash Attention error**: Ensure compatible version (2.8.2) is installed
4. **WebSocket connection failed**: Check firewall settings and port availability

### Logs

Check the terminal output for detailed error messages and processing status.

## Performance

### Typical Processing Times
- **Model Loading**: 2-3 minutes (first request)
- **Video Generation**: 2-5 minutes per video
- **Queue Throughput**: ~3 videos per 5-10 minutes

### Resource Requirements
- **GPU Memory**: 16GB+ recommended
- **RAM**: 32GB+ recommended
- **Storage**: ~100GB for models + generated videos
