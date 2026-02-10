import math
import time

# --- משתני היסטוריה גלובליים ---
finger_history = []
wave_history = []
last_wave_time = 0

def detect_wave(hand_lms):
    global wave_history
    # שימוש בנקודה 8 (אצבע מורה) לזיהוי נפנוף - יותר רגישה מהשורש
    pos_x = hand_lms.landmark[8].x 
    wave_history.append(pos_x)
    
    if len(wave_history) > 15: wave_history.pop(0)
    if len(wave_history) < 15: return False
    
    # חישוב טווח התנועה
    diff = max(wave_history) - min(wave_history)
    
    # בדיקת "תנודתיות" - אנחנו סופרים כמה פעמים התנועה שינתה כיוון
    direction_changes = 0
    for i in range(1, len(wave_history) - 1):
        prev = wave_history[i-1]
        curr = wave_history[i]
        nxt = wave_history[i+1]
        if (curr > prev and curr > nxt) or (curr < prev and curr < nxt):
            direction_changes += 1
            
    # WAVE חזק: טווח תנועה מספיק ולפחות 2 שינויי כיוון (נפנוף אמיתי)
    return diff > 0.12 and direction_changes >= 2

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
    
    # 1. בדיקת מצב אצבעות בסיסי
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

    # 2. זיהוי WAVE מחוזק (שלום) - חייב להיות עם יד פתוחה יחסית
    if total >= 3:
        if detect_wave(hand_lms):
            return "WAVE"

    # 3. זיהוי COME (בוא) - פוזיציה חכמה
    wrist = hand_lms.landmark[0]
    middle_mcp = hand_lms.landmark[9]
    is_upright = middle_mcp.y < wrist.y 
    
    if hand_type == "Right" and is_upright:
        half_curled_count = 0
        for tip_idx in [8, 12, 16]:
            tip = hand_lms.landmark[tip_idx]
            pip = hand_lms.landmark[tip_idx-2]
            mcp = hand_lms.landmark[tip_idx-3]
            # בדיקת ה"אזור המת" של חצי קיפול
            if mcp.y > tip.y > pip.y or abs(tip.y - pip.y) < 0.04:
                half_curled_count += 1
        
        if half_curled_count >= 2:
            return "COME"

    # 4. מחוות דינמיות אחרות
    if hand_type == "Right":
        if fingers[1] == 1 and total <= 2: 
            if detect_circle(hand_lms): return "SPIN"

    # 5. מצבים סטטיים
    if total <= 1: return "SIT"
    if total >= 4: return "STAND"
    
    return "READY"

def get_combo_action(left_gesture, right_gesture):
    # עדיפות ראשונה למחוות תנועה בימין
    if right_gesture == "WAVE": return "HELLO"
    if right_gesture == "COME": return "FOLLOW"
    if right_gesture == "SPIN": return "SPINNING"
    
    # עדיפות שנייה למצבים סטטיים בשתי ידיים
    if left_gesture == "SIT" and right_gesture == "SIT": 
        return "LIE DOWN"
    if left_gesture == "STAND" and right_gesture == "STAND": 
        return "ATTENTION"
    
    return "READY"
