import os
import cv2
from moviepy.editor import VideoFileClip, concatenate_videoclips
from enhance import enhance_highlights

def compile_highlights(
    video_path, 
    output_path=os.path.join(os.path.dirname(__file__), "..", "data", "highlights.mp4"), 
    rally_segments=None,
    enhance_video=True,
    target_fps=60,
    speed_factor=1.05,
    color_enhancement=True,
    audio_filter=True
):
    """
    Compile rally segments into a highlights video with optional enhancements.
    
    Args:
        video_path: Path to the input video file
        output_path: Path to save the highlights video
        rally_segments: List of (start_time, end_time) tuples in seconds
        enhance_video: Whether to apply video enhancements
        target_fps: Target frame rate for interpolation
        speed_factor: Factor to speed up the video
        color_enhancement: Whether to enhance video colors
        audio_filter: Whether to apply low-pass filter to audio
    
    Returns:
        Path to the highlights video
    """
    if not rally_segments:
        raise ValueError("No rally segments provided.")

    # If enhancements are requested, use the new enhance_highlights function
    if enhance_video:
        print("Compiling highlights with enhancements...")
        return enhance_highlights(
            video_path, 
            output_path, 
            rally_segments,
            target_fps=target_fps,
            speed_factor=speed_factor,
            color_enhancement=color_enhancement,
            audio_filter=audio_filter
        )
    
    # Otherwise, use the original simple compilation method
    print("Compiling highlights without enhancements...")
    
    # Use moviepy to handle video with audio
    print("Loading video clip...")
    source_clip = VideoFileClip(video_path)
    
    # Extract subclips for each rally segment
    rally_clips = []
    for i, (start, end) in enumerate(rally_segments):
        print(f"Extracting rally {i+1}/{len(rally_segments)}: {start}s to {end}s")
        rally_clip = source_clip.subclip(start, end)
        rally_clips.append(rally_clip)
    
    # Concatenate all rally clips
    print("Concatenating rally clips...")
    final_clip = concatenate_videoclips(rally_clips)
    
    # Write output file with audio
    print(f"Writing output to {output_path}...")
    final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')
    
    # Clean up
    source_clip.close()
    for clip in rally_clips:
        clip.close()
    final_clip.close()
    
    return output_path