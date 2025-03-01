import os
import cv2
import numpy as np
from pathlib import Path
import shutil
import time
from src.config import TEMPLATES_DIR

class TemplateManager:
    """Manages badminton court templates for different tournaments and match types."""
    
    def __init__(self):
        self.templates_dir = TEMPLATES_DIR
        self.templates = {}
        self.load_templates()
    
    def load_templates(self):
        """Load all templates from the templates directory."""
        if not self.templates_dir.exists():
            self.templates_dir.mkdir(exist_ok=True)
            print(f"Created templates directory at {self.templates_dir}")
            return
        
        for template_file in self.templates_dir.glob('*.jpg'):
            template_name = template_file.stem
            self.templates[template_name] = {
                'path': template_file,
                'template': cv2.imread(str(template_file), 0)  # Load as grayscale
            }
            
        print(f"Loaded {len(self.templates)} templates from {self.templates_dir}")
    
    def get_default_template(self):
        """Get the default template (gameplay_template_gray.jpg)."""
        default_path = self.templates_dir / 'gameplay_template_gray.jpg'
        if default_path.exists():
            return str(default_path)
        
        # If default doesn't exist, return the first available template or None
        if self.templates:
            return str(next(iter(self.templates.values()))['path'])
        return None
    
    def get_best_template(self, frame):
        """
        Find the best matching template for the given frame.
        
        Args:
            frame: OpenCV image frame to match against templates
            
        Returns:
            Path to the best matching template
        """
        if not self.templates:
            return self.get_default_template()
        
        # Convert frame to grayscale if needed
        if len(frame.shape) == 3:
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray_frame = frame
        
        # Find best matching template
        best_score = -1
        best_template = None
        
        for name, template_data in self.templates.items():
            template = template_data['template']
            
            # Resize template to match frame if needed
            h, w = template.shape
            scale = min(gray_frame.shape[0] / h, gray_frame.shape[1] / w, 1.0)
            if scale < 1.0:
                template = cv2.resize(template, None, fx=scale, fy=scale)
            
            # Perform template matching
            result = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
            score = np.max(result)
            
            if score > best_score:
                best_score = score
                best_template = template_data['path']
        
        return str(best_template) if best_template else self.get_default_template()
    
    def add_template_from_frame(self, frame, name=None):
        """
        Add a new template from a video frame.
        
        Args:
            frame: OpenCV image frame to use as template
            name: Optional name for the template, auto-generated if None
            
        Returns:
            Path to the saved template
        """
        # Convert to grayscale
        if len(frame.shape) == 3:
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray_frame = frame
        
        # Generate template name if not provided
        if name is None:
            timestamp = int(time.time())
            name = f"template_{timestamp}"
        
        # Save template
        template_path = self.templates_dir / f"{name}.jpg"
        cv2.imwrite(str(template_path), gray_frame)
        
        # Add to templates dictionary
        self.templates[name] = {
            'path': template_path,
            'template': gray_frame
        }
        
        print(f"Added new template: {template_path}")
        return str(template_path)
    
    def extract_template_from_video(self, video_path, timestamp=60, name=None):
        """
        Extract a template from a video at the specified timestamp.
        
        Args:
            video_path: Path to the video file
            timestamp: Time (in seconds) to extract the frame from
            name: Optional name for the template
            
        Returns:
            Path to the saved template or None if extraction failed
        """
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return None
        
        video = cv2.VideoCapture(video_path)
        if not video.isOpened():
            print(f"Could not open video: {video_path}")
            return None
        
        # Seek to timestamp
        fps = video.get(cv2.CAP_PROP_FPS)
        frame_number = int(timestamp * fps)
        video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        # Read frame
        ret, frame = video.read()
        video.release()
        
        if not ret:
            print(f"Could not read frame at timestamp {timestamp}s")
            return None
        
        # Generate template name if not provided
        if name is None:
            video_name = Path(video_path).stem
            name = f"{video_name}_template"
        
        # Add template
        return self.add_template_from_frame(frame, name)
    
    def get_template_for_match_type(self, match_type):
        """
        Get the appropriate template for the given match type.
        Currently using the same template for all match types.
        
        Args:
            match_type: Type of match (e.g., 'men_singles', 'women_doubles')
            
        Returns:
            Path to the template
        """
        # For now, just return the default template
        # In the future, this could be expanded to have specific templates per match type
        return self.get_default_template()

# Create global instance
template_manager = TemplateManager() 