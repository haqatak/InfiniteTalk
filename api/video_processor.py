#!/usr/bin/env python3
"""
Video processor for InfiniteTalk integration
"""

import os
import sys
import json
import asyncio
import subprocess
from typing import Optional, Callable, Any
from pathlib import Path

# Add parent directory to path to import InfiniteTalk modules
sys.path.append(str(Path(__file__).parent.parent))

class VideoProcessor:
    def __init__(self):
        self.infinitetalk_dir = Path(__file__).parent.parent
        self.python_env = "/root/miniconda3/envs/multitalk/bin/python"
        self.model_initialized = False
    
    async def process_video(
        self,
        image_path: str,
        audio_path: str,
        output_path: str,
        request_id: str,
        prompt: str = None,
        progress_callback: Optional[Callable[[str], Any]] = None
    ) -> bool:
        """
        Process video generation using InfiniteTalk with lightx2v LoRA
        
        Args:
            image_path: Path to reference image
            audio_path: Path to audio file
            output_path: Path to save generated video
            request_id: Unique request identifier
            progress_callback: Function to call with progress updates
            
        Returns:
            bool: True if successful, False otherwise
        """
        
        try:
            if progress_callback:
                await progress_callback("Preparing input files...")
            
            # Create temporary JSON config for this request
            config_path = os.path.join(self.infinitetalk_dir, f"api/uploads/{request_id}_config.json")
            
            # Convert paths to relative paths from InfiniteTalk root directory
            rel_image_path = os.path.relpath(image_path, self.infinitetalk_dir)
            rel_audio_path = os.path.relpath(audio_path, self.infinitetalk_dir)
            
            # Create config similar to single_example_image.json
            config = {
                "prompt": prompt or "A person speaking naturally with clear lip sync and facial expressions, professional video quality with natural lighting and smooth motion",
                "cond_video": rel_image_path,
                "cond_audio": {
                    "person1": rel_audio_path
                }
            }
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            if progress_callback:
                await progress_callback("Starting InfiniteTalk model...")
            
            # Make sure config path is relative to the working directory
            relative_config_path = f"api/uploads/{request_id}_config.json"
            relative_output_path = f"api/{output_path.replace('.mp4', '')}"
            
            # Prepare the command
            cmd = [
                self.python_env,
                "generate_infinitetalk.py",
                "--ckpt_dir", "weights/Wan2.1-I2V-14B-480P",
                "--wav2vec_dir", "weights/chinese-wav2vec2-base",
                "--infinitetalk_dir", "weights/InfiniteTalk/single/infinitetalk.safetensors",
                "--lora_dir", "weights/lightx2v_lora.safetensors",
                "--input_json", relative_config_path,
                "--lora_scale", "1.0",
                "--size", "infinitetalk-480",
                "--sample_text_guide_scale", "1.0",
                "--sample_audio_guide_scale", "2.0",
                "--sample_steps", "6",  # lightx2v 4-step acceleration
                "--mode", "streaming",
                "--motion_frame", "9",
                "--sample_shift", "2",
                "--num_persistent_param_in_dit", "0",
                "--save_file", relative_output_path
            ]
            
            if progress_callback:
                await progress_callback("Loading models (T5, VAE, CLIP, DiT)...")
            
            # Run the process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.infinitetalk_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=dict(os.environ, PYTHONPATH=str(self.infinitetalk_dir))
            )
            
            # Monitor progress
            progress_messages = [
                ("loading weights/Wan2.1-I2V-14B-480P/models_t5_umt5-xxl-enc-bf16.pth", "Loading T5 text encoder..."),
                ("loading weights/Wan2.1-I2V-14B-480P/Wan2.1_VAE.pth", "Loading VAE decoder..."),
                ("loading weights/Wan2.1-I2V-14B-480P/models_clip", "Loading CLIP vision encoder..."),
                ("Creating WanModel", "Loading 14B DiT transformer..."),
                ("Loading LoRA weights", "Applying lightx2v LoRA..."),
                ("Applied LoRA", "lightx2v LoRA applied successfully"),
                ("Generating video", "Starting video generation..."),
                ("No conversion needed", "Processing audio embedding..."),
                ("Video generation completed", "Video generation completed!")
            ]
            
            # Read output line by line
            async def read_output():
                if process.stdout:
                    async for line in process.stdout:
                        line_str = line.decode().strip()
                        
                        # Check for progress indicators
                        for trigger, message in progress_messages:
                            if trigger in line_str:
                                if progress_callback:
                                    await progress_callback(message)
                                break
                        
                        # Log the line for debugging
                        print(f"[{request_id}] {line_str}")
            
            # Start reading output
            output_task = asyncio.create_task(read_output())
            
            # Wait for process to complete
            await process.wait()
            
            # Wait for output reading to complete
            await output_task
            
            # Check if process was successful
            if process.returncode == 0:
                # Check if output file was created
                expected_output = f"{output_path.replace('.mp4', '')}.mp4"
                if os.path.exists(expected_output):
                    # Move to final location if needed
                    if expected_output != output_path:
                        os.rename(expected_output, output_path)
                    
                    if progress_callback:
                        await progress_callback("Video generation completed successfully!")
                    
                    # Cleanup temporary files
                    try:
                        os.remove(config_path)
                        os.remove(image_path)
                        os.remove(audio_path)
                    except:
                        pass
                    
                    return True
                else:
                    if progress_callback:
                        await progress_callback("Error: Output file not created")
                    return False
            else:
                # Read error output
                error_msg = "Process failed"
                if process.stderr:
                    try:
                        error_output = await process.stderr.read()
                        error_msg = error_output.decode().strip()
                        if not error_msg:
                            error_msg = f"Process exited with code {process.returncode}"
                    except:
                        error_msg = f"Process exited with code {process.returncode}"
                
                print(f"[{request_id}] Error: {error_msg}")
                
                if progress_callback:
                    await progress_callback(f"Error: {error_msg[:100]}...")
                
                return False
                
        except Exception as e:
            print(f"[{request_id}] Exception: {str(e)}")
            if progress_callback:
                await progress_callback(f"Error: {str(e)}")
            return False
    
    def is_model_ready(self) -> bool:
        """Check if model files are available"""
        required_files = [
            "weights/Wan2.1-I2V-14B-480P/models_t5_umt5-xxl-enc-bf16.pth",
            "weights/Wan2.1-I2V-14B-480P/Wan2.1_VAE.pth", 
            "weights/Wan2.1-I2V-14B-480P/models_clip_open-clip-xlm-roberta-large-vit-huge-14.pth",
            "weights/chinese-wav2vec2-base",
            "weights/InfiniteTalk/single/infinitetalk.safetensors",
            "weights/lightx2v_lora.safetensors"
        ]
        
        for file_path in required_files:
            full_path = self.infinitetalk_dir / file_path
            if not full_path.exists():
                return False
        
        return True
    
    def get_model_info(self) -> dict:
        """Get information about the model setup"""
        return {
            "model_ready": self.is_model_ready(),
            "lightx2v_enabled": True,
            "sample_steps": 4,
            "resolution": "480p",
            "mode": "streaming",
            "offload_enabled": True
        }
