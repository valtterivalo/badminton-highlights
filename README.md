# Badminton Highlights Generator

An automated system for generating badminton match highlights from full-length YouTube videos.

## Overview

This project automates the process of creating highlight videos from full badminton matches. It:

1. Downloads full-length badminton matches from YouTube
2. Analyzes match information using GPT-4o-mini
3. Detects rally segments using computer vision
4. Compiles a highlights video
5. Optionally uploads the highlights back to YouTube

## Features

- **Intelligent Rally Detection**: Detects rallies based on camera stability, player movement, and visual patterns
- **Service Preparation Handling**: Properly identifies service preparation periods to include the complete rally
- **Match Information Extraction**: Uses AI to extract players, tournament, and other metadata from video titles and descriptions
- **Video Enhancement**: Apply frame interpolation, color enhancement, and audio filtering
- **Video Preprocessing**: Trim out periods before/after matches and set pauses
- **Comprehensive Caching**: Cache downloaded videos, preprocessed files, and rally detection results for faster reruns
- **Debug Visualization**: Optional debug mode to visualize detection parameters
- **Preview Mode**: Preview highlights before uploading
- **YouTube Integration**: Upload highlights directly to YouTube with proper metadata

## Setup

### Prerequisites

- Python 3.8 or higher
- OpenCV
- FFmpeg installed on your system
- Google Cloud project with YouTube API enabled
- API keys for OpenAI and YouTube

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/badminton-highlights.git
   cd badminton-highlights
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up credentials:
   - Create a `credentials` directory
   - Download OAuth 2.0 Client ID from the Google Cloud Console and save as `credentials/client_secrets.json`
   - Set environment variables for API keys:
     ```
     # On Windows
     set OPENAI_API_KEY=your_api_key_here
     set YOUTUBE_API_KEY=your_api_key_here
     
     # On macOS/Linux
     export OPENAI_API_KEY=your_api_key_here
     export YOUTUBE_API_KEY=your_api_key_here
     ```

## Usage

### Basic Usage

Generate and save highlights without uploading:
```
python src/main.py "https://www.youtube.com/watch?v=video_id"
```

### Full Process with Upload

Process a video and upload the highlights to YouTube:
```
python src/main.py "https://www.youtube.com/watch?v=video_id" --upload
```

### Preview Mode

Preview the highlights before deciding whether to upload:
```
python src/main.py "https://www.youtube.com/watch?v=video_id" --preview --upload
```

### Debug Mode

Generate a debug visualization to see the rally detection in action:
```
python src/main.py "https://www.youtube.com/watch?v=video_id" --debug
```

### Specify Match Type

Adjust detection parameters based on match type:
```
python src/main.py "https://www.youtube.com/watch?v=video_id" --match-type men_doubles
```

### Video Preprocessing Options

You can preprocess the video before rally detection to trim out periods before/after the match or during set pauses:

```
python src/main.py "https://www.youtube.com/watch?v=video_id" --match-start "9:50" --match-end "1.14:23" --set-pauses "32:40-34:40,1.02:15-1.04:15"
```

#### Timestamp Format

Timestamps use the following format:
- For times under one hour: `mm:ss` (e.g., `9:50`, `12:53`)
- For times over one hour: `hh.mm:ss` (e.g., `1.14:23`, `2.05:10`)

Set pauses use the same timestamp format, separated by a dash (`-`) between start and end times, with multiple pauses separated by commas.

#### Preprocessing Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--match-start` | Timestamp when the match starts | `--match-start "9:50"` |
| `--match-end` | Timestamp when the match ends | `--match-end "1.14:23"` |
| `--set-pauses` | Comma-separated list of set pauses | `--set-pauses "32:40-34:40,1.02:15-1.04:15"` |
| `--keep-temp` | Keep temporary preprocessed files | `--keep-temp` |

This preprocessing trims out unwanted sections before any rally detection or highlights compilation, making the final video more focused on the actual match play.

### Caching Options

The system includes a comprehensive caching mechanism to avoid reprocessing videos that have already been processed. This saves significant time when rerunning the script with the same parameters.

| Parameter | Description |
|-----------|-------------|
| `--no-cache` | Disable caching (force reprocessing) |
| `--clear-cache` | Clear the entire cache before processing |
| `--clear-cache-days N` | Clear cache entries older than N days |

By default, the system will:
1. Check if the video has already been downloaded and use the cached version if available
2. Check if the video has already been preprocessed with the same parameters and use the cached version if available
3. Check if rally detection has already been performed with the same parameters and use the cached results if available

This saves significant time when working with the same videos multiple times.

### All Options

```
usage: main.py [-h] [--output OUTPUT] [--upload] [--preview] [--debug] 
              [--match-type {men_singles,women_singles,men_doubles,women_doubles,mixed_doubles}]
              [--extract-template] [--template-time TEMPLATE_TIME]
              [--no-enhance] [--target-fps TARGET_FPS] [--speed-factor SPEED_FACTOR]
              [--no-color-enhance] [--no-audio-filter]
              [--match-start MATCH_START] [--match-end MATCH_END] [--set-pauses SET_PAUSES]
              [--keep-temp] [--no-cache] [--clear-cache] [--clear-cache-days CLEAR_CACHE_DAYS]
              url

Badminton Highlights Generator

positional arguments:
  url                   YouTube URL of the badminton match

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output directory for generated files
  --upload, -u          Upload to YouTube after processing
  --preview, -p         Preview highlights before uploading
  --debug, -d           Generate debug visualization
  --match-type {men_singles,women_singles,men_doubles,women_doubles,mixed_doubles}, -m {men_singles,women_singles,men_doubles,women_doubles,mixed_doubles}
                        Type of badminton match
  --extract-template, -e
                        Extract a template from the video
  --template-time TEMPLATE_TIME, -t TEMPLATE_TIME
                        Time (in seconds) to extract template from
  --no-enhance          Disable video enhancements
  --target-fps TARGET_FPS
                        Target frame rate for interpolation (default: 60)
  --speed-factor SPEED_FACTOR
                        Speed factor for rallies (default: 1.05)
  --no-color-enhance    Disable color enhancement
  --no-audio-filter     Disable audio low-pass filter
  --match-start MATCH_START
                        Timestamp when the match starts (mm:ss or hh.mm:ss format)
  --match-end MATCH_END
                        Timestamp when the match ends (mm:ss or hh.mm:ss format)
  --set-pauses SET_PAUSES
                        Comma-separated list of set pauses as 'start-end' timestamps
  --keep-temp           Keep temporary preprocessed files
  --no-cache            Disable caching (force reprocessing)
  --clear-cache         Clear the cache before processing
  --clear-cache-days CLEAR_CACHE_DAYS
                        Clear cache entries older than this many days
```

