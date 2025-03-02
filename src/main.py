import os
import argparse
import time
from pathlib import Path
from download import download_video
from process import detect_rallies
from compile import compile_highlights
from upload import upload_to_youtube, get_authenticated_service, update_video_thumbnail
from preprocess import trim_match_video, parse_timestamp, parse_set_pauses, create_timestamp_mapper
from process_cache import (
    get_cached_preprocessing, cache_preprocessing_result,
    get_cached_rally_detection, cache_rally_detection_result
)
import json
import requests
import openai
import cv2
from datetime import datetime
from config import (
    OPENAI_API_KEY, 
    YOUTUBE_API_KEY, 
    OUTPUT_DIR, 
    YOUTUBE_UPLOAD_SETTINGS,
    get_rally_parameters
)
from template_manager import template_manager

def analyze_video_metadata(url, title, description):
    """
    Analyze video metadata using GPT-4o-mini to extract match information.
    
    Args:
        url: The YouTube video URL
        title: The video title
        description: The video description
        
    Returns:
        Dictionary with extracted metadata
    """
    # Set OpenAI API key
    openai.api_key = OPENAI_API_KEY
    
    if not openai.api_key:
        print("Warning: OpenAI API key not found. Using generic metadata.")
        return {
            "player1": "Unknown Player 1",
            "player2": "Unknown Player 2",
            "tournament": "Unknown Tournament",
            "round": "Unknown Round",
            "year": datetime.now().year
        }
    
    prompt = f"""
    Extract the following information from this badminton match video:
    - Player 1 full name
    - Player 2 full name
    - Tournament name
    - Round of tournament (e.g., Final, Semi-final, Quarter-final)
    - Year of the match
    
    Video Title: {title}
    Video Description: {description}
    Video URL: {url}
    
    Format your response as a JSON object with the following fields:
    {{
        "player1": "Full Name",
        "player2": "Full Name",
        "tournament": "Tournament Name",
        "round": "Round Name",
        "year": YYYY
    }}
    Only include the JSON object in your response, nothing else.
    """
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise analyzer of badminton match metadata."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        print(f"Error in metadata extraction: {e}")
        return {
            "player1": "Unknown Player 1",
            "player2": "Unknown Player 2",
            "tournament": "Unknown Tournament",
            "round": "Unknown Round",
            "year": datetime.now().year
        }

def get_video_info(url):
    """
    Get video title and description from YouTube API.
    """
    video_id = url.split("v=")[1].split("&")[0]
    api_key = YOUTUBE_API_KEY
    
    if not api_key:
        print("Warning: YouTube API key not found. Cannot retrieve video metadata.")
        return "Badminton Match", "Badminton match video"
    
    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={api_key}"
    response = requests.get(api_url)
    data = response.json()
    
    if 'items' in data and len(data['items']) > 0:
        snippet = data['items'][0]['snippet']
        return snippet['title'], snippet['description']
    
    return "Badminton Match", "Badminton match video"

def format_output_filename(metadata, output_dir):
    """Format the output filename based on metadata"""
    player1 = metadata["player1"].replace(" ", "_")
    player2 = metadata["player2"].replace(" ", "_")
    tournament = metadata["tournament"].replace(" ", "_")
    year = metadata["year"]
    
    filename = f"{player1}_vs_{player2}_{tournament}_{year}_highlights.mp4"
    return os.path.join(output_dir, filename)

def format_video_title(metadata):
    """Format the YouTube video title based on metadata"""
    return f"{metadata['player1']} vs {metadata['player2']} | {metadata['tournament']} {metadata['round']} {metadata['year']} | Highlights"

def format_video_description(metadata, original_url):
    """Format the YouTube video description based on metadata"""
    return f"""Badminton Highlights: {metadata['player1']} vs {metadata['player2']}
Tournament: {metadata['tournament']} {metadata['round']} {metadata['year']}

This video contains automatically generated highlights from the full match.
Full match: {original_url}

#badminton #highlights #{metadata['tournament'].replace(' ', '')} #{metadata['player1'].replace(' ', '')} #{metadata['player2'].replace(' ', '')}
"""

