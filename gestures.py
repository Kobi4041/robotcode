import math
import time

# --- משתני היסטוריה גלובליים ---
finger_history = []
wave_history = []
come_history = []  # היסטוריה לזיהוי תנועת בוא

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
    """
    מזהה תנועת 'בוא' על ידי בדיקת מעבר מיד פתוחה ליד סגורה
    """
    global come_history
    come_history.append(total_fingers)
    
    if len(come_history) > 15: come_history.pop(0)
    if len(come_history) < 15: return False

    # מחלקים את ההיסטוריה לזמן התחלה וזמן סוף
    start_state = max(come_history[:7]) # המקסימום בחצי הראשון (מחפשים יד פתוחה >= 4)
    end_state = min(come_history[-7:])  # המינימום בחצי השני (מחפשים יד סגורה <= 1)
    
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
    if not hand_lms: return "None"
    
    # 1. חישוב אצבעות פתוחות
    fingers = []
    thumb_tip = hand_lms.landmark[4]
    pinky_base = hand_lms.landmark[17]
    dist = math.sqrt((thumb_tip.x - pinky_base.x)**2 + (thumb_tip.y - pinky_base.y)**2)
    fingers.append(1 if dist > 0.18 else 0)

    for tip in [8, 12, 16, 20]:
        fingers.append(1 if hand_lms.landmark[tip].y < hand_lms.landmark[tip-2].y else 0)
    
    total = fingers.count(1)

    # --- 2. מחוות דינמיות (סדר עדיפויות) ---

    # א. בדיקת WAVE (שלום)
    if total >= 4:
        if detect_wave(hand_lms):
            return "WAVE"

    # ב. בדיקת COME (בוא) - השדרוג החדש
    if hand_type == "Right":
        # בודק אם היד זקופה יחסית כדי למנוע זיהוי מהרצפה
        wrist = hand_lms.landmark[0]
        middle_mcp = hand_lms.landmark[9]
        if middle_mcp.y < wrist.y: # יד פונה למעלה
            if detect_come_here(total):
                return "COME"

    # ג. בדיקת SPIN (סיבוב)
    if hand_type == "Right" and fingers[1] == 1 and total <= 2: 
        if detect_circle(hand_lms): return "SPIN"

    # --- 3. מצבים סטטיים ---
    if total ==0: return "STOP"
    if total == 1: return "STAND"
    if total == 2: return "SIT"

    
    return "READY"

def get_combo_action(left_gesture, right_gesture):
    # סדר עדיפויות מוחלט לביצוע
    if right_gesture == "WAVE": return "HELLO"
    if right_gesture == "COME": return "FOLLOW"
    if right_gesture == "SPIN": return "SPINNING"
    return "READY"
