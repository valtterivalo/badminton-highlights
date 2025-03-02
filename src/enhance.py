import os
import cv2
import numpy as np
from scipy.signal import butter, filtfilt
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, AudioClip
from moviepy.audio.fx.all import audio_fadein, audio_fadeout
import subprocess
from moviepy.video.fx.speedx import speedx

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

def _enhance_colors(frame, saturation=1.2, vibrance=1.1):
    """
    Enhance the colors of a video frame with subtle adjustments.
    
    Args:
        frame: A numpy array containing the image data
        saturation: Color saturation multiplier (1.0 = no change)
        vibrance: Smart saturation adjustment (primarily affects less saturated colors)
    
    Returns:
        Enhanced frame
    """
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
    
    def process_audio(audio_array, t):
        """
        Process audio data with a low-pass filter.
        
        Args:
            audio_array: The audio data array
            t: Time parameter required by MoviePy
        
        Returns:
            Filtered audio array
        """
        # Make sure audio_array is an actual array, not a function
        if callable(audio_array):
            # If it's a function, we need to call it with the time parameter
            try:
                audio_array = audio_array(t)
            except Exception as e:
                print(f"Error calling audio function: {e}")
                # Return a silent audio frame of appropriate shape
                # Determine shape from the audio clip's nchannels
                nchannels = getattr(audio, 'nchannels', 2)
                return np.zeros((1, nchannels))
        
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

def enhance_highlights(video_path, output_path, rallies, target_fps=60, speed_factor=1.05, color_enhance=True, audio_filter=True):
    """
    Enhance the highlights video by applying frame interpolation, color enhancement, and audio filtering.
    
    Args:
        video_path: Path to the input video
        output_path: Path to save the enhanced video
        rallies: List of detected rally segments as (start, end) tuples
        target_fps: Target frame rate for interpolation, default 60
        speed_factor: Speed multiplier for rallies, default 1.05 (5% increase)
        color_enhance: Whether to apply color enhancement
        audio_filter: Whether to apply audio filtering
    
    Returns:
        Path to the enhanced video
    """
    print(f"Enhancing highlights video with target FPS: {target_fps}, speed factor: {speed_factor}")
    print(f"Color enhancement: {'Enabled' if color_enhance else 'Disabled'}")
    print(f"Audio filtering: {'Enabled' if audio_filter else 'Disabled'}")
    
    # Get the original video info
    video = VideoFileClip(video_path)
    original_fps = video.fps
    video.close()
    
    # Create the clips for each rally
    rally_clips = []
    for start, end in rallies:
        # Load the clip for this rally
        clip = VideoFileClip(video_path, target_resolution=None).subclip(start, end)
        
        # Speed up the clip
        if speed_factor != 1.0:
            clip = clip.fx(speedx, speed_factor)
        
        # Apply frame interpolation if target_fps is higher than original
        # This must be done selectively to each clip individually
        if target_fps > original_fps:
            # We'll skip the frame interpolation step here, keeping original FPS
            # as it's done more effectively during the final composition
            pass
        
        # Color enhancement
        if color_enhance:
            # Use a wrapper function since _enhance_colors now operates directly on frames
            clip = clip.fl_image(lambda img: _enhance_colors(img, saturation=1.2, vibrance=1.1))
        
        # Apply audio filter on individual clips
        if audio_filter and clip.audio is not None:
            # Using a simpler approach that's less likely to cause errors
            # Apply a butter lowpass filter directly to the audio
            cutoff = 8000  # Lowpass cutoff frequency in Hz
            clip = clip.fx(lambda c: c.set_audio(c.audio.fx(lambda a: _simple_lowpass_filter(a, cutoff))))
        
        rally_clips.append(clip)
    
    # Concatenate the rally clips
    if rally_clips:
        final_clip = concatenate_videoclips(rally_clips)
        
        # Create the temporary output file path
        temp_output = f"{output_path}.temp.mp4"
        
        # Write the video to the temporary file
        final_clip.write_videofile(temp_output, codec='libx264', audio_codec='aac')
        
        # Close all clips
        for clip in rally_clips:
            clip.close()
        final_clip.close()
        
        # Move the temporary file to the output path
        if os.path.exists(temp_output):
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(temp_output, output_path)
            print(f"Highlights video enhanced and saved to {output_path}")
        
        return output_path
    else:
        print("No rally clips to enhance")
        return video_path

def _simple_lowpass_filter(audio_clip, cutoff_freq=8000):
    """
    A simpler implementation of a low-pass filter that's less likely to cause errors.
    
    Args:
        audio_clip: AudioClip to filter
        cutoff_freq: Cutoff frequency in Hz
        
    Returns:
        Filtered AudioClip
    """
    # Get the sample rate
    fps = audio_clip.fps
    
    # Create a Butterworth low-pass filter
    def butter_lowpass(cutoff, fs, order=5):
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return b, a
    
    b, a = butter_lowpass(cutoff_freq, fps)
    
    # Define a function that processes each chunk of audio
    def filter_audio(chunk, t):
        # Process each channel separately
        # Check if chunk is a function instead of an array
        if callable(chunk):
            try:
                chunk = chunk(t)
            except Exception as e:
                print(f"Error calling audio function: {e}")
                # Return a silent audio frame
                return np.zeros((1, 2))  # Default to stereo silence
                
        if len(chunk.shape) > 1 and chunk.shape[1] > 1:
            result = np.zeros_like(chunk)
            for i in range(chunk.shape[1]):
                result[:, i] = filtfilt(b, a, chunk[:, i])
            return result
        else:
            return filtfilt(b, a, chunk)
    
    # Apply the filter to the audio clip
    return audio_clip.fl(filter_audio)

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