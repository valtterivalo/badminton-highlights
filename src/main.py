import os
import argparse
import time
from pathlib import Path
from src.download import download_video
from src.process import detect_rallies
from src.compile import compile_highlights
from src.upload import upload_to_youtube, get_authenticated_service, update_video_thumbnail
import json
import requests
import openai
import cv2
from datetime import datetime
from src.config import (
    OPENAI_API_KEY, 
    YOUTUBE_API_KEY, 
    OUTPUT_DIR, 
    YOUTUBE_UPLOAD_SETTINGS,
    get_rally_parameters
)
from src.template_manager import template_manager

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
    
    # Extract template if requested
    if args.extract_template:
        print(f"Extracting template from video at {args.template_time} seconds...")
        template_path = template_manager.extract_template_from_video(
            temp_video_path, 
            timestamp=args.template_time
        )
        if template_path:
            print(f"Extracted template saved to {template_path}")
        else:
            print("Failed to extract template")
    
    # Get the appropriate template for the match type
    template_path = template_manager.get_template_for_match_type(args.match_type)
    
    # Get rally parameters for the match type
    rally_params = get_rally_parameters(args.match_type)
    
    # Step 3: Process the video to detect rallies
    print(f"Processing video to detect rallies (match type: {args.match_type})...")
    start_time = time.time()
    
    rally_segments = detect_rallies(
        temp_video_path, 
        template_path=template_path,
        test=False, 
        debug=args.debug,
        match_type=args.match_type,
        **rally_params
    )
    
    process_time = time.time() - start_time
    print(f"Processing completed in {process_time:.2f} seconds. Detected {len(rally_segments)} rally segments.")
    
    if not rally_segments:
        print("No rally segments detected. Exiting.")
        return
    
    # Step 4: Compile the highlights video
    output_filename = format_output_filename(metadata, args.output)
    print(f"Compiling highlights video to {output_filename}...")
    compile_highlights(temp_video_path, output_filename, rally_segments)
    print("Highlights compilation complete.")
    
    # Extract a thumbnail for the video
    thumbnail_path = extract_thumbnail(temp_video_path, rally_segments, args.output)
    if thumbnail_path:
        print(f"Extracted thumbnail saved to {thumbnail_path}")
    
    # Step 5: Preview highlights if requested
    if args.preview:
        print("Opening preview window...")
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
    if os.path.exists(temp_video_path):
        os.remove(temp_video_path)
        print("Temporary files cleaned up.")

if __name__ == "__main__":
    main() 