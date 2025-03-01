"""
Utility script to add an existing video to the cache.
This is useful for adding videos that were downloaded before 
the cache system was implemented.
"""

import os
import argparse
from src.video_cache import add_video_to_cache, extract_video_id, get_all_cached_videos

def add_existing_video(url, file_path):
    """Add an existing video to the cache."""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False
    
    video_id = extract_video_id(url)
    print(f"Adding video to cache: {video_id}")
    print(f"File path: {file_path}")
    
    add_video_to_cache(url, file_path)
    print("Video added to cache successfully.")
    return True

def list_cached_videos():
    """List all videos in the cache."""
    cache = get_all_cached_videos()
    if not cache:
        print("Cache is empty.")
        return
    
    print("\nCached Videos:")
    print("--------------")
    for video_id, info in cache.items():
        print(f"ID: {video_id}")
        print(f"URL: {info.get('url', 'N/A')}")
        print(f"Path: {info.get('file_path', 'N/A')}")
        print(f"Title: {info.get('title', 'N/A')}")
        print(f"Duration: {info.get('duration', 'N/A')} seconds")
        print(f"Downloaded: {info.get('download_date', 'N/A')}")
        print("--------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video Cache Utility")
    parser.add_argument("--add", action="store_true", help="Add a video to the cache")
    parser.add_argument("--list", action="store_true", help="List all cached videos")
    parser.add_argument("--url", type=str, help="YouTube URL", default="https://www.youtube.com/watch?v=-lE9pco8kVQ")
    parser.add_argument("--file", type=str, help="Path to the video file", default="output/temp_input.mp4")
    
    args = parser.parse_args()
    
    if args.add:
        add_existing_video(args.url, args.file)
    
    if args.list or not (args.add or args.list):
        list_cached_videos() 