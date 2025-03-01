"""
Module for tracking and managing downloaded YouTube videos.
This prevents re-downloading videos that have already been processed.
"""

import os
import json
import re
from urllib.parse import urlparse, parse_qs

# Path for the video cache file
CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "output", "video_cache.json")

def extract_video_id(url):
    """
    Extract the YouTube video ID from a URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        str: YouTube video ID
    """
    # Handle different URL formats
    if 'youtu.be' in url:
        # Short URL format: https://youtu.be/VIDEO_ID
        return url.split('/')[-1].split('?')[0]
    
    # Standard format: https://www.youtube.com/watch?v=VIDEO_ID
    parsed_url = urlparse(url)
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if 'v' in parse_qs(parsed_url.query):
            return parse_qs(parsed_url.query)['v'][0]
    
    # If we couldn't extract the ID, just return the URL as a fallback
    return url

def load_cache():
    """Load the video cache from disk."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Cache file {CACHE_FILE} is corrupted. Creating a new one.")
            return {}
    else:
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        return {}

def save_cache(cache):
    """Save the video cache to disk."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def get_cached_video_path(url):
    """
    Check if a video has already been downloaded.
    
    Args:
        url: YouTube URL
        
    Returns:
        str or None: Path to the cached video file, or None if not found
    """
    video_id = extract_video_id(url)
    cache = load_cache()
    
    if video_id in cache:
        path = cache[video_id]['file_path']
        if os.path.exists(path):
            return path
        else:
            # File was deleted, remove from cache
            del cache[video_id]
            save_cache(cache)
    
    return None

def add_video_to_cache(url, file_path, title=None, duration=None):
    """
    Add a downloaded video to the cache.
    
    Args:
        url: YouTube URL
        file_path: Path to the downloaded video file
        title: Video title (optional)
        duration: Video duration in seconds (optional)
    """
    video_id = extract_video_id(url)
    cache = load_cache()
    
    cache[video_id] = {
        'url': url,
        'file_path': file_path,
        'title': title,
        'duration': duration,
        'download_date': os.path.getmtime(file_path) if os.path.exists(file_path) else None
    }
    
    save_cache(cache)
    
def get_all_cached_videos():
    """
    Get all cached videos.
    
    Returns:
        dict: Dictionary of all cached videos
    """
    return load_cache() 