import os
import cv2
from moviepy.editor import VideoFileClip
import numpy as np
from pathlib import Path

def trim_match_video(
    input_path, 
    output_path=None, 
    match_start=None, 
    match_end=None, 
    set_pauses=None
):
    """
    Preprocess a match video by trimming out periods before/after the match and set pauses.
    
    Args:
        input_path: Path to the input video file
        output_path: Path to save the trimmed video (defaults to input_path with _trimmed suffix)
        match_start: Timestamp (in seconds) where the match actually starts
        match_end: Timestamp (in seconds) where the match ends
        set_pauses: List of (start_time, end_time) tuples for set pauses to remove
        
    Returns:
        Tuple of (output_path, timestamp_mapping)
        timestamp_mapping is a function to convert original timestamps to new ones
    """
    if output_path is None:
        base_path, ext = os.path.splitext(input_path)
        output_path = f"{base_path}_trimmed{ext}"
    
    print(f"Preprocessing video: {input_path}")
    print(f"Trimmed output will be saved to: {output_path}")
    
    # Load video
    clip = VideoFileClip(input_path)
    original_duration = clip.duration
    
    # If no trimming needed, return the original video path
    if match_start is None and match_end is None and not set_pauses:
        print("No trimming parameters specified, using original video")
        return input_path, lambda t: t
    
    # Create segments to keep
    keep_segments = []
    
    # Determine match start and end times
    start_time = match_start if match_start is not None else 0
    end_time = match_end if match_end is not None else original_duration
    
    if start_time >= end_time:
        raise ValueError("Match start time must be before match end time")
    
    # If there are no set pauses, we just have one segment from start to end
    if not set_pauses:
        keep_segments.append((start_time, end_time))
    else:
        # Sort set pauses by start time
        sorted_pauses = sorted(set_pauses, key=lambda x: x[0])
        
        # Validate set pauses
        for pause_start, pause_end in sorted_pauses:
            if pause_start >= pause_end:
                raise ValueError(f"Invalid set pause: {pause_start}-{pause_end}. Start must be before end.")
        
        # Add segments between pauses
        current_time = start_time
        for pause_start, pause_end in sorted_pauses:
            if pause_start > current_time and pause_start < end_time:
                keep_segments.append((current_time, min(pause_start, end_time)))
            current_time = max(current_time, pause_end)
        
        # Add final segment if needed
        if current_time < end_time:
            keep_segments.append((current_time, end_time))
    
    if not keep_segments:
        raise ValueError("No valid segments to keep after applying trimming parameters")
    
    print(f"Keeping {len(keep_segments)} video segments:")
    for i, (seg_start, seg_end) in enumerate(keep_segments):
        print(f"  Segment {i+1}: {seg_start:.1f}s - {seg_end:.1f}s (duration: {seg_end - seg_start:.1f}s)")
    
    # Extract segments
    segments = []
    for seg_start, seg_end in keep_segments:
        segment = clip.subclip(seg_start, seg_end)
        segments.append(segment)
    
    # Concatenate segments
    from moviepy.editor import concatenate_videoclips
    final_clip = concatenate_videoclips(segments)
    
    # Write output file
    print(f"Writing trimmed video...")
    final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')
    
    # Clean up
    clip.close()
    for segment in segments:
        segment.close()
    final_clip.close()
    
    # Create timestamp mapping function
    def map_timestamp(original_time):
        """Convert an original timestamp to the corresponding time in the trimmed video."""
        if original_time < start_time or original_time > end_time:
            return None  # Time outside the match
        
        # Adjust for time removed from the beginning
        adjusted_time = original_time - start_time
        
        # Adjust for set pauses
        if set_pauses:
            for pause_start, pause_end in sorted_pauses:
                if pause_start <= original_time:
                    # Subtract the duration of any pauses that occurred before this timestamp
                    pause_duration = min(pause_end, original_time) - pause_start
                    adjusted_time -= max(0, pause_duration)
        
        return max(0, adjusted_time)
    
    return output_path, map_timestamp

def parse_timestamp(timestamp_str):
    """
    Parse a timestamp string into seconds.
    Accepts formats:
    - mm:ss (e.g., '9:50', '12:53') for times under one hour
    - hh.mm:ss (e.g., '1.14:23') for times over one hour
    
    Args:
        timestamp_str: String timestamp
        
    Returns:
        Time in seconds as float
    """
    if timestamp_str is None:
        return None
    
    # Check if the timestamp has a period (hh.mm:ss format)
    if '.' in timestamp_str:
        # Format is hh.mm:ss
        hours_str, rest = timestamp_str.split('.')
        if ':' not in rest:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}. Expected 'hh.mm:ss'")
        
        minutes_str, seconds_str = rest.split(':')
        return (float(hours_str) * 3600) + (float(minutes_str) * 60) + float(seconds_str)
    
    # Format is mm:ss
    if ':' in timestamp_str:
        parts = timestamp_str.split(':')
        if len(parts) != 2:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}. Expected 'mm:ss'")
        
        return (float(parts[0]) * 60) + float(parts[1])
    
    # If it's just a number, treat as seconds
    try:
        return float(timestamp_str)
    except ValueError:
        raise ValueError(f"Invalid timestamp format: {timestamp_str}")

def parse_set_pauses(pauses_str):
    """
    Parse a comma-separated list of set pause ranges.
    Each range should be in the format 'start-end' where start and end are timestamps.
    
    Args:
        pauses_str: String like '1:23:45-1:25:45,2:15:30-2:17:30'
        
    Returns:
        List of (start_time, end_time) tuples in seconds
    """
    if not pauses_str:
        return None
        
    pauses = []
    ranges = pauses_str.split(',')
    
    for range_str in ranges:
        if '-' not in range_str:
            raise ValueError(f"Invalid pause range format: {range_str}. Expected 'start-end'")
            
        start_str, end_str = range_str.split('-')
        start_time = parse_timestamp(start_str.strip())
        end_time = parse_timestamp(end_str.strip())
        
        pauses.append((start_time, end_time))
    
    return pauses

def create_timestamp_mapper(match_start, match_end, set_pauses):
    """
    Create a function that maps original video timestamps to preprocessed video timestamps.
    This is a helper function to ensure consistent timestamp mapping across the application.
    
    Args:
        match_start: Match start time in seconds
        match_end: Match end time in seconds
        set_pauses: List of (start, end) tuples for set pauses
        
    Returns:
        function: A function that maps original timestamps to preprocessed timestamps
    """
    offset = 0
    if match_start is not None:
        offset += match_start
    
    pause_offsets = []
    if set_pauses:
        for pause_start, pause_end in set_pauses:
            pause_duration = pause_end - pause_start
            pause_offsets.append((pause_start, pause_duration))
    
    def mapper(t):
        adjusted_t = t
        if match_start is not None and t < match_start:
            return 0  # Before match starts
        if match_end is not None and t > match_end:
            return match_end - offset  # After match ends
        
        adjusted_t -= offset
        
        for p_start, p_duration in sorted(pause_offsets):
            if t > p_start:
                adjusted_t -= p_duration
        
        return max(0, adjusted_t)
    
    return mapper 