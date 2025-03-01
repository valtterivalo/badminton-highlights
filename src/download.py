import os
from yt_dlp import YoutubeDL
from src import video_cache

def download_video(url, output_path=os.path.join(os.path.dirname(__file__), "..", "output", "input_video.mp4")):
    """
    Download a YouTube video, checking the cache first to avoid re-downloading.
    
    Args:
        url: YouTube URL
        output_path: Path to save the downloaded video
        
    Returns:
        str: Path to the video file (either downloaded or from cache)
    """
    # Check if video is already in cache
    cached_path = video_cache.get_cached_video_path(url)
    if cached_path:
        print(f"Video already downloaded: {cached_path}")
        return cached_path
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Download the video
    print(f"Downloading video from {url}...")
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
    }
    
    # Download the video
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get('title')
        duration = info.get('duration')
    
    # Add video to cache
    video_cache.add_video_to_cache(url, output_path, title, duration)
    
    print(f"Video downloaded to: {output_path}")
    return output_path