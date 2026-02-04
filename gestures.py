import math
import time

# --- משתני היסטוריה גלובליים ---
finger_history = []
come_here_history = []
wave_history = []  # הוספנו את זה כדי שלא תהיה שגיאת NameError

def detect_wave(hand_lms):
    global wave_history
    # שימוש בנקודה 0 (פרק כף היד) - הכי יציב לזיהוי תנועת גוף
    pos_x = hand_lms.landmark[0].x 
    wave_history.append(pos_x)
    if len(wave_history) > 12: wave_history.pop(0)
    if len(wave_history) < 12: return False
    
    # בדיקת טווח התנועה בציר X
    diff = max(wave_history) - min(wave_history)
    return diff > 0.08  # רגישות גבוהה יותר (0.08 במקום 0.12)

def detect_circle(hand_lms):
    global finger_history
    pos = (hand_lms.landmark[8].x, hand_lms.landmark[8].y)
    finger_history.append(pos)
    if len(finger_history) > 15: finger_history.pop(0)
    if len(finger_history) < 15: return False
    
    min_x = min([p[0] for p in finger_history]); max_x = max([p[0] for p in finger_history])
    min_y = min([p[1] for p in finger_history]); max_y = max([p[1] for p in finger_history])
    return (max_x - min_x) > 0.1 and (max_y - min_y) > 0.1

def detect_come_here(total_fingers):
    global come_here_history
    come_here_history.append(total_fingers)
    if len(come_here_history) > 20: come_here_history.pop(0)
    return max(come_here_history) >= 4 and min(come_here_history) <= 1

def count_fingers(hand_lms, hand_type):
    if not hand_lms: return "None"
    
    # --- 1. חישוב כמות אצבעות פתוחות ---
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

    # --- 2. בדיקת מחוות דינמיות (חייב להיות לפני הסטטיות!) ---
    
    # בדיקת שלום (WAVE) - עובד אם היד פתוחה וזזה
    if total >= 3:
        if detect_wave(hand_lms): return "WAVE"

    # מחוות מיוחדות ליד ימין
    if hand_type == "Right":
        if detect_come_here(total): return "COME"
        if fingers[1] == 1 and total <= 2: 
            if detect_circle(hand_lms): return "SPIN"

    # --- 3. בדיקת מצבים סטטיים (רק אם לא זוהתה תנועה) ---
    if total <= 1: return "SIT"
    if total >= 4: return "STAND"
    
    return "READY"

def get_combo_action(left_gesture, right_gesture):
    # עדיפות 1: שלום (ביד אחת - ימין או שמאל)
    if right_gesture == "WAVE" or left_gesture == "WAVE":
        return "HELLO"

    # עדיפות 2: שתי ידיים (מצבים סטטיים)
    if left_gesture == "SIT" and right_gesture == "SIT": 
        return "LIE DOWN"
    if left_gesture == "STAND" and right_gesture == "STAND": 
        return "ATTENTION"
    
    # עדיפות 3: מחוות דינמיות בודדות
    if right_gesture == "COME": return "FOLLOW"
    if right_gesture == "SPIN": return "SPINNING"
    
    return "READY"