## Setting Up YouTube API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the YouTube Data API v3
4. Create OAuth 2.0 credentials (Desktop app)
5. Download the client secrets JSON file
6. Save it to `credentials/client_secrets.json`

The first time you run an upload, the application will open a browser window asking you to authenticate with your YouTube account.

## Rally Detection Parameters

The rally detection algorithm uses several parameters that can be adjusted based on the specifics of the video:

| Parameter | Default | Description |
|-----------|---------|-------------|
| STABILITY_THRESHOLD | 0.8 | Minimum template matching score to consider camera stable |
| MOVEMENT_THRESHOLD | 3000 | Minimum pixel difference to detect significant movement |
| LOW_MOVEMENT_THRESHOLD | 2500 | Threshold for detecting low movement periods |
| MIN_RALLY_FRAMES | 45 | Minimum length of a valid rally (in frames) |
| MIN_SEGMENT_FRAMES | 15 | Minimum length for a potential rally segment |
| LOOKBACK_BUFFER | 30 | Number of frames to look back for detecting rally starts |
| SERVICE_PREP_MAX_FRAMES | 180 | Maximum frames to consider as service preparation (6 seconds at 30fps) |

## Video Enhancement Options

The system includes several video enhancement options to improve the quality of the output highlights:

| Parameter | Default | Description |
|-----------|---------|-------------|
| TARGET_FPS | 60 | Target frame rate after interpolation |
| SPEED_FACTOR | 1.05 | Speed multiplier for rallies (5% increase) |
| COLOR_ENHANCEMENT | Enabled | Subtle color enhancement for more vibrant video |
| AUDIO_FILTER | Enabled | Low-pass audio filter to reduce commentary while preserving game sounds |

These enhancements can be disabled individually using the corresponding command-line arguments.

## Project Structure

```
badminton-highlights/
├── credentials/                # API credentials (not in repo)
├── data/                       # Input videos and temporary files
├── output/                     # Output highlights videos
│   ├── video_cache.json        # Cache for downloaded videos
│   └── process_cache.json      # Cache for preprocessing and rally detection
├── templates/                  # Court templates for detection
├── src/                        # Source code
│   ├── download.py             # YouTube video download functionality
│   ├── process.py              # Rally detection algorithm
│   ├── preprocess.py           # Video preprocessing functionality
│   ├── compile.py              # Video compilation functionality
│   ├── enhance.py              # Video enhancement functionality
│   ├── upload.py               # YouTube upload functionality
│   ├── template_manager.py     # Court template management
│   ├── video_cache.py          # Video download caching
│   ├── process_cache.py        # Processing results caching
│   ├── config.py               # Configuration settings
│   └── main.py                 # Main script integrating all components
└── README.md                   # This file
```

## Extending the Project

### Adding New Match Types

To add support for a new match type, update the `main.py` script by adding it to the choices for the `--match-type` argument, and implement appropriate parameter adjustments in the rally detection algorithm.

### Custom Thumbnail Generation

The upload module includes functionality for setting custom thumbnails. To enable this:

1. Generate a thumbnail image (e.g., a key frame from an exciting rally)
2. Uncomment and modify the thumbnail code in `main.py` to use `update_video_thumbnail()`

### Advanced Caching

The caching system can be extended to support additional processing steps:

1. Edit `process_cache.py` to add new caching functions for your specific processing step
2. Use the `generate_process_id` function to create unique identifiers for your process
3. Store and retrieve results using the cache API

## Troubleshooting

### Authentication Issues

If you encounter authentication errors with the YouTube API:
- Delete the `token.pickle` file in the credentials directory
- Ensure your `client_secrets.json` file is valid and properly formatted
- Re-run the upload process to trigger a new authentication flow

### Detection Problems

If rally detection is not working as expected:
- Use the `--debug` flag to generate a visualization video
- Adjust thresholds in `process.py` based on the specific video characteristics
- Try specifying the correct match type with `--match-type`

### Audio Processing Issues

If you encounter audio processing errors:
- Make sure you have FFmpeg installed and accessible in your PATH
- Try disabling audio filtering with `--no-audio-filter`
- Check if the input video has valid audio tracks

### Caching Issues

If caching doesn't seem to work or causes unexpected behavior:
- Clear the cache using `--clear-cache` and try again
- Check the cache files in the output directory for corruption
- Verify the file paths in the cache entries match your actual files

## License

[MIT License](LICENSE)

## Acknowledgments

- This project uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube video downloading
- Rally detection is built on OpenCV
- Video enhancement uses MoviePy and FFmpeg
- Metadata extraction uses OpenAI's GPT models

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 