import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Base directories
BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_DIR = BASE_DIR / 'credentials'
TEMPLATES_DIR = BASE_DIR / 'templates'
DATA_DIR = BASE_DIR / 'data'
OUTPUT_DIR = BASE_DIR / 'output'

# Create directories if they don't exist
CREDENTIALS_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE_PLAYLIST_ID = os.getenv('YOUTUBE_PLAYLIST_ID')

# File paths
YOUTUBE_CREDENTIALS_PATH = CREDENTIALS_DIR / 'client_secrets.json'
YOUTUBE_TOKEN_PATH = CREDENTIALS_DIR / 'token.pickle'

# Template paths based on match type
TEMPLATES = {
    'men_singles': TEMPLATES_DIR / 'gameplay_template_gray.jpg',
    'women_singles': TEMPLATES_DIR / 'gameplay_template_gray.jpg',  # Use the same for now
    'men_doubles': TEMPLATES_DIR / 'gameplay_template_gray.jpg',    # Use the same for now
    'women_doubles': TEMPLATES_DIR / 'gameplay_template_gray.jpg',  # Use the same for now
    'mixed_doubles': TEMPLATES_DIR / 'gameplay_template_gray.jpg',  # Use the same for now
}

# YouTube upload settings
YOUTUBE_UPLOAD_SETTINGS = {
    'category_id': '17',  # Sports
    'privacy_status': 'private',  # Start with private videos for safety
    'notify_subscribers': False,
    'language': 'en'
}

# Rally detection parameters by match type
RALLY_PARAMETERS = {
    'men_singles': {
        'CAMERA_MOVEMENT_THRESHOLD': 90000,
        'LOW_MOVEMENT_THRESHOLD': 2500,
        'ALLOWED_LOW_MOVEMENT_FRAMES': 60,
        'MIN_CLOSEUP_MOVEMENT': 30000,
        'MIN_RALLY_DURATION': 8,
        'MAX_MERGE_GAP': 8,
    },
    'women_singles': {
        'CAMERA_MOVEMENT_THRESHOLD': 90000,
        'LOW_MOVEMENT_THRESHOLD': 2300,  # Slightly lower for potentially lower intensity movements
        'ALLOWED_LOW_MOVEMENT_FRAMES': 60,
        'MIN_CLOSEUP_MOVEMENT': 28000,
        'MIN_RALLY_DURATION': 8,
        'MAX_MERGE_GAP': 8,
    },
    'men_doubles': {
        'CAMERA_MOVEMENT_THRESHOLD': 95000,  # Higher due to more court coverage
        'LOW_MOVEMENT_THRESHOLD': 3000,  # Higher due to more players
        'ALLOWED_LOW_MOVEMENT_FRAMES': 60,
        'MIN_CLOSEUP_MOVEMENT': 32000,
        'MIN_RALLY_DURATION': 7,  # Doubles rallies can be shorter
        'MAX_MERGE_GAP': 7,
    },
    'women_doubles': {
        'CAMERA_MOVEMENT_THRESHOLD': 95000,
        'LOW_MOVEMENT_THRESHOLD': 2800,
        'ALLOWED_LOW_MOVEMENT_FRAMES': 60,
        'MIN_CLOSEUP_MOVEMENT': 30000,
        'MIN_RALLY_DURATION': 7,
        'MAX_MERGE_GAP': 7,
    },
    'mixed_doubles': {
        'CAMERA_MOVEMENT_THRESHOLD': 95000,
        'LOW_MOVEMENT_THRESHOLD': 2900,
        'ALLOWED_LOW_MOVEMENT_FRAMES': 60,
        'MIN_CLOSEUP_MOVEMENT': 31000,
        'MIN_RALLY_DURATION': 7,
        'MAX_MERGE_GAP': 7,
    }
}

def save_credentials_sample():
    """Create a sample .env file if it doesn't exist"""
    env_sample = """# API Keys
OPENAI_API_KEY=your_openai_api_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here
YOUTUBE_PLAYLIST_ID=optional_youtube_playlist_id_for_uploads
"""
    sample_path = BASE_DIR / '.env.sample'
    if not sample_path.exists():
        with open(sample_path, 'w') as f:
            f.write(env_sample)
        print(f"Created sample environment file at {sample_path}")

def get_template_path(match_type='men_singles'):
    """Get the appropriate template path for the given match type"""
    return TEMPLATES.get(match_type, TEMPLATES['men_singles'])

def get_rally_parameters(match_type='men_singles'):
    """Get the rally detection parameters for the given match type"""
    return RALLY_PARAMETERS.get(match_type, RALLY_PARAMETERS['men_singles'])

# Create sample .env file
save_credentials_sample()

# Print warning if API keys are not set
if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not set in environment or .env file")
if not YOUTUBE_API_KEY:
    print("WARNING: YOUTUBE_API_KEY not set in environment or .env file") 