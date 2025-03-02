import os
import cv2
import numpy as np
from scipy.signal import butter, filtfilt
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip
from moviepy.audio.fx.all import audio_fadein, audio_fadeout
import subprocess

def enhance_video(
    input_path, 
    output_path=None, 
    target_fps=60, 
    speed_factor=1.05, 
    color_enhancement=True,
    audio_filter=True,
    audio_lowpass_cutoff=10000
):
    """
    Enhance a video by interpolating frames, adjusting speed, and enhancing colors.
    
    Args:
        input_path: Path to the input video file
        output_path: Path to save the enhanced video (defaults to input_path with _enhanced suffix)
        target_fps: Target frame rate for interpolation
        speed_factor: Factor to speed up the video
        color_enhancement: Whether to enhance video colors
        audio_filter: Whether to apply low-pass filter to audio
        audio_lowpass_cutoff: Cutoff frequency for low-pass filter in Hz
    
    Returns:
        Path to the enhanced video file
    """
    if output_path is None:
        base_path, ext = os.path.splitext(input_path)
        output_path = f"{base_path}_enhanced{ext}"
    
    print(f"Enhancing video: {input_path}")
    print(f"Output will be saved to: {output_path}")
    
    # Load video
    clip = VideoFileClip(input_path)
    original_fps = clip.fps
    
    print(f"Original video: {clip.duration:.2f}s, {original_fps} fps")
    
    # Apply enhancements
    enhanced_clip = clip
    
    # 1. Speed adjustment
    if speed_factor != 1.0:
        print(f"Speeding up video by factor of {speed_factor:.2f}")
        enhanced_clip = enhanced_clip.speedx(speed_factor)
    
    # 2. Color enhancement
    if color_enhancement:
        print("Enhancing colors")
        # Apply moderate color enhancement
        enhanced_clip = _enhance_colors(enhanced_clip)
    
    # 3. Audio low-pass filter
    if audio_filter and enhanced_clip.audio is not None:
        print(f"Applying audio low-pass filter with cutoff at {audio_lowpass_cutoff} Hz")
        enhanced_clip = _apply_audio_filter(enhanced_clip, cutoff=audio_lowpass_cutoff)
    
    # 4. Frame rate conversion using FFmpeg (after all other processing)
    print(f"Writing enhanced video (before frame rate conversion)")
    temp_output = output_path + ".temp.mp4"
    enhanced_clip.write_videofile(temp_output, codec='libx264', audio_codec='aac')
    enhanced_clip.close()
    
    # Apply frame rate interpolation if needed
    if target_fps > original_fps:
        print(f"Performing frame rate interpolation: {original_fps} → {target_fps} fps")
        interpolate_framerate(temp_output, output_path, target_fps)
        try:
            os.remove(temp_output)
        except:
            print(f"Warning: Could not remove temporary file {temp_output}")
    else:
        # Just rename the temp file
        os.rename(temp_output, output_path)
    
    print(f"Video enhancement complete: {output_path}")
    return output_path

def interpolate_framerate(input_path, output_path, target_fps):
    """
    Use FFmpeg with filter_complex to perform frame interpolation.
    
    This utilizes motion interpolation to create smoother video by generating 
    intermediate frames between existing ones.
    """
    # Check if ffmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Warning: FFmpeg not found or not working. Frame interpolation skipped.")
        os.rename(input_path, output_path)
        return
    
    # For interpolation, we'll use the minterpolate filter with a blend mode
    cmd = [
        'ffmpeg', '-i', input_path,
        '-filter_complex', f'minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
        '-c:a', 'copy',
        '-y', output_path
    ]
    
    try:
        print(f"Running FFmpeg interpolation...")
        subprocess.run(cmd, check=True)
        print(f"Frame interpolation completed successfully")
    except subprocess.SubprocessError as e:
        print(f"Error during frame interpolation: {e}")
        print("Falling back to simple frame rate conversion without interpolation")
        
        # Fallback to simpler frame rate conversion
        cmd = [
            'ffmpeg', '-i', input_path,
            '-r', str(target_fps),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-c:a', 'copy',
            '-y', output_path
        ]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.SubprocessError as e:
            print(f"Error during fallback conversion: {e}")
            # If all else fails, just use the original
            os.rename(input_path, output_path)

