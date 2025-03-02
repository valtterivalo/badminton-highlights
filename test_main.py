"""
Simplified test script for the main functionality focusing on download caching.
"""

import os
from download import download_video

def main():
    # URL to test
    url = "https://www.youtube.com/watch?v=-lE9pco8kVQ"
    
    # Output path
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "input_video.mp4")
    
    # Try to download (should use cache)
    print(f"Attempting to download video from: {url}")
    video_path = download_video(url, output_path)
    
    print(f"Video path: {video_path}")
    if os.path.exists(video_path):
        print(f"Video size: {os.path.getsize(video_path) / (1024*1024):.2f} MB")
    else:
        print("Video file not found!")

if __name__ == "__main__":
    main() 