import math
import time

# --- Global History Variables ---
# Used to track hand movement over time for dynamic gesture recognition
finger_history = []
wave_history = []
last_spin_time = 0 

def detect_wave(hand_lms):
    # Detects a 'Waving' motion by tracking the X-axis oscillation of the index finger tip
    global wave_history
    pos_x = hand_lms.landmark[8].x 
    wave_history.append(pos_x)
    
    # Keep history size consistent (buffer of 25 frames)
    if len(wave_history) > 25: 
        wave_history.pop(0)
    if len(wave_history) < 25: 
        return False
    
    # Calculate range of motion (horizontal spread)
    diff = max(wave_history) - min(wave_history)
    
    # Count frequency of direction changes to identify oscillation
    direction_changes = 0
    for i in range(2, len(wave_history) - 2):
        prev_avg = (wave_history[i-1] + wave_history[i-2]) / 2
        curr = wave_history[i]
        next_avg = (wave_history[i+1] + wave_history[i+2]) / 2
        
        # Detect local peaks or valleys (direction flips)
        if (curr > prev_avg and curr > next_avg) or (curr < prev_avg and curr < next_avg):
            direction_changes += 1  

    # Return True if movement is wide enough and has enough oscillations
    return diff > 0.1 and direction_changes >= 3

def detect_circle(hand_lms):
    # Detects a circular motion (Spinning) by tracking the index finger tip
    global finger_history, last_spin_time
    
    # Cooldown mechanism: prevent multiple triggers (2 seconds delay)
    current_time = time.time()
    if current_time - last_spin_time < 2.0:
        return False

    pos = (hand_lms.landmark[8].x, hand_lms.landmark[8].y)
    finger_history.append(pos)
    
    # Buffer size 60 frames to capture complete circular rotations
    if len(finger_history) > 60: 
        finger_history.pop(0)
    if len(finger_history) < 60: 
        return False
    
    try:
        xs = [p[0] for p in finger_history]
        ys = [p[1] for p in finger_history]
        
        # Range Check: Ensure the motion is large enough to be intentional
        diff_x = max(xs) - min(xs)
        diff_y = max(ys) - min(ys)
        
        if diff_x < 0.15 or diff_y < 0.15:
            return False

        # Peak Detection: Helper function to count direction changes on an axis
        def count_changes(series):
            changes = 0
            for i in range(2, len(series) - 2):
                prev_avg = (series[i-1] + series[i-2]) / 2
                curr = series[i]
                next_avg = (series[i+1] + series[i+2]) / 2
                if (curr > prev_avg and curr > next_avg) or (curr < prev_avg and curr < next_avg):
                    changes += 1
            return changes

        changes_x = count_changes(xs)
        changes_y = count_changes(ys)

        # Identify circular motion: requires multiple peaks on both X and Y axes
        if changes_x >= 4 and changes_y >= 4:
            print(f"--- 2 CIRCLES DETECTED! (X:{changes_x}, Y:{changes_y}) ---")
            finger_history = []  # Clear history after detection
            last_spin_time = current_time 
            return True
            
    except Exception as e:
        # Error handling for coordinate processing
        print(f"Circle detection error: {e}")
        return False
        
    return False

def count_fingers(hand_lms, hand_type):
    # Main logic for classifying gestures into robot commands
    if not hand_lms or hand_type != "Right": 
        return "NONE"
    
    # --- 1. Detect state of the 4 main fingers (Index to Pinky) ---
    fingers_open = []   
    for tip in [8, 12, 16, 20]:
        # Finger is open if tip is higher (lower Y value) than the mid-joint
        fingers_open.append(1 if hand_lms.landmark[tip].y < hand_lms.landmark[tip-2].y else 0)
    
    total_others = sum(fingers_open)

    # --- 2. Detect Thumb state ---
    # Thumb is open if tip is further to the side than the base joint
    thumb_open = 1 if hand_lms.landmark[4].x < hand_lms.landmark[3].x else 0

    # --- 3. Check for Dynamic Gestures (High Priority) ---

    # HELLO: All fingers open + Waving motion
    if total_others == 4 and thumb_open == 1:
        if detect_wave(hand_lms):
            return "HELLO"
        return "FIVE_FINGERS"

    # SPINNING: Only Index finger open + Circular motion
    if total_others == 1 and fingers_open[0] == 1:
        if detect_circle(hand_lms):
            return "SPINNING"
        return "STAND"

    # --- 4. Static Gesture Mapping (Based on finger counts) ---

    # REVERSE: 4 fingers open but thumb is hidden
    if total_others == 4 and thumb_open == 0:
        return "REVERSE"

    # Map remaining finger combinations to specific robot states
    if total_others == 2: return "SIT"
    if total_others == 3: return "FOLLOW"
    if total_others == 0: return "STOP"
    if total_others == 1: return "STAND"
    
    return "NONE"
