import os
import cv2
from moviepy.editor import VideoFileClip, concatenate_videoclips

def compile_highlights(video_path, output_path=os.path.join(os.path.dirname(__file__), "..", "data", "highlights.mp4"), rally_segments=None):
    if not rally_segments:
        raise ValueError("No rally segments provided.")

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