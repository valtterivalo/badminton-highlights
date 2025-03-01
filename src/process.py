import os
import cv2
import numpy as np
import random
from collections import deque

def detect_rallies(video_path, template_path=os.path.join(os.path.dirname(__file__), "..", "templates", "gameplay_template_gray.jpg"), 
                  test=False, debug=False, match_type="men_singles", 
                  CAMERA_MOVEMENT_THRESHOLD=90000, LOW_MOVEMENT_THRESHOLD=2500, 
                  ALLOWED_LOW_MOVEMENT_FRAMES=60, MIN_CLOSEUP_MOVEMENT=30000,
                  MIN_RALLY_DURATION=8, MAX_MERGE_GAP=8):
    """
    Detect rally segments in a badminton match video.
    
    Args:
        video_path: Path to the input video file
        template_path: Path to the court template image
        test: Whether to analyze only a test segment
        debug: Whether to generate a debug visualization video
        match_type: Type of match for parameter optimization
        CAMERA_MOVEMENT_THRESHOLD: Threshold for camera stability detection
        LOW_MOVEMENT_THRESHOLD: Threshold for detecting low movement during service
        ALLOWED_LOW_MOVEMENT_FRAMES: Maximum frames of low movement allowed during service
        MIN_CLOSEUP_MOVEMENT: Minimum movement for replay/closeup detection
        MIN_RALLY_DURATION: Minimum duration for valid rally segments (seconds)
        MAX_MERGE_GAP: Maximum gap to merge adjacent segments (seconds)
        
    Returns:
        List of (start_time, end_time) tuples in seconds
    """
    template = cv2.imread(template_path, 0)
    if template is None:
        raise FileNotFoundError(f"Template image not found at {template_path}")

    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        raise FileNotFoundError("Could not open video.")

    fps = video.get(cv2.CAP_PROP_FPS)
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    total_duration = total_frames / fps

    # Test mode: Random 2-minute clip
    if test:
        clip_duration = 120
        if total_duration <= clip_duration:
            start_time = 0
            end_time = total_duration
        else:
            start_time = random.uniform(0, total_duration - clip_duration)
            end_time = start_time + clip_duration
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)
        video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        print(f"Test mode: Analyzing 2-minute clip from {start_time:.1f} to {end_time:.1f} seconds")
    else:
        start_time = 0
        end_time = total_duration
        start_frame = 0
        end_frame = total_frames

    # Log the parameters being used
    print(f"Rally detection parameters for {match_type}:")
    print(f"  CAMERA_MOVEMENT_THRESHOLD: {CAMERA_MOVEMENT_THRESHOLD}")
    print(f"  LOW_MOVEMENT_THRESHOLD: {LOW_MOVEMENT_THRESHOLD}")
    print(f"  ALLOWED_LOW_MOVEMENT_FRAMES: {ALLOWED_LOW_MOVEMENT_FRAMES}")
    print(f"  MIN_CLOSEUP_MOVEMENT: {MIN_CLOSEUP_MOVEMENT}")
    print(f"  MIN_RALLY_DURATION: {MIN_RALLY_DURATION}s")
    print(f"  MAX_MERGE_GAP: {MAX_MERGE_GAP}s")
    print(f"Using template: {template_path}")

    # Create debug video writer if needed
    debug_writer = None
    if debug:
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        debug_out_path = os.path.join(os.path.dirname(video_path), 'debug_output.avi')
        frame_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        debug_writer = cv2.VideoWriter(debug_out_path, fourcc, fps/2, (frame_width, frame_height))
        print(f"Debug video will be saved to {debug_out_path}")

    subtractor = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=40)
    rally_segments = []
    is_rally = False
    rally_start_time = 0
    frame_count = 0
    last_progress = -1
    
    # Improved parameters
    FRAME_SKIP = 2
    MIN_NON_RALLY_FRAMES = 45
    MIN_CANDIDATE_FRAMES = 4
    LOOKBACK_BUFFER_SIZE = int(3 * fps)
    
    # Camera stability parameters
    CAMERA_STABILITY_WINDOW_SIZE = 5    # Use a window to smooth camera stability detection
    camera_stability_window = deque([True] * CAMERA_STABILITY_WINDOW_SIZE, maxlen=CAMERA_STABILITY_WINDOW_SIZE)
    
    # Using a sliding window to smooth out detection
    rally_score_window = deque(maxlen=7)
    frame_buffer = deque(maxlen=LOOKBACK_BUFFER_SIZE)
    time_buffer = deque(maxlen=LOOKBACK_BUFFER_SIZE)
    
    prev_frame = None
    rally_candidate_frames = 0
    frames_without_rally = 0
    
    # Additional tracking for consistent detection
    camera_moving_frames = 0
    CONTINUOUS_CAMERA_MOVING_FRAMES = 8  # Must have this many consecutive moving frames to confirm camera is moving
    excessive_movement_frames = 0
    CONTINUOUS_EXCESSIVE_MOVEMENT_FRAMES = 5  # Must have this many excessive movement frames to confirm not a rally
    
    # Stores potential rally segments for post-processing
    potential_segments = []

    # Pre-detection state tracking for lookback
    pre_detection_scores = []
    
    # Track low movement during rally
    low_movement_frames = 0
    in_service_preparation = False
    
    while video.isOpened() and (test is False or video.get(cv2.CAP_PROP_POS_FRAMES) < end_frame):
        for _ in range(FRAME_SKIP - 1):
            ret = video.grab()
            if not ret or (test and video.get(cv2.CAP_PROP_POS_FRAMES) >= end_frame):
                break

        ret, frame = video.read()
        if not ret:
            break

        frame_count += FRAME_SKIP
        current_time = video.get(cv2.CAP_PROP_POS_MSEC) / 1000
        
        # Add to lookback buffer
        frame_buffer.append(frame.copy())
        time_buffer.append(current_time)
        
        progress = int((frame_count / (end_frame - start_frame if test else total_frames)) * 100)

        if progress % 5 == 0 and progress != last_progress:
            print(f"Progress: {progress}% ({current_time:.1f}/{end_time:.1f} seconds), Rallies detected: {len(rally_segments)}")
            last_progress = progress

        # Downsample frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        gray_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        
        # Template matching - using the template for court recognition
        small_template = cv2.resize(template, (0, 0), fx=0.5, fy=0.5)
        result = cv2.matchTemplate(gray_frame, small_template, cv2.TM_CCOEFF_NORMED)
        template_score = np.max(result)
        angle_match = template_score > 0.62
        
        # Movement detection with more accurate thresholds
        mask = subtractor.apply(small_frame)
        
        # Apply morphology operations to improve motion detection
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        movement_pixels = cv2.countNonZero(mask)
        low_movement = movement_pixels < LOW_MOVEMENT_THRESHOLD
        excessive_movement = movement_pixels >= MIN_CLOSEUP_MOVEMENT
        
        # Improved camera stability check
        # 1. First, get the raw camera stability value
        raw_camera_stable = True
        camera_movement_pixels = 0
        
        if prev_frame is not None:
            prev_gray = cv2.cvtColor(cv2.resize(prev_frame, (0, 0), fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray_frame, prev_gray)
            camera_movement_pixels = cv2.countNonZero(diff)
            raw_camera_stable = camera_movement_pixels <= CAMERA_MOVEMENT_THRESHOLD
        prev_frame = frame.copy()
        
        # 2. Update camera stability window
        camera_stability_window.append(raw_camera_stable)
        
        # 3. Determine camera stability using a majority vote from the window
        camera_stable = sum(camera_stability_window) > (len(camera_stability_window) / 2)
        
        # 4. Track consecutive camera movement
        if not raw_camera_stable:
            camera_moving_frames += 1
        else:
            camera_moving_frames = 0
            
        # 5. Track consecutive excessive movement
        if excessive_movement:
            excessive_movement_frames += 1
        else:
            excessive_movement_frames = 0
        
        # 6. Track low movement frames during a rally (for service prep detection)
        if is_rally and low_movement:
            low_movement_frames += FRAME_SKIP
            in_service_preparation = low_movement_frames <= ALLOWED_LOW_MOVEMENT_FRAMES
        else:
            if is_rally and low_movement_frames > 0:
                # Reset only if we detect significant movement again
                low_movement_frames = 0
                in_service_preparation = False
            
        # Persistent camera movement + excessive movement strongly indicates replays/closeups
        is_replay_or_closeup = (camera_moving_frames >= CONTINUOUS_CAMERA_MOVING_FRAMES and 
                               excessive_movement_frames >= CONTINUOUS_EXCESSIVE_MOVEMENT_FRAMES)
        
        # Calculate rally score with improved logic - primarily based on camera stability and template
        rally_score = 0
        if angle_match and not is_replay_or_closeup:
            # Primary factor is camera stability and template match
            template_weight = 0.8  # Increased weight for template match
            movement_weight = 0.2  # Significantly decreased movement weight
            
            # Compute movement score
            if low_movement and is_rally:
                # During service preparation, don't penalize for low movement
                movement_score = 0.8 if in_service_preparation else 0.4
            else:
                # Normal movement scoring
                movement_score = min(1.0, movement_pixels / 8000)
            
            rally_score = template_weight * template_score + movement_weight * movement_score
            
            # Apply camera stability penalty
            if not camera_stable:
                rally_score *= 0.9
        
        # Add to sliding window
        rally_score_window.append(rally_score)
        
        # If not in a rally, store pre-detection scores for lookback
        if not is_rally:
            pre_detection_scores.append(rally_score)
            if len(pre_detection_scores) > LOOKBACK_BUFFER_SIZE:
                pre_detection_scores.pop(0)
        
        # Average score from window for smoother transitions
        avg_score = sum(rally_score_window) / len(rally_score_window) if rally_score_window else 0
        
        # Primary determination based on camera stability and template match
        is_probable_rally = avg_score > 0.55 and not is_replay_or_closeup and camera_stable
        
        # Special case: we're in service preparation but camera is stable and template matches
        if is_rally and low_movement and in_service_preparation and camera_stable and angle_match:
            is_probable_rally = True
            
        # Add debug visualization
        if debug and debug_writer is not None:
            debug_frame = frame.copy()
            # Add visualization elements
            score_color = (0, 255, 0) if is_probable_rally else (0, 0, 255)
            cv2.putText(debug_frame, f"Score: {avg_score:.2f}", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, score_color, 2)
            cv2.putText(debug_frame, f"Template: {template_score:.2f}", (50, 90), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0) if angle_match else (0, 0, 255), 2)
            
            # Movement indicator with service preparation info
            movement_color = (0, 255, 0)  # Default green
            if low_movement:
                if in_service_preparation:
                    movement_color = (0, 255, 255)  # Yellow for service prep
                else:
                    movement_color = (0, 0, 255)  # Red for too low
            elif excessive_movement:
                movement_color = (0, 0, 255)  # Red for excessive
                
            cv2.putText(debug_frame, f"Movement: {movement_pixels}", (50, 130), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, movement_color, 2)
            
            cv2.putText(debug_frame, f"Camera: {'Stable' if camera_stable else 'Moving'} ({camera_movement_pixels})", (50, 170), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0) if camera_stable else (0, 0, 255), 2)
            
            # Add advanced states
            if in_service_preparation:
                state_text = "SERVICE PREPARATION"
                state_color = (0, 255, 255)  # Yellow
            elif is_replay_or_closeup:
                state_text = "REPLAY/CLOSEUP" 
                state_color = (0, 0, 255)  # Red
            else:
                state_text = "NORMAL VIEW"
                state_color = (0, 255, 0)  # Green
                
            cv2.putText(debug_frame, state_text, (50, 210), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, state_color, 2)
            
            # Add rally state and service info
            if is_rally:
                if in_service_preparation:
                    rally_info = f"RALLY (Service Prep: {low_movement_frames/fps:.1f}s)"
                else:
                    rally_info = "RALLY"
            else:
                rally_info = "CANDIDATE" if rally_candidate_frames > 0 else "NO RALLY"
                
            cv2.putText(debug_frame, rally_info, (50, 250), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
            # Add match type info
            cv2.putText(debug_frame, f"Match Type: {match_type}", (50, 290), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            debug_writer.write(debug_frame)
        
        # State machine with improved logic for rally detection
        if is_probable_rally or (is_rally and in_service_preparation and camera_stable and angle_match):
            if not is_rally:
                rally_candidate_frames += FRAME_SKIP
                if rally_candidate_frames >= MIN_CANDIDATE_FRAMES:
                    # Look back to find when the rally actually started
                    pre_rally_scores = pre_detection_scores.copy()
                    
                    # Find the longest continuous sequence of good scores going backwards
                    lookback_frames = 0
                    for i in range(len(pre_rally_scores)-1, -1, -1):
                        if pre_rally_scores[i] > 0.3:  # Lenient threshold for lookback
                            lookback_frames += 1
                        else:
                            # Allow for brief interruptions (up to 5 frames)
                            interruption_count = 0
                            for j in range(i, max(0, i-5), -1):
                                if pre_rally_scores[j] <= 0.3:
                                    interruption_count += 1
                            
                            if interruption_count < 3:  # Allow up to 2 bad frames
                                lookback_frames += interruption_count
                                continue
                            else:
                                break
                    
                    # Calculate how far back to look for rally start
                    lookback_time = min(3.0, lookback_frames * FRAME_SKIP / fps)
                    
                    # Determine rally start time with the lookback
                    if len(time_buffer) > 0 and lookback_time > 0:
                        # Find the closest timestamp in the buffer
                        target_time = current_time - lookback_time
                        closest_idx = 0
                        min_diff = float('inf')
                        
                        for i, t in enumerate(time_buffer):
                            diff = abs(t - target_time)
                            if diff < min_diff:
                                min_diff = diff
                                closest_idx = i
                        
                        if closest_idx < len(time_buffer):
                            rally_start_time = time_buffer[closest_idx]
                        else:
                            rally_start_time = current_time - (rally_candidate_frames / fps)
                    else:
                        rally_start_time = current_time - (rally_candidate_frames / fps)
                        
                    is_rally = True
                    frames_without_rally = 0
                    low_movement_frames = 0
                    in_service_preparation = False
                    print(f"Rally started at {rally_start_time:.1f} seconds (Score: {avg_score:.2f}, Progress: {progress}%, Lookback: {lookback_time:.1f}s)")
            else:
                frames_without_rally = 0  # Still in a rally
        else:
            if not is_rally:
                rally_candidate_frames = 0  # Reset candidate counter
            else:
                # Check if this is a replay/closeup which would immediately end a rally
                if is_replay_or_closeup:
                    frames_without_rally = MIN_NON_RALLY_FRAMES  # Force rally end
                elif low_movement and not in_service_preparation:
                    # Only increment non-rally frames if low movement AND we've exceeded service prep allowance
                    frames_without_rally += FRAME_SKIP
                elif not camera_stable:
                    # Camera instability is a strong signal for rally end
                    frames_without_rally += FRAME_SKIP * 2  # Count as double frames to end rally faster when camera moves
                else:
                    # Normal frame count
                    frames_without_rally += FRAME_SKIP
                
                # End rally after sustained non-rally frames
                if frames_without_rally >= MIN_NON_RALLY_FRAMES:
                    # Calculate end time with improved logic
                    if is_replay_or_closeup:
                        # For replays/closeups, end rally immediately at detection point
                        rally_end_time = current_time - (CONTINUOUS_CAMERA_MOVING_FRAMES * FRAME_SKIP / fps)
                    else:
                        # For normal endings, use 1/3 rule as before
                        rally_end_time = current_time - (frames_without_rally / fps / 3)
                    
                    rally_duration = rally_end_time - rally_start_time
                    
                    # Store as potential segment
                    potential_segments.append((rally_start_time, rally_end_time, rally_duration))
                    print(f"Rally ended at {rally_end_time:.1f} seconds, Duration: {rally_duration:.1f}s (Progress: {progress}%)")
                    is_rally = False
                    rally_candidate_frames = 0
                    low_movement_frames = 0
                    in_service_preparation = False

    # Handle the case where video ends during a rally
    if is_rally:
        rally_end_time = current_time
        rally_duration = rally_end_time - rally_start_time
        potential_segments.append((rally_start_time, rally_end_time, rally_duration))
        print(f"Video ended during rally, Duration: {rally_duration:.1f}s")

    # Clean up resources
    video.release()
    if debug_writer is not None:
        debug_writer.release()
    
    # Post-processing: merge nearby segments and filter by min duration
    
    if potential_segments:
        # Sort segments by start time
        potential_segments.sort(key=lambda x: x[0])
        
        # Merge nearby segments
        merged_segments = []
        current_segment = potential_segments[0]
        
        for next_segment in potential_segments[1:]:
            gap = next_segment[0] - current_segment[1]
            
            # If gap between segments is small, merge them
            if gap <= MAX_MERGE_GAP:
                # Check if the gap is very small (under 2 seconds)
                if gap < 2.0:
                    # Direct merge for very small gaps
                    current_segment = (current_segment[0], next_segment[1], next_segment[1] - current_segment[0])
                else:
                    # For larger gaps (2-8 seconds), we need to check if it might be a valid pause
                    # between points (like when players reset or a player retrieves the shuttle)
                    # Here we'll check the gap duration relative to the surrounding segments
                    
                    # If both segments are long enough to be valid rallies
                    if current_segment[2] > 5 and next_segment[2] > 5:
                        # If the gap is less than 40% of the average rally duration, merge
                        avg_duration = (current_segment[2] + next_segment[2]) / 2
                        if gap < (0.4 * avg_duration):
                            current_segment = (current_segment[0], next_segment[1], next_segment[1] - current_segment[0])
                        else:
                            # This is likely a valid pause between points, don't merge
                            merged_segments.append(current_segment)
                            current_segment = next_segment
                    else:
                        # If either segment is short, more likely they should be merged
                        current_segment = (current_segment[0], next_segment[1], next_segment[1] - current_segment[0])
            else:
                merged_segments.append(current_segment)
                current_segment = next_segment
        
        merged_segments.append(current_segment)  # Add the last segment
        
        # Filter segments by minimum duration
        for start, end, duration in merged_segments:
            if duration >= MIN_RALLY_DURATION:
                rally_segments.append((start, end))
                print(f"Final rally segment: {start:.1f}-{end:.1f} ({duration:.1f}s)")
            else:
                print(f"Discarded short rally: {start:.1f}-{end:.1f} ({duration:.1f}s < {MIN_RALLY_DURATION}s)")
    
    print(f"Analysis complete: {len(rally_segments)} rallies detected after merging and filtering.")
    return rally_segments

if __name__ == "__main__":
    video_path = os.path.join(os.path.dirname(__file__), "..", "data", "input_video.mp4")
    segments = detect_rallies(video_path, test=True, debug=True)
    print("Detected rally segments (start, end) in seconds:", segments)