def extract_thumbnail(video_path, rally_segments, output_dir):
    """
    Extract a thumbnail from an exciting moment in the video.
    
    Args:
        video_path: Path to the video file
        rally_segments: List of rally segments (start_time, end_time)
        output_dir: Directory to save the thumbnail
        
    Returns:
        Path to the thumbnail or None if extraction failed
    """
    if not rally_segments:
        return None
    
    # Find the longest rally (potentially most exciting)
    longest_rally = max(rally_segments, key=lambda x: x[1] - x[0])
    rally_duration = longest_rally[1] - longest_rally[0]
    
    # Take thumbnail from around 1/3 into the longest rally
    thumbnail_time = longest_rally[0] + (rally_duration / 3)
    
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        return None
    
    # Seek to the thumbnail time
    video.set(cv2.CAP_PROP_POS_MSEC, thumbnail_time * 1000)
    ret, frame = video.read()
    video.release()
    
    if not ret:
        return None
    
    # Save the thumbnail
    thumbnail_path = os.path.join(output_dir, "thumbnail.jpg")
    cv2.imwrite(thumbnail_path, frame)
    return thumbnail_path

def preview_highlights(video_path):
    """
    Play the highlights video for preview before uploading
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error opening video file")
        return False
    
    print("\nPreviewing highlights video. Press 'q' to stop, 'c' to continue to upload.")
    print("Window must be in focus for keyboard input to register.\n")
    
    window_name = "Highlights Preview"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)
    
    continue_upload = False
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        cv2.imshow(window_name, frame)
        key = cv2.waitKey(25) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            continue_upload = True
            break
    
    cap.release()
    cv2.destroyAllWindows()
    return continue_upload

def main():
    parser = argparse.ArgumentParser(description="Badminton Highlights Generator")
    parser.add_argument("url", help="YouTube URL of the badminton match")
    parser.add_argument("--output", "-o", help="Output directory for generated files", 
                        default=str(OUTPUT_DIR))
    parser.add_argument("--upload", "-u", action="store_true", help="Upload to YouTube after processing")
    parser.add_argument("--preview", "-p", action="store_true", help="Preview highlights before uploading")
    parser.add_argument("--debug", "-d", action="store_true", help="Generate debug visualization")
    parser.add_argument("--match-type", "-m", choices=["men_singles", "women_singles", "men_doubles", "women_doubles", "mixed_doubles"],
                        default="men_singles", help="Type of badminton match")
    parser.add_argument("--extract-template", "-e", action="store_true", help="Extract a template from the video")
    parser.add_argument("--template-time", "-t", type=int, default=60, help="Time (in seconds) to extract template from")
    
    # Add new video enhancement options
    parser.add_argument("--no-enhance", action="store_true", help="Disable video enhancements")
    parser.add_argument("--target-fps", type=int, default=60, help="Target frame rate for interpolation (default: 60)")
    parser.add_argument("--speed-factor", type=float, default=1.05, help="Speed factor for rallies (default: 1.05)")
    parser.add_argument("--no-color-enhance", action="store_true", help="Disable color enhancement")
    parser.add_argument("--no-audio-filter", action="store_true", help="Disable audio low-pass filter")
    
    # Add new video preprocessing options
    parser.add_argument("--match-start", help="Timestamp when the match starts (format: mm:ss for times under one hour, hh.mm:ss for times over one hour, e.g., '9:50' or '1.14:23')")
    parser.add_argument("--match-end", help="Timestamp when the match ends (format: mm:ss for times under one hour, hh.mm:ss for times over one hour, e.g., '9:50' or '1.14:23')")
    parser.add_argument("--set-pauses", help="Comma-separated list of set pauses as 'start-end' timestamps (e.g., '9:50-12:40,1.14:23-1.16:23')")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary preprocessed files")
    
    # Add cache-related arguments
    parser.add_argument("--no-cache", action="store_true", help="Disable caching (force reprocessing)")
    parser.add_argument("--clear-cache", action="store_true", help="Clear the cache before processing")
    parser.add_argument("--clear-cache-days", type=int, help="Clear cache entries older than this many days")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Step 1: Download the video (with cache check)
    print(f"Checking/downloading video from {args.url}...")
    temp_video_path = str(output_dir / "temp_input.mp4")
    # download_video now checks the cache before downloading
    temp_video_path = download_video(args.url, temp_video_path)
    print(f"Video path: {temp_video_path}")
    
    # Step 2: Get video metadata and analyze with GPT-4o-mini
    print("Retrieving video metadata...")
    title, description = get_video_info(args.url)
    print(f"Video title: {title}")
    
    print("Analyzing match information...")
    metadata = analyze_video_metadata(args.url, title, description)
    print(f"Match information: {json.dumps(metadata, indent=2)}")
    
    # Handle cache clearing if requested
    if args.clear_cache:
        from process_cache import clear_cache
        clear_cache()
        print("Cache cleared.")
    elif args.clear_cache_days:
        from process_cache import clear_cache
        clear_cache(args.clear_cache_days)
    
    # New Step: Preprocess video to trim unwanted sections
    match_start = parse_timestamp(args.match_start) if args.match_start else None
    match_end = parse_timestamp(args.match_end) if args.match_end else None
    set_pauses = parse_set_pauses(args.set_pauses) if args.set_pauses else None
    
    # Initialize timestamp_mapper as identity function
    timestamp_mapper = lambda t: t
    
    if match_start is not None or match_end is not None or set_pauses is not None:
        print("Processing video trimming...")
        preprocessed_path = str(output_dir / "preprocessed_input.mp4")
        
        # Check cache for preprocessed video
        cached_preprocessing = None
        if not args.no_cache:
            cached_preprocessing = get_cached_preprocessing(
                temp_video_path, match_start, match_end, set_pauses
            )
        
        if cached_preprocessing:
            # Use cached preprocessing results
            processing_video_path = cached_preprocessing['output_path']
            print(f"Using cached preprocessed video: {processing_video_path}")
            
            # Recreate the timestamp mapper function
            original_start = cached_preprocessing.get('match_start')
            original_end = cached_preprocessing.get('match_end')
            original_pauses = cached_preprocessing.get('set_pauses')
            
            # Use the utility function to create the timestamp mapper
            timestamp_mapper = create_timestamp_mapper(original_start, original_end, original_pauses)
        else:
            # Process the video
            print("Preprocessing video to trim unwanted sections...")
            trimmed_video_path, timestamp_mapper = trim_match_video(
                temp_video_path,
                preprocessed_path,
                match_start=match_start,
                match_end=match_end,
                set_pauses=set_pauses
            )
            
            # Cache the result
            if not args.no_cache:
                cache_preprocessing_result(
                    temp_video_path, trimmed_video_path,
                    match_start, match_end, set_pauses
                )
            
            # Use the trimmed video for further processing
            processing_video_path = trimmed_video_path
            print(f"Using preprocessed video for analysis: {processing_video_path}")
    else:
        # No preprocessing needed
        processing_video_path = temp_video_path
        print("No preprocessing parameters specified, using original video")
    
    # Extract template if requested
    if args.extract_template:
        # If using a preprocessed video, adjust the template extraction time
        template_time = args.template_time
        if processing_video_path != temp_video_path and match_start is not None:
            template_time = timestamp_mapper(match_start + args.template_time)
            print(f"Adjusting template extraction time to {template_time}s in the trimmed video")
        
        print(f"Extracting template from video at {template_time} seconds...")
        template_manager.extract_template_from_video(processing_video_path, template_time)
        print("Template extraction complete. Continuing with normal processing.")
    
    # Get the appropriate template file
    template_path = template_manager.get_template_path()
    print(f"Using template file: {template_path}")
    
    # Setup rally detection parameters based on match type
    rally_params = get_rally_parameters(args.match_type)
    print(f"Using parameters for match type: {args.match_type}")
    
    # Step 3: Detect rally segments
    print("Detecting rally segments...")
    start_time = time.time()
    
    # Try to get cached rally detection results
    rally_segments = None
    if not args.no_cache:
        cached_rally_data = get_cached_rally_detection(
            processing_video_path, template_path, args.match_type, rally_params
        )
        if cached_rally_data:
            rally_segments = cached_rally_data.get('rally_segments')
            if rally_segments:
                print(f"Using cached rally detection results: {len(rally_segments)} rallies")
    
    # If no cached results, detect rallies
    if not rally_segments:
        rally_segments = detect_rallies(
            processing_video_path, 
            template_path=template_path,
            test=False, 
            debug=args.debug,
            match_type=args.match_type,
            **rally_params
        )
        
        # Cache the rally detection results
        if not args.no_cache:
            cache_rally_detection_result(
                processing_video_path, template_path,
                args.match_type, rally_params, rally_segments
            )
    
    process_time = time.time() - start_time
    print(f"Processing completed in {process_time:.2f} seconds. Detected {len(rally_segments)} rally segments.")
    
    if not rally_segments:
        print("No rally segments detected. Exiting.")
        return
    
    # Step 4: Compile the highlights video with enhancements
    output_filename = format_output_filename(metadata, args.output)
    print(f"Compiling highlights video to {output_filename}...")
    
    # Set up enhancement options
    enhance_video = not args.no_enhance
    color_enhancement = not args.no_color_enhance
    audio_filter = not args.no_audio_filter
    
    # Add information about enhancements
    if enhance_video:
        print(f"Applying video enhancements:")
        print(f"  - Frame interpolation: {args.target_fps} fps")
        print(f"  - Speed adjustment: {args.speed_factor:.2f}x")
        print(f"  - Color enhancement: {'Enabled' if color_enhancement else 'Disabled'}")
        print(f"  - Audio filter: {'Enabled' if audio_filter else 'Disabled'}")
    
    compile_highlights(
        processing_video_path, 
        output_filename, 
        rally_segments, 
        enhance_video=enhance_video,
        target_fps=args.target_fps,
        speed_factor=args.speed_factor,
        color_enhancement=color_enhancement,
        audio_filter=audio_filter
    )
    print("Highlights compilation complete.")
    
    # Extract a thumbnail from the longest rally
    thumbnail_path = None
    try:
        print("Extracting thumbnail...")
        thumbnail_path = extract_thumbnail(processing_video_path, rally_segments, args.output)
        if thumbnail_path:
            print(f"Thumbnail saved to {thumbnail_path}")
    except Exception as e:
        print(f"Error extracting thumbnail: {e}")
    
    # Step 5: Preview if requested
    if args.preview:
        print("Previewing highlights...")
        should_upload = preview_highlights(output_filename)
        if not should_upload:
            print("Upload cancelled after preview. Highlights video is saved at:")
            print(output_filename)
            return
    
    # Step 6: Upload to YouTube if requested
    if args.upload:
        print("Preparing to upload to YouTube...")
        title = format_video_title(metadata)
        description = format_video_description(metadata, args.url)
        
        print(f"Title: {title}")
        print(f"Description: {description}")
        
        confirm = input("Continue with upload? (y/n): ")
        if confirm.lower() != 'y':
            print("Upload cancelled. Highlights video is saved at:")
            print(output_filename)
            return
        
        try:
            print("Uploading to YouTube...")
            video_id = upload_to_youtube(
                output_filename, 
                title=title, 
                description=description,
                tags=[
                    "badminton", "highlights", 
                    metadata["tournament"].replace(" ", ""),
                    metadata["player1"].replace(" ", ""),
                    metadata["player2"].replace(" ", "")
                ],
                **YOUTUBE_UPLOAD_SETTINGS
            )
            
            if video_id:
                print(f"Upload complete! YouTube video ID: {video_id}")
                print(f"Video URL: https://www.youtube.com/watch?v={video_id}")
                
                # Set custom thumbnail if available
                if thumbnail_path:
                    try:
                        youtube = get_authenticated_service()
                        if update_video_thumbnail(youtube, video_id, thumbnail_path):
                            print("Custom thumbnail set successfully")
                    except Exception as e:
                        print(f"Error setting thumbnail: {e}")
            else:
                print("Upload failed.")
        except Exception as e:
            print(f"Error during upload: {e}")
            print("Highlights video is saved at:")
            print(output_filename)
    else:
        print("Skipping upload. Highlights video is saved at:")
        print(output_filename)
    
    # Cleanup
    if not args.keep_temp:
        # Remove temporary files
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        
        # Remove preprocessed file if created
        if processing_video_path != temp_video_path and os.path.exists(processing_video_path):
            os.remove(processing_video_path)
            
        print("Temporary files cleaned up.")
    else:
        print(f"Keeping temporary files as requested.")
        if processing_video_path != temp_video_path:
            print(f"Preprocessed video saved at: {processing_video_path}")

if __name__ == "__main__":
    main() 