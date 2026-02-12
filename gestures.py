import math
import time

# --- משתני היסטוריה גלובליים ---
finger_history = []
wave_history = []
come_history = []

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
    return diff > 0.15 and direction_changes >= 3

def detect_come_here(total_fingers):
    global come_history
    come_history.append(total_fingers)
    if len(come_history) > 10: come_history.pop(0) # קיצרנו ל-10 לזיהוי מהיר יותר
    if len(come_history) < 10: return False
    start_state = max(come_history[:5]) 
    end_state = min(come_history[-5:])  
    return start_state >= 4 and end_state <= 1

def detect_circle(hand_lms):
    global finger_history
    pos = (hand_lms.landmark[8].x, hand_lms.landmark[8].y)
    finger_history.append(pos)
    if len(finger_history) > 15: finger_history.pop(0)
    if len(finger_history) < 15: return False
    
    min_x = min([p[0] for p in finger_history]); max_x = max([p[0] for p in finger_history])
    min_y = min([p[1] for p in finger_history]); max_y = max([p[1] for p in finger_history])
    return (max_x - min_x) > 0.1 and (max_y - min_y) > 0.1

def count_fingers(hand_lms, hand_type):
    if not hand_lms or hand_type != "Right": return "None"
    
    # נקודות מפתח של האגודל
    thumb_tip = hand_lms.landmark[4]
    thumb_ip = hand_lms.landmark[3]
    thumb_mcp = hand_lms.landmark[2]
    
    # בדיקה אם שאר האצבעות סגורות (8, 12, 16, 20)
    fingers_open = []   
    for tip in [8, 12, 16, 20]:
        fingers_open.append(1 if hand_lms.landmark[tip].y < hand_lms.landmark[tip-2].y else 0)
    
    total_others = sum(fingers_open)

    # --- זיהוי אגודל למטה (REVERSE) ---
    # האגודל נמוך משמעותית מהמפרק שלו ושאר האצבעות סגורות
    if total_others == 0 and thumb_tip.y > thumb_mcp.y + 0.04:
        return "BACK"

    # --- זיהוי אגודל למעלה (ATTENTION) ---
    # האגודל גבוה משמעותית מהמפרק שלו ושאר האצבעות סגורות
    if total_others == 0 and thumb_tip.y < thumb_mcp.y - 0.04:
        return "THUMB_UP"

    # --- בדיקת מחוות דינמיות ---
    if total_others >= 3 and detect_wave(hand_lms):
        return "WAVE"

    if detect_come_here(total_others):
        return "COME"

    if fingers_open[0] == 1 and total_others == 1: 
        if detect_circle(hand_lms): return "SPIN"

    # --- מצבים סטטיים ---
    if total_others == 0: return "STOP"    # אגרוף סגור
    if total_others == 1: return "STAND"   # אצבע אחת (לא אגודל)
    if total_others == 2: return "SIT"     # שתי אצבעות
    
    return "READY"

def get_combo_action(left_gesture, right_gesture):
    if right_gesture == "WAVE": return "HELLO"
    if right_gesture == "COME": return "FOLLOW"
    if right_gesture == "SPIN": return "SPINNING"
    if right_gesture == "STOP": return "STOP"
    if right_gesture == "THUMB_UP": return "ATTENTION"
    if right_gesture == "STAND": return "ATTENTION"
    if right_gesture == "SIT": return "LIE DOWN"
    if right_gesture == "BACK": return "REVERSE"
    
    return "READY"
