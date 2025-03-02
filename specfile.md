# Badminton Highlights Generator - Specification Document

## Project Overview

The Badminton Highlights Generator is an automated system designed to transform full-length badminton match videos into concise highlight videos by detecting and extracting rally segments while removing downtime. The project uses computer vision techniques to identify when active gameplay is occurring, with a primary focus on camera stability and court visibility as key indicators.

## Current State

### Rally Detection Algorithm

The core component of the system is the rally detection algorithm (`src/process.py`), which has been refined to effectively identify active gameplay segments in badminton match videos. Key features include:

- **Camera Stability Detection**: Using frame differencing to detect when the camera is stable (showing gameplay) versus moving (showing replays, closeups, etc.)
- **Court Template Matching**: Using template matching to identify when the camera is showing the court from the standard gameplay angle
- **Service Preparation Handling**: Special logic to maintain rally continuity during service preparation when players remain relatively still
- **Replay/Closeup Detection**: Identification of segments showing replays or player closeups that should be excluded
- **Post-processing**: Merging of nearby segments and filtering by minimum duration to create coherent rally clips
- **Debug Visualization**: Comprehensive visual debugging to aid in algorithm refinement

The algorithm has been tuned for men's singles matches but is designed to be adaptable to other match types (women's singles, doubles, etc.) with parameter adjustments.

### Project Structure

```
badminton-highlights/
├── src/
│   ├── process.py        # Core rally detection algorithm
│   ├── download.py       # YouTube video downloading functionality
│   ├── upload.py         # YouTube video uploading functionality
│   ├── compile.py        # Video compilation utilities
│   └── __init__.py
├── templates/
│   ├── gameplay_template_gray.jpg     # Template for court recognition
│   └── gameplay_template_original.jpg # Original template image
├── data/
│   └── input_video.mp4   # Test video file
└── specfile.md           # This specification document
```

## Future Development

### 1. End-to-End Pipeline

The next major development goal is creating an end-to-end pipeline that:

1. **Downloads** a full badminton match from YouTube
2. **Analyzes** the video metadata to extract match information (players, tournament, etc.)
3. **Processes** the video to detect rally segments
4. **Compiles** the rallies into a cohesive highlights video
5. **Uploads** the highlights back to YouTube with appropriate metadata

### 2. Match Information Extraction

Implement a system to extract match information using a large language model:
- Use GPT-4o-mini or similar for cost-effective video title/description analysis
- Extract player names, tournament, round, and other relevant metadata
- Format this information for use in generated highlight video titles and descriptions

### 3. Video Processing Enhancements

Planned improvements to the video processing pipeline:
- **Score Detection**: Implement OCR to detect when the score changes as an additional rally end indicator
- **Audio Processing**: Analyze audio levels to help identify exciting moments or rally endpoints (crowd reactions)
- **Parameter Auto-tuning**: Develop methods to automatically adjust detection parameters based on video characteristics
- **Support for Different Match Types**: Optimize parameters for women's singles, doubles, and mixed doubles matches
- **Frame Rate Interpolation**: Convert 30fps videos to 60fps for smoother playback
- **Rally Speed Adjustment**: Speed up rallies by approximately 5% to make them appear more dynamic
- **Color Enhancement**: Apply subtle color enhancement to make the video more vibrant
- **Audio Filter**: Apply a low-pass filter (above 10kHz) to reduce commentary while preserving game sounds
- **Rally Trimming Improvements**: 
  - Expand the lookback window to start rallies slightly earlier
  - Trim rally endings to be slightly shorter
  - Implement a maximum rally duration (90 seconds) to avoid extremely long segments

### 4. Cloud Deployment

Prepare the system for cloud deployment:
- Containerize the application for consistent deployment
- Set up a scalable architecture to process multiple videos concurrently
- Implement a NoSQL database to track processed videos and their metadata
- Create a simple API for triggering new highlight generation jobs
- Implement monitoring and logging for production reliability

### 5. Monetization Strategy

Develop a monetization approach:
- Initial testing on local machine to assess viewer interest and potential revenue
- YouTube channel growth strategies and optimization
- Potential for generating custom highlights based on user requests

## Technical Guidelines

### Rally Detection Parameters

Key parameters that may need adjustment for different match types:

| Parameter | Description | Current Value | Adjustment Notes |
|-----------|-------------|---------------|------------------|
| `CAMERA_MOVEMENT_THRESHOLD` | Threshold for camera movement detection | 90000 | Increase for shaky cameras |
| `LOW_MOVEMENT_THRESHOLD` | Threshold for detecting low movement | 2500 | May need adjustment for different playstyles |
| `ALLOWED_LOW_MOVEMENT_FRAMES` | Max frames of low movement allowed | 60 | Approximately 6 seconds at 10fps processing |
| `MIN_CLOSEUP_MOVEMENT` | Min movement for replay/closeup detection | 30000 | Adjust based on video style |
| `MIN_RALLY_DURATION` | Minimum duration for valid rally segments | 8 | Measured in seconds |
| `MAX_MERGE_GAP` | Maximum gap to merge adjacent segments | 8 | Measured in seconds |
| `MAX_RALLY_DURATION` | Maximum duration for valid rally segments | 90 | Measured in seconds |
| `LOOKBACK_BUFFER_SIZE` | Frames to look back for rally start detection | 3 * fps | Will be increased for better rally starts |

