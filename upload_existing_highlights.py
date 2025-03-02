#!/usr/bin/env python
"""
Script to upload an existing highlights video to YouTube.
"""

import os
import json
import argparse
from pathlib import Path
from upload import upload_to_youtube, get_authenticated_service, update_video_thumbnail
from config import YOUTUBE_UPLOAD_SETTINGS

def main():
    parser = argparse.ArgumentParser(description="Upload existing highlights to YouTube")
    parser.add_argument("--video", "-v", required=True, help="Path to the highlights video file")
    parser.add_argument("--thumbnail", "-t", help="Path to thumbnail image (optional)")
    parser.add_argument("--title", help="Video title (optional)")
    parser.add_argument("--description", help="Video description (optional)")
    
    args = parser.parse_args()
    
    # Check if the video file exists
    video_path = args.video
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return 1
        
    # Use the filename to suggest a title if not provided
    if not args.title:
        filename = os.path.basename(video_path)
        filename = os.path.splitext(filename)[0]
        suggested_title = filename.replace('_', ' ')
        title = input(f"Video title [default: {suggested_title}]: ") or suggested_title
    else:
        title = args.title
        
    # Ask for description if not provided
    if not args.description:
        default_description = f"Badminton highlights video.\n\n#badminton #highlights"
        print("Please enter a description (press Enter on an empty line to finish):")
        print(f"[default: {default_description}]")
        
        lines = []
        while True:
            line = input()
            if not line and not lines:  # Empty first line, use default
                description = default_description
                break
            if not line:  # Empty line after entering some text
                break
            lines.append(line)
            
        if lines:
            description = "\n".join(lines)
    else:
        description = args.description
        
    # Check for thumbnail
    thumbnail_path = args.thumbnail
    if thumbnail_path and not os.path.exists(thumbnail_path):
        print(f"Warning: Thumbnail file not found: {thumbnail_path}")
        thumbnail_path = None
    
    # Confirm upload
    print("\nReady to upload to YouTube:")
    print(f"Video: {video_path}")
    print(f"Title: {title}")
    print(f"Description: {description}")
    if thumbnail_path:
        print(f"Thumbnail: {thumbnail_path}")
        
    confirm = input("\nProceed with upload? (y/n): ")
    if confirm.lower() != 'y':
        print("Upload cancelled.")
        return 0
        
    # Upload the video
    try:
        print("Uploading to YouTube...")
        video_id = upload_to_youtube(
            video_path, 
            title=title, 
            description=description,
            tags=["badminton", "highlights"],
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
            return 1
    except Exception as e:
        print(f"Error during upload: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main()) 