"""
Simple test script to verify the video caching system.
"""

import os
from video_cache import get_cached_video_path, add_video_to_cache, get_all_cached_videos

# Test URL
url = "https://www.youtube.com/watch?v=-lE9pco8kVQ"

# Check if video is in cache
print("Checking cache for video...")
cached_path = get_cached_video_path(url)

if cached_path:
    print(f"Video found in cache at: {cached_path}")
else:
    print("Video not found in cache")
    
    # Add to cache if it exists in output directory
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    test_path = os.path.join(output_dir, "temp_input.mp4")
    
    if os.path.exists(test_path):
        print(f"Adding existing video to cache: {test_path}")
        add_video_to_cache(url, test_path, "Test video", 3600)
        print("Video added to cache")
    else:
        print(f"No video found at {test_path}")

# List all cached videos
print("\nAll cached videos:")
print("-----------------")
videos = get_all_cached_videos()
if videos:
    for video_id, info in videos.items():
        print(f"ID: {video_id}")
        print(f"Path: {info.get('file_path')}")
        print(f"Title: {info.get('title')}")
        print("-----------------")
else:
    print("No videos in cache") 