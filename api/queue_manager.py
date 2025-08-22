#!/usr/bin/env python3
"""
Queue management system for InfiniteTalk video generation
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque
import threading

class QueueManager:
    def __init__(self, max_queue_size: int = 20, max_concurrent: int = 3):
        self.max_queue_size = max_queue_size
        self.max_concurrent = max_concurrent
        
        # Thread-safe collections
        self._lock = threading.Lock()
        
        # Queue for pending requests
        self._queue: deque = deque()
        
        # Currently processing requests
        self._processing: Dict[str, Dict[str, Any]] = {}
        
        # Completed/failed requests (keep for a while for status checking)
        self._completed: Dict[str, Dict[str, Any]] = {}
        
        # Request lookup by ID
        self._all_requests: Dict[str, Dict[str, Any]] = {}
    
    def add_to_queue(self, request_item: Dict[str, Any]) -> bool:
        """Add a request to the queue"""
        with self._lock:
            if len(self._queue) >= self.max_queue_size:
                return False
            
            request_item["queued_at"] = time.time()
            request_item["status"] = "queued"
            
            self._queue.append(request_item)
            self._all_requests[request_item["request_id"]] = request_item
            
            return True
    
    def get_next_item(self) -> Optional[Dict[str, Any]]:
        """Get the next item from the queue"""
        with self._lock:
            if self._queue:
                return self._queue.popleft()
            return None
    
    def start_processing(self, request_id: str) -> bool:
        """Move a request from queue to processing"""
        with self._lock:
            if len(self._processing) >= self.max_concurrent:
                return False
            
            if request_id in self._all_requests:
                request_item = self._all_requests[request_id]
                request_item["status"] = "processing"
                request_item["started_at"] = time.time()
                
                self._processing[request_id] = request_item
                return True
            
            return False
    
    def complete_request(self, request_id: str, result_url: str = None):
        """Mark a request as completed"""
        with self._lock:
            if request_id in self._processing:
                request_item = self._processing.pop(request_id)
                request_item["status"] = "completed"
                request_item["completed_at"] = time.time()
                request_item["result_url"] = result_url
                
                self._completed[request_id] = request_item
                self._all_requests[request_id] = request_item
    
    def fail_request(self, request_id: str, error_message: str):
        """Mark a request as failed"""
        with self._lock:
            if request_id in self._processing:
                request_item = self._processing.pop(request_id)
                request_item["status"] = "failed"
                request_item["error"] = error_message
                request_item["failed_at"] = time.time()
                
                self._completed[request_id] = request_item
                self._all_requests[request_id] = request_item
    
    def update_request_status(self, request_id: str, status: str, message: str = ""):
        """Update the status of a request"""
        with self._lock:
            if request_id in self._all_requests:
                self._all_requests[request_id]["status"] = status
                self._all_requests[request_id]["message"] = message
                self._all_requests[request_id]["last_updated"] = time.time()
                
                # Update in processing dict if it exists there
                if request_id in self._processing:
                    self._processing[request_id]["status"] = status
                    self._processing[request_id]["message"] = message
                    self._processing[request_id]["last_updated"] = time.time()
    
    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific request"""
        with self._lock:
            return self._all_requests.get(request_id)
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        with self._lock:
            return len(self._queue)
    
    def get_processing_count(self) -> int:
        """Get current processing count"""
        with self._lock:
            return len(self._processing)
    
    def can_start_processing(self) -> bool:
        """Check if we can start processing a new request"""
        with self._lock:
            return len(self._processing) < self.max_concurrent and len(self._queue) > 0
    
    def get_queue_position(self, request_id: str) -> Optional[int]:
        """Get position in queue (1-based)"""
        with self._lock:
            for i, item in enumerate(self._queue):
                if item["request_id"] == request_id:
                    return i + 1
            return None
    
    def get_all_requests(self) -> List[Dict[str, Any]]:
        """Get all queued requests"""
        with self._lock:
            return list(self._queue)
    
    def get_processing_requests(self) -> List[Dict[str, Any]]:
        """Get all currently processing requests"""
        with self._lock:
            return list(self._processing.values())
    
    def get_completed_requests(self) -> List[Dict[str, Any]]:
        """Get all completed requests"""
        with self._lock:
            return list(self._completed.values())
    
    def cleanup_old_requests(self, max_age_hours: int = 24):
        """Remove old completed/failed requests"""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        with self._lock:
            to_remove = []
            for request_id, request_item in self._completed.items():
                completed_at = request_item.get("completed_at") or request_item.get("failed_at", 0)
                if completed_at < cutoff_time:
                    to_remove.append(request_id)
            
            for request_id in to_remove:
                self._completed.pop(request_id, None)
                self._all_requests.pop(request_id, None)
    
    def get_estimated_wait_time(self, request_id: str) -> Optional[str]:
        """Get estimated wait time for a request"""
        position = self.get_queue_position(request_id)
        if position is None:
            return None
        
        # Rough estimate: 2-5 minutes per video
        avg_processing_time = 3.5 * 60  # 3.5 minutes in seconds
        estimated_seconds = position * avg_processing_time
        
        if estimated_seconds < 60:
            return f"{int(estimated_seconds)} seconds"
        elif estimated_seconds < 3600:
            return f"{int(estimated_seconds / 60)} minutes"
        else:
            hours = int(estimated_seconds / 3600)
            minutes = int((estimated_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get detailed queue statistics"""
        with self._lock:
            total_requests = len(self._all_requests)
            queued_count = len(self._queue)
            processing_count = len(self._processing)
            completed_count = len([r for r in self._completed.values() if r["status"] == "completed"])
            failed_count = len([r for r in self._completed.values() if r["status"] == "failed"])
            
            return {
                "total_requests": total_requests,
                "queued": queued_count,
                "processing": processing_count,
                "completed": completed_count,
                "failed": failed_count,
                "queue_utilization": queued_count / self.max_queue_size,
                "processing_utilization": processing_count / self.max_concurrent
            }
    
    def remove_request(self, request_id: str) -> bool:
        """Remove a request from all tracking structures"""
        with self._lock:
            removed = False
            
            # Remove from queue if present
            self._queue = [req for req in self._queue if req["request_id"] != request_id]
            
            # Remove from processing if present
            if request_id in self._processing:
                del self._processing[request_id]
                removed = True
            
            # Remove from completed if present
            if request_id in self._completed:
                del self._completed[request_id]
                removed = True
            
            # Remove from all requests if present
            self._all_requests = [req for req in self._all_requests if req["request_id"] != request_id]
            
            return removed
