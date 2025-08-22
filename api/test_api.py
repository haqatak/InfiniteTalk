#!/usr/bin/env python3
"""
Test script for InfiniteTalk API
"""

import requests
import json
import time
import os

API_BASE = "http://localhost:8000"

def test_api_health():
    """Test if the API is running"""
    try:
        response = requests.get(f"{API_BASE}/")
        print(f"✅ API Health: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ API Health: {e}")
        return False

def test_queue_status():
    """Test queue status endpoint"""
    try:
        response = requests.get(f"{API_BASE}/api/queue")
        data = response.json()
        print(f"✅ Queue Status: {data}")
        return True
    except Exception as e:
        print(f"❌ Queue Status: {e}")
        return False

def test_file_upload():
    """Test file upload with sample files"""
    # Use existing example files
    image_path = "../examples/single/ref_image.png"
    audio_path = "../examples/single/1.wav"
    
    if not os.path.exists(image_path) or not os.path.exists(audio_path):
        print(f"❌ Sample files not found: {image_path}, {audio_path}")
        return False
    
    try:
        with open(image_path, 'rb') as img_file, open(audio_path, 'rb') as audio_file:
            files = {
                'image': ('test_image.png', img_file, 'image/png'),
                'audio': ('test_audio.wav', audio_file, 'audio/wav')
            }
            
            response = requests.post(f"{API_BASE}/api/generate", files=files)
            
            if response.status_code == 200:
                data = response.json()
                request_id = data['request_id']
                print(f"✅ File Upload: Request ID {request_id}")
                
                # Monitor status for a bit
                for i in range(5):
                    time.sleep(2)
                    status_response = requests.get(f"{API_BASE}/api/status/{request_id}")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"   Status: {status_data['status']} - {status_data['message']}")
                        
                        if status_data['status'] in ['completed', 'failed']:
                            break
                    else:
                        print(f"   Status check failed: {status_response.status_code}")
                        break
                
                return True
            else:
                print(f"❌ File Upload: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ File Upload: {e}")
        return False

def main():
    print("🧪 Testing InfiniteTalk API")
    print("=" * 40)
    
    # Test API health
    if not test_api_health():
        print("API is not running. Please start it first.")
        return
    
    # Test queue status
    test_queue_status()
    
    # Test file upload (optional - requires sample files)
    print("\n📁 Testing file upload...")
    print("Note: This will submit a real request to the queue!")
    user_input = input("Continue? (y/N): ").strip().lower()
    
    if user_input == 'y':
        test_file_upload()
    else:
        print("Skipping file upload test.")
    
    print("\n✅ API testing complete!")
    print(f"🌐 Web interface: {API_BASE}")

if __name__ == "__main__":
    main()
