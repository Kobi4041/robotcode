import math
import time

# היסטוריית תנועה לזיהוי מחוות דינמיות
finger_history = []
come_here_history = []
def detect_wave(hand_lms):
    global wave_history
    # שומרים את מיקום מרכז כף היד (ציר X)
    pos_x = hand_lms.landmark[9].x 
    wave_history.append(pos_x)
    if len(wave_history) > 15: wave_history.pop(0)
    if len(wave_history) < 15: return False
    
    # בודקים את הטווח שהיד עברה - אם היא זזה מספיק מצד לצד
    diff = max(wave_history) - min(wave_history)
    return diff > 0.12  # רגישות הנפנוף

def detect_circle(hand_lms):
    global finger_history
    pos = (hand_lms.landmark[8].x, hand_lms.landmark[8].y)
    finger_history.append(pos)
    if len(finger_history) > 15: finger_history.pop(0)
    if len(finger_history) < 15: return False
    
    min_x = min([p[0] for p in finger_history]); max_x = max([p[0] for p in finger_history])
    min_y = min([p[1] for p in finger_history]); max_y = max([p[1] for p in finger_history])
    # בודק אם הייתה תנועה רחבה מספיק בשני הצירים
    return (max_x - min_x) > 0.1 and (max_y - min_y) > 0.1

def detect_come_here(total_fingers):
    global come_here_history
    come_here_history.append(total_fingers)
    if len(come_here_history) > 20: come_here_history.pop(0)
    # מחפש שינוי מהיר בין יד פתוחה לסגורה (נפנוף "בוא")
    return max(come_here_history) >= 4 and min(come_here_history) <= 1

def count_fingers(hand_lms, hand_type):
    if not hand_lms: return "None"
    
    fingers = []
    # אגודל
    thumb_tip = hand_lms.landmark[4]
    pinky_base = hand_lms.landmark[17]
    dist = math.sqrt((thumb_tip.x - pinky_base.x)**2 + (thumb_tip.y - pinky_base.y)**2)
    fingers.append(1 if dist > 0.18 else 0)

    # 4 אצבעות
    for tip in [8, 12, 16, 20]:
        fingers.append(1 if hand_lms.landmark[tip].y < hand_lms.landmark[tip-2].y else 0)
    
    total = fingers.count(1)

    # זיהוי מחוות מיוחדות ליד ימין
    if hand_type == "Right":
        if detect_come_here(total): return "COME"
        if fingers[1] == 1 and total <= 2: # רק אצבע מורה מורמת
            if detect_circle(hand_lms): return "SPIN"

    if total <= 1: return "SIT"
    if total >= 4: return "STAND"
    return "READY"

def get_combo_action(left_gesture, right_gesture):
    # --- 1. עדיפות עליונה: שתי ידיים (מצבים סטטיים) ---
    if left_gesture == "SIT" and right_gesture == "SIT": 
        return "LIE DOWN"
    if left_gesture == "STAND" and right_gesture == "STAND": 
        return "ATTENTION"
    
    # --- 2. עדיפות שנייה: מחוות דינמיות ביד ימין       ---
    if right_gesture == "COME": return "FOLLOW"
    if right_gesture == "SPIN": return "SPINNING"
    if right_gesture == "WAVE": return "HELLO" 
    
    # --- 3. ברירת מחדל ---
    return "READY"
