import math
import time

# --- משתני היסטוריה גלובליים ---
finger_history = []
wave_history = []
last_spin_time = 0 

def detect_wave(hand_lms):
    global wave_history
    pos_x = hand_lms.landmark[8].x 
    wave_history.append(pos_x)
    if len(wave_history) > 25: wave_history.pop(0)
    if len(wave_history) < 25: return False
    diff = max(wave_history) - min(wave_history)
    direction_changes = 0
    for i in range(2, len(wave_history) - 2):
        prev_avg = (wave_history[i-1] + wave_history[i-2]) / 2
        curr = wave_history[i]
        next_avg = (wave_history[i+1] + wave_history[i+2]) / 2
        if (curr > prev_avg and curr > next_avg) or (curr < prev_avg and curr < next_avg):
            direction_changes += 1  
    return diff > 0.1 and direction_changes >= 3

def detect_circle(hand_lms):
    global finger_history, last_spin_time
    current_time = time.time()
    if current_time - last_spin_time < 2.0: return False
    pos = (hand_lms.landmark[8].x, hand_lms.landmark[8].y)
    finger_history.append(pos)
    if len(finger_history) > 60: finger_history.pop(0)
    if len(finger_history) < 60: return False
    try:
        xs = [p[0] for p in finger_history]; ys = [p[1] for p in finger_history]
        if (max(xs) - min(xs)) < 0.15 or (max(ys) - min(ys)) < 0.15: return False
        def count_changes(series):
            changes = 0
            for i in range(2, len(series) - 2):
                if (series[i] > (series[i-1]+series[i-2])/2 and series[i] > (series[i+1]+series[i+2])/2) or \
                   (series[i] < (series[i-1]+series[i-2])/2 and series[i] < (series[i+1]+series[i+2])/2):
                    changes += 1
            return changes
        if count_changes(xs) >= 4 and count_changes(ys) >= 4:
            finger_history = []; last_spin_time = current_time
            return True
    except: return False
    return False

def count_fingers(hand_lms, hand_type):
    if not hand_lms: return "NONE"
    
    fingers_open = []   
    for tip in [8, 12, 16, 20]:
        fingers_open.append(1 if hand_lms.landmark[tip].y < hand_lms.landmark[tip-2].y else 0)
    
    total_others = sum(fingers_open)
    if hand_type == "Right":
        thumb_open = 1 if hand_lms.landmark[4].x < hand_lms.landmark[3].x else 0
    else:
        thumb_open = 1 if hand_lms.landmark[4].x > hand_lms.landmark[3].x else 0

    # מחוות דינמיות (רק ליד ימין)
    if hand_type == "Right":
        if total_others == 4 and thumb_open == 1 and detect_wave(hand_lms): return "HELLO"
        if total_others == 1 and fingers_open[0] == 1 and detect_circle(hand_lms): return "CIRCLE"

    # מחוות סטטיות
    if total_others == 0 and thumb_open == 0: return "STOP"
    if total_others == 1 and thumb_open == 0: return "STAND"
    if total_others == 2 and thumb_open == 0: return "SIT"
    if total_others == 3 and thumb_open == 0: return "FOLLOW"
    if total_others == 4 and thumb_open == 0: return "REVERSE"
    if total_others == 4 and thumb_open == 1: return "FIVE"
    
    return "NONE"
