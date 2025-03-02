"""
Test script for validating audio preservation in the highlights compilation process.
This script extracts a 1-minute clip from an existing video and simulates rally detection
by manually defining segments within that clip.
"""

import os
from moviepy.editor import VideoFileClip
from compile import compile_highlights

def create_test_clip(input_path, output_path, start_time=600, duration=60):
    """
    Extract a test clip from the input video.
    
    Args:
        input_path: Path to the original video
        output_path: Path to save the test clip
        start_time: Start time in seconds (default: 10 minutes)
        duration: Duration in seconds (default: 1 minute)
    """
    print(f"Extracting {duration}s test clip starting at {start_time}s...")
    clip = VideoFileClip(input_path)
    subclip = clip.subclip(start_time, start_time + duration)
    subclip.write_videofile(output_path, codec='libx264', audio_codec='aac')
    clip.close()
    subclip.close()
    print(f"Test clip saved to {output_path}")

def test_highlight_compilation():
    """Run a test of the highlight compilation with audio preservation."""
    # Paths
    base_dir = os.path.dirname(__file__)
    output_dir = os.path.join(base_dir, "output")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Define file paths
    input_video = os.path.join(output_dir, "temp_input.mp4")
    test_clip_path = os.path.join(output_dir, "test_clip.mp4")
    test_output_path = os.path.join(output_dir, "test_highlights.mp4")
    
    # Check if input video exists
    if not os.path.exists(input_video):
        print(f"Error: Input video not found at {input_video}")
        print("Please make sure you have downloaded the video first.")
        return
    
    # Extract a 1-minute test clip starting at 10 minutes
    create_test_clip(input_video, test_clip_path)
    
    # Simulate rally segments within the 1-minute clip
    # Format: list of (start_time, end_time) in seconds, relative to the clip
    simulated_rallies = [
        (5, 15),    # 10-second rally
        (25, 40),   # 15-second rally
        (45, 55)    # 10-second rally
    ]
    
    # Compile highlights with audio
    print("Compiling test highlights with audio...")
    compile_highlights(test_clip_path, test_output_path, simulated_rallies)
    
    print(f"\nTest completed successfully!")
    print(f"Original test clip: {test_clip_path}")
    print(f"Highlights with audio: {test_output_path}")
    print("\nCheck that both files have audio and compare them.")

if __name__ == "__main__":
    test_highlight_compilation() 