### Video Enhancement Parameters

New parameters for video quality enhancement:

| Parameter | Description | Target Value | Implementation Notes |
|-----------|-------------|--------------|----------------------|
| `FRAME_RATE_TARGET` | Target frame rate after interpolation | 60fps | Auto-detect source fps first |
| `SPEED_FACTOR` | Speed multiplier for rallies | 1.05 (5% increase) | Maintain audio pitch during speed change |
| `COLOR_SATURATION` | Color saturation adjustment | 1.1-1.2 (10-20% increase) | Apply subtle increase without overprocessing |
| `COLOR_VIBRANCE` | Color vibrance adjustment | 1.1-1.2 (10-20% increase) | Enhance colors without distortion |
| `AUDIO_LOWPASS_CUTOFF` | Frequency cutoff for low-pass filter | ~10kHz | Reduce commentary while preserving game sounds |

### Development Best Practices

1. **Code Style**:
   - Follow PEP 8 for Python code style
   - Use descriptive variable names and add comments for complex logic
   - Document parameter tuning decisions

2. **Testing**:
   - Test with diverse badminton videos (different tournaments, camera angles)
   - Generate debug videos to visualize algorithm performance
   - Compare automated results with manual rally identification

3. **Performance Considerations**:
   - Use frame skipping to improve processing speed
   - Implement multi-threading for parallel video processing
   - Profile memory usage for large video files

4. **Error Handling**:
   - Implement robust error handling for video processing
   - Create recovery mechanisms for network issues during download/upload
   - Log errors comprehensively for debugging

## API Specification (Planned)

### Rally Detection Function

```python
def detect_rallies(
    video_path: str,
    template_path: str = "templates/gameplay_template_gray.jpg",
    test: bool = False,
    debug: bool = False,
    match_type: str = "men_singles"
) -> List[Tuple[float, float]]:
    """
    Detect rally segments in a badminton match video.
    
    Args:
        video_path: Path to the input video file
        template_path: Path to the court template image
        test: Whether to analyze only a test segment
        debug: Whether to generate a debug visualization video
        match_type: Type of match for parameter optimization
        
    Returns:
        List of (start_time, end_time) tuples in seconds
    """
```

### Video Enhancement Function (Planned)

```python
def enhance_video(
    input_path: str,
    output_path: str,
    target_fps: int = 60,
    speed_factor: float = 1.05,
    color_enhancement: bool = True,
    audio_filter: bool = True
) -> None:
    """
    Enhance a video by interpolating frames, adjusting speed, and enhancing colors.
    
    Args:
        input_path: Path to the input video file
        output_path: Path to save the enhanced video
        target_fps: Target frame rate for interpolation
        speed_factor: Factor to speed up the video
        color_enhancement: Whether to enhance video colors
        audio_filter: Whether to apply low-pass filter to audio
    """
```

### End-to-End Processing Function (Planned)

```python
def process_match_video(
    video_url: str,
    output_path: str = None,
    auto_upload: bool = False,
    youtube_credentials: dict = None,
    match_type: str = None,
    enhance_video: bool = True
) -> dict:
    """
    Process a full badminton match from URL to highlights video.
    
    Args:
        video_url: YouTube URL of the match video
        output_path: Directory to save the output video
        auto_upload: Whether to upload the result to YouTube
        youtube_credentials: Credentials for YouTube API
        match_type: Type of match (auto-detected if None)
        enhance_video: Whether to apply video enhancements
        
    Returns:
        Dictionary with processing information and results
    """
```

## Roadmap

| Phase | Feature | Timeline | Status |
|-------|---------|----------|--------|
| 1 | Rally Detection Algorithm | Completed | ✅ |
| 2 | End-to-End Pipeline Development | 2-3 weeks | 🔄 |
| 3 | Match Information Extraction | 1-2 weeks | 📝 |
| 4 | Enhanced Video Processing | 3-4 weeks | 🔄 |
| 4.1 | Frame Rate Interpolation | 1 week | ✅ |
| 4.2 | Rally Speed Adjustment | 3-4 days | ✅ |
| 4.3 | Color Enhancement | 3-4 days | ✅ |
| 4.4 | Audio Processing | 3-4 days | ✅ |
| 4.5 | Rally Detection Refinements | 1 week | ✅ |
| 5 | Local Deployment & Testing | 2-3 weeks | 📝 |
| 6 | Cloud Deployment | 4-6 weeks | 📝 |

## Conclusion

The Badminton Highlights Generator has shown promising results in accurately detecting rally segments in professional badminton matches. With continued development, this project has the potential to automate the creation of high-quality highlight videos, providing value to badminton enthusiasts while exploring potential revenue generation through YouTube monetization.

Regular updates to this specification will be made as the project evolves and new features are implemented. 