def _enhance_colors(clip, saturation=1.2, vibrance=1.1):
    """
    Enhance the colors of a video clip with subtle adjustments.
    
    Args:
        clip: MoviePy VideoClip
        saturation: Color saturation multiplier (1.0 = no change)
        vibrance: Smart saturation adjustment (primarily affects less saturated colors)
    
    Returns:
        Enhanced clip
    """
    def modify_frame(frame):
        # Convert to HSV for easier color manipulation
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
        
        # Split into channels
        h, s, v = cv2.split(hsv)
        
        # Apply vibrance (smart saturation that affects less saturated pixels more)
        # Calculate average saturation
        avg_sat = np.mean(s)
        
        # Apply vibrance: affects less saturated pixels more
        vibrance_mask = (255 - s) / 255.0
        s = s + (vibrance_mask * (vibrance - 1.0) * s)
        
        # Apply standard saturation adjustment
        s = s * saturation
        
        # Make sure saturation stays in valid range
        s = np.clip(s, 0, 255)
        
        # Boost brightness slightly
        v = v * 1.05
        v = np.clip(v, 0, 255)
        
        # Merge channels and convert back to RGB
        hsv = cv2.merge([h, s, v])
        rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
        
        return rgb
    
    # Apply the color enhancement to each frame
    return clip.fl_image(modify_frame)

def _apply_audio_filter(clip, cutoff=10000, order=4):
    """
    Apply a low-pass filter to the audio track to reduce commentary while preserving game sounds.
    
    Args:
        clip: MoviePy VideoClip with audio
        cutoff: Cut-off frequency in Hz
        order: Filter order
    
    Returns:
        Clip with filtered audio
    """
    if clip.audio is None:
        return clip
    
    # Get audio data
    audio = clip.audio
    fps = audio.fps
    
    def butter_lowpass(cutoff, fs, order=order):
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return b, a
    
    def process_audio(audio_array, *args):
        """
        Process audio data with a low-pass filter.
        
        Args:
            audio_array: The audio data array
            *args: Additional arguments passed by MoviePy (like t for time)
                  which we don't need but must accept
        
        Returns:
            Filtered audio array
        """
        # Make sure audio_array is an actual array, not a function
        if callable(audio_array):
            # If it's a function, we need to call it to get the actual data
            # This shouldn't normally happen, but let's handle it just in case
            print("Warning: audio_array is a function, not an array as expected")
            try:
                # Try calling it without arguments first
                audio_array = audio_array()
            except Exception as e:
                print(f"Error calling audio function: {e}")
                # Return the input to avoid breaking the pipeline
                return audio_array
        
        # If stereo, process each channel separately
        if len(audio_array.shape) > 1 and audio_array.shape[1] > 1:
            # Get filter coefficients
            b, a = butter_lowpass(cutoff, fps)
            
            # Apply filter to each channel
            filtered_channels = []
            for channel in range(audio_array.shape[1]):
                filtered_channel = filtfilt(b, a, audio_array[:, channel])
                filtered_channels.append(filtered_channel)
            
            # Combine channels
            filtered_audio = np.column_stack(filtered_channels)
        else:
            # Mono audio
            b, a = butter_lowpass(cutoff, fps)
            filtered_audio = filtfilt(b, a, audio_array)
        
        return filtered_audio
    
    # Apply the filter to the audio
    filtered_audio = audio.fl(process_audio)
    
    # Create a new clip with filtered audio
    return clip.set_audio(filtered_audio)

def enhance_highlights(
    input_path, 
    output_path, 
    rally_segments,
    target_fps=60,
    speed_factor=1.05,
    color_enhancement=True,
    audio_filter=True
):
    """
    Create an enhanced highlights video from rally segments.
    
    Args:
        input_path: Path to the source video
        output_path: Path to save the highlights video
        rally_segments: List of (start_time, end_time) tuples in seconds
        target_fps: Target frame rate for interpolation
        speed_factor: Factor to speed up the video
        color_enhancement: Whether to enhance video colors
        audio_filter: Whether to apply low-pass filter to audio
    
    Returns:
        Path to the enhanced highlights video
    """
    if not rally_segments:
        raise ValueError("No rally segments provided.")

    print("Loading source video...")
    source_clip = VideoFileClip(input_path)
    original_fps = source_clip.fps
    
    print(f"Extracting and enhancing {len(rally_segments)} rally clips...")
    rally_clips = []
    
    for i, (start, end) in enumerate(rally_segments):
        print(f"Processing rally {i+1}/{len(rally_segments)}: {start:.1f}s to {end:.1f}s")
        
        # Extract the rally clip
        rally_clip = source_clip.subclip(start, end)
        
        # Apply enhancements
        enhanced_clip = rally_clip
        
        # 1. Speed up
        if speed_factor != 1.0:
            enhanced_clip = enhanced_clip.speedx(speed_factor)
        
        # 2. Color enhancement
        if color_enhancement:
            enhanced_clip = _enhance_colors(enhanced_clip)
        
        # 3. Audio filtering
        if audio_filter and enhanced_clip.audio is not None:
            enhanced_clip = _apply_audio_filter(enhanced_clip)
        
        # 4. Add short fade in/out
        enhanced_clip = enhanced_clip.fadein(0.3).fadeout(0.3)
        if enhanced_clip.audio is not None:
            enhanced_clip = enhanced_clip.audio_fadein(0.3).audio_fadeout(0.3)
        
        rally_clips.append(enhanced_clip)
    
    # Concatenate all enhanced rally clips
    print("Concatenating enhanced rally clips...")
    final_clip = concatenate_videoclips(rally_clips)
    
    # Write intermediate result (before frame rate conversion)
    temp_output = output_path + ".temp.mp4"
    print(f"Writing intermediate output to {temp_output}...")
    final_clip.write_videofile(temp_output, codec='libx264', audio_codec='aac')
    
    # Clean up
    source_clip.close()
    for clip in rally_clips:
        clip.close()
    final_clip.close()
    
    # Apply frame rate interpolation if needed
    if target_fps > original_fps:
        print(f"Performing frame rate interpolation: {original_fps} → {target_fps} fps")
        interpolate_framerate(temp_output, output_path, target_fps)
        os.remove(temp_output)
    else:
        # Just rename the temp file
        os.rename(temp_output, output_path)
    
    print(f"Enhanced highlights saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhance a video or create enhanced highlights")
    parser.add_argument("input_path", help="Path to the input video file")
    parser.add_argument("--output_path", help="Path to save the output video (optional)")
    parser.add_argument("--target_fps", type=int, default=60, help="Target frame rate (default: 60)")
    parser.add_argument("--speed", type=float, default=1.05, help="Speed factor (default: 1.05)")
    parser.add_argument("--no_color", action="store_false", dest="color_enhancement", help="Disable color enhancement")
    parser.add_argument("--no_audio", action="store_false", dest="audio_filter", help="Disable audio filtering")
    
    args = parser.parse_args()
    
    output_path = args.output_path
    if output_path is None:
        base_path, ext = os.path.splitext(args.input_path)
        output_path = f"{base_path}_enhanced{ext}"
    
    enhance_video(
        args.input_path,
        output_path,
        target_fps=args.target_fps,
        speed_factor=args.speed,
        color_enhancement=args.color_enhancement,
        audio_filter=args.audio_filter
    ) 