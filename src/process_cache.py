"""
Module for caching processed video files and their results.
This prevents re-processing videos that have already been processed.
"""

import os
import json
import hashlib
from pathlib import Path
import time

# Path for the process cache file
CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "output", "process_cache.json")

def generate_process_id(video_path, process_params):
    """
    Generate a unique ID for a processing operation based on the input file and parameters.
    
    Args:
        video_path: Path to the input video file
        process_params: Dictionary of processing parameters
    
    Returns:
        str: Unique process ID
    """
    # Convert parameters to a stable string representation
    params_str = json.dumps(process_params, sort_keys=True)
    
    # Get video file hash based on modification time and size
    # (we don't hash the content because that would be slow for large videos)
    video_stats = os.stat(video_path)
    video_id = f"{video_path}:{video_stats.st_mtime}:{video_stats.st_size}"
    
    # Compute hash of combined inputs
    hash_input = f"{video_id}:{params_str}"
    return hashlib.md5(hash_input.encode()).hexdigest()

def load_cache():
    """Load the process cache from disk."""
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
    """Save the process cache to disk."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def get_cached_preprocessing(video_path, match_start=None, match_end=None, set_pauses=None):
    """
    Check if a video has already been preprocessed with the same parameters.
    
    Args:
        video_path: Path to the input video file
        match_start: Match start time in seconds
        match_end: Match end time in seconds
        set_pauses: List of (start, end) tuples for set pauses
    
    Returns:
        dict or None: Cache entry for the preprocessed video, or None if not found
    """
    if not os.path.exists(video_path):
        return None
    
    # Create parameter dictionary
    params = {
        'process_type': 'preprocess',
        'match_start': match_start,
        'match_end': match_end,
        'set_pauses': set_pauses
    }
    
    process_id = generate_process_id(video_path, params)
    cache = load_cache()
    
    if process_id in cache:
        entry = cache[process_id]
        output_path = entry.get('output_path')
        
        if output_path and os.path.exists(output_path):
            print(f"Found cached preprocessed video: {output_path}")
            return entry
        else:
            # File was deleted, remove from cache
            del cache[process_id]
            save_cache(cache)
    
    return None

def cache_preprocessing_result(video_path, output_path, match_start=None, match_end=None, 
                               set_pauses=None, timestamp_mapper=None):
    """
    Add a preprocessed video to the cache.
    
    Args:
        video_path: Path to the input video file
        output_path: Path to the preprocessed video file
        match_start: Match start time in seconds
        match_end: Match end time in seconds
        set_pauses: List of (start, end) tuples for set pauses
        timestamp_mapper: Function that maps original timestamps to preprocessed timestamps
    """
    # Create parameter dictionary
    params = {
        'process_type': 'preprocess',
        'match_start': match_start,
        'match_end': match_end,
        'set_pauses': set_pauses
    }
    
    process_id = generate_process_id(video_path, params)
    cache = load_cache()
    
    # We can't directly store the timestamp_mapper function, so we store the parameters
    # that will allow us to recreate it
    cache[process_id] = {
        'input_path': video_path,
        'output_path': output_path,
        'match_start': match_start,
        'match_end': match_end,
        'set_pauses': set_pauses,
        'process_date': time.time()
    }
    
    save_cache(cache)
    print(f"Cached preprocessed video: {output_path}")

def get_cached_rally_detection(video_path, template_path, match_type, rally_params):
    """
    Check if rally detection has already been performed with the same parameters.
    
    Args:
        video_path: Path to the input video file
        template_path: Path to the template file
        match_type: Type of badminton match
        rally_params: Dictionary of rally detection parameters
    
    Returns:
        dict or None: Cache entry containing rally segments, or None if not found
    """
    if not os.path.exists(video_path):
        return None
    
    # Create parameter dictionary
    params = {
        'process_type': 'rally_detection',
        'template_path': template_path,
        'match_type': match_type,
        **rally_params
    }
    
    process_id = generate_process_id(video_path, params)
    cache = load_cache()
    
    if process_id in cache:
        return cache[process_id]
    
    return None

def cache_rally_detection_result(video_path, template_path, match_type, rally_params, rally_segments):
    """
    Add rally detection results to the cache.
    
    Args:
        video_path: Path to the input video file
        template_path: Path to the template file
        match_type: Type of badminton match
        rally_params: Dictionary of rally detection parameters
        rally_segments: List of (start, end) tuples for detected rallies
    """
    # Create parameter dictionary
    params = {
        'process_type': 'rally_detection',
        'template_path': template_path,
        'match_type': match_type,
        **rally_params
    }
    
    process_id = generate_process_id(video_path, params)
    cache = load_cache()
    
    cache[process_id] = {
        'input_path': video_path,
        'template_path': template_path,
        'match_type': match_type,
        'rally_params': rally_params,
        'rally_segments': rally_segments,
        'process_date': time.time()
    }
    
    save_cache(cache)
    print(f"Cached rally detection results for {video_path}: {len(rally_segments)} rallies")

def clear_cache(older_than_days=None):
    """
    Clear the cache, optionally only removing entries older than a certain number of days.
    
    Args:
        older_than_days: If provided, only clear entries older than this many days
    """
    if older_than_days is None:
        # Clear entire cache
        save_cache({})
        return
    
    # Only clear old entries
    cache = load_cache()
    current_time = time.time()
    cutoff_time = current_time - (older_than_days * 24 * 60 * 60)
    
    new_cache = {
        k: v for k, v in cache.items()
        if 'process_date' not in v or v['process_date'] > cutoff_time
    }
    
    save_cache(new_cache)
    print(f"Cleared {len(cache) - len(new_cache)} cache entries older than {older_than_days} days") 