#!/usr/bin/env python3
"""
FastAPI server for InfiniteTalk video generation with queue management
"""

import os
import sys
import asyncio
import uuid
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.requests import Request
from pydantic import BaseModel

# Add parent directory to path to import InfiniteTalk modules
sys.path.append(str(Path(__file__).parent.parent))

from queue_manager import QueueManager
from video_processor import VideoProcessor

# Initialize FastAPI app
app = FastAPI(title="InfiniteTalk API", description="Audio-driven video generation with lightx2v acceleration")

# Mount templates
templates = Jinja2Templates(directory="api/templates")

# Initialize queue manager and video processor
queue_manager = QueueManager(max_queue_size=20, max_concurrent=3)
video_processor = VideoProcessor()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Pydantic models
class ProcessingRequest(BaseModel):
    request_id: str
    status: str
    message: str
    timestamp: str
    position_in_queue: Optional[int] = None
    estimated_time: Optional[str] = None
    result_url: Optional[str] = None

class QueueStatus(BaseModel):
    queue_size: int
    processing_count: int
    max_queue_size: int
    max_concurrent: int
    requests: List[ProcessingRequest]

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/generate", response_model=ProcessingRequest)
async def generate_video(
    image: UploadFile = File(..., description="Reference image"),
    audio: UploadFile = File(..., description="Audio file"),
    prompt: str = Form(None, description="Optional prompt for video generation")
):
    """Submit a video generation request"""
    
    # Validate file types
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
    audio_extensions = ['.wav', '.mp3', '.flac', '.aac', '.ogg']
    
    image_ext = Path(image.filename).suffix.lower()
    audio_ext = Path(audio.filename).suffix.lower()
    
    if image_ext not in image_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid image file type. Supported: {image_extensions}")
    
    if audio_ext not in audio_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid audio file type. Supported: {audio_extensions}")
    
    # Check queue capacity
    if queue_manager.get_queue_size() >= queue_manager.max_queue_size:
        raise HTTPException(status_code=429, detail="Queue is full. Please try again later.")
    
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    
    # Save uploaded files
    image_path = f"uploads/{request_id}_image{Path(image.filename).suffix}"
    audio_path = f"uploads/{request_id}_audio{Path(audio.filename).suffix}"
    
    with open(image_path, "wb") as f:
        content = await image.read()
        f.write(content)
    
    with open(audio_path, "wb") as f:
        content = await audio.read()
        f.write(content)
    
    # Add to queue
    queue_item = {
        "request_id": request_id,
        "image_path": image_path,
        "audio_path": audio_path,
        "prompt": prompt,
        "timestamp": datetime.now().isoformat(),
        "status": "queued"
    }
    
    queue_manager.add_to_queue(queue_item)
    
    # Broadcast queue update
    await manager.broadcast(json.dumps({
        "type": "queue_update",
        "data": await get_queue_status_data()
    }))
    
    # Start processing if possible
    asyncio.create_task(process_queue())
    
    return ProcessingRequest(
        request_id=request_id,
        status="queued",
        message="Request added to queue",
        timestamp=queue_item["timestamp"],
        position_in_queue=queue_manager.get_queue_position(request_id)
    )

@app.get("/api/status/{request_id}", response_model=ProcessingRequest)
async def get_request_status(request_id: str):
    """Get status of a specific request"""
    status = queue_manager.get_request_status(request_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return ProcessingRequest(
        request_id=request_id,
        status=status["status"],
        message=status.get("message", ""),
        timestamp=status["timestamp"],
        position_in_queue=queue_manager.get_queue_position(request_id),
        estimated_time=status.get("estimated_time"),
        result_url=status.get("result_url")
    )

@app.get("/api/queue", response_model=QueueStatus)
async def get_queue_status():
    """Get current queue status"""
    return QueueStatus(**(await get_queue_status_data()))

async def get_queue_status_data() -> Dict[str, Any]:
    """Helper function to get queue status data"""
    queue_items = queue_manager.get_all_requests()
    processing_items = queue_manager.get_processing_requests()
    
    requests = []
    for item in queue_items + processing_items:
        request_obj = ProcessingRequest(
            request_id=item["request_id"],
            status=item["status"],
            message=item.get("message", ""),
            timestamp=item["timestamp"],
            position_in_queue=queue_manager.get_queue_position(item["request_id"]) if item["status"] == "queued" else None,
            estimated_time=item.get("estimated_time"),
            result_url=item.get("result_url")
        )
        requests.append(request_obj.dict())
    
    return {
        "queue_size": queue_manager.get_queue_size(),
        "processing_count": queue_manager.get_processing_count(),
        "max_queue_size": queue_manager.max_queue_size,
        "max_concurrent": queue_manager.max_concurrent,
        "requests": requests
    }

@app.get("/api/result/{request_id}")
async def get_result(request_id: str):
    """Download the generated video"""
    status = queue_manager.get_request_status(request_id)
    
    if not status or status["status"] != "completed":
        raise HTTPException(status_code=404, detail="Video not ready or request not found")
    
    video_path = f"outputs/{request_id}.mp4"
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"infinitetalk_{request_id}.mp4"
    )

@app.delete("/api/result/{request_id}")
async def delete_result(request_id: str):
    """Delete the generated video and associated files"""
    try:
        # Delete video file
        video_path = f"outputs/{request_id}.mp4"
        if os.path.exists(video_path):
            os.remove(video_path)
        
        # Delete uploaded files if they exist
        for ext in ['.png', '.jpg', '.jpeg', '.wav', '.mp3', '.flac']:
            image_path = f"uploads/{request_id}_image{ext}"
            audio_path = f"uploads/{request_id}_audio{ext}"
            if os.path.exists(image_path):
                os.remove(image_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
        
        # Delete config file
        config_path = f"uploads/{request_id}_config.json"
        if os.path.exists(config_path):
            os.remove(config_path)
        
        # Remove from queue manager if it exists
        queue_manager.remove_request(request_id)
        
        return {"message": "Video and associated files deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting files: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        # Send initial queue status
        await websocket.send_text(json.dumps({
            "type": "queue_update",
            "data": await get_queue_status_data()
        }))
        
        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await websocket.send_text(json.dumps({"type": "pong", "data": data}))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def process_queue():
    """Background task to process the queue"""
    while queue_manager.can_start_processing():
        queue_item = queue_manager.get_next_item()
        if queue_item:
            # Start processing
            queue_manager.start_processing(queue_item["request_id"])
            
            # Broadcast status update
            await manager.broadcast(json.dumps({
                "type": "status_update",
                "data": {
                    "request_id": queue_item["request_id"],
                    "status": "processing",
                    "message": "Video generation started"
                }
            }))
            
            await manager.broadcast(json.dumps({
                "type": "queue_update",
                "data": await get_queue_status_data()
            }))
            
            # Process in background
            asyncio.create_task(process_video(queue_item))

async def process_video(queue_item: Dict[str, Any]):
    """Process a single video generation request"""
    request_id = queue_item["request_id"]
    
    try:
        # Update status
        queue_manager.update_request_status(request_id, "processing", "Initializing models...")
        await manager.broadcast(json.dumps({
            "type": "status_update",
            "data": {
                "request_id": request_id,
                "status": "processing",
                "message": "Initializing models..."
            }
        }))
        
        # Create output filename
        output_path = f"outputs/{request_id}.mp4"
        
        # Process video using InfiniteTalk
        success = await video_processor.process_video(
            image_path=queue_item["image_path"],
            audio_path=queue_item["audio_path"],
            output_path=output_path,
            request_id=request_id,
            prompt=queue_item.get("prompt"),
            progress_callback=lambda msg: asyncio.create_task(send_progress_update(request_id, msg))
        )
        
        if success:
            # Mark as completed
            queue_manager.complete_request(request_id, result_url=f"/api/result/{request_id}")
            
            await manager.broadcast(json.dumps({
                "type": "status_update",
                "data": {
                    "request_id": request_id,
                    "status": "completed",
                    "message": "Video generation completed!",
                    "result_url": f"/api/result/{request_id}"
                }
            }))
        else:
            # Mark as failed
            queue_manager.fail_request(request_id, "Video generation failed")
            
            await manager.broadcast(json.dumps({
                "type": "status_update",
                "data": {
                    "request_id": request_id,
                    "status": "failed",
                    "message": "Video generation failed"
                }
            }))
    
    except Exception as e:
        # Mark as failed
        queue_manager.fail_request(request_id, f"Error: {str(e)}")
        
        await manager.broadcast(json.dumps({
            "type": "status_update",
            "data": {
                "request_id": request_id,
                "status": "failed",
                "message": f"Error: {str(e)}"
            }
        }))
    
    finally:
        # Update queue status
        await manager.broadcast(json.dumps({
            "type": "queue_update",
            "data": await get_queue_status_data()
        }))
        
        # Try to process next item
        await process_queue()

async def send_progress_update(request_id: str, message: str):
    """Send progress update via WebSocket"""
    await manager.broadcast(json.dumps({
        "type": "progress_update",
        "data": {
            "request_id": request_id,
            "message": message
        }
    }))

if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    
    # Run the server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
