import math
import time

# --- משתני היסטוריה גלובליים ---
finger_history = []
wave_history = []

def detect_wave(hand_lms):
    global wave_history
    # משתמשים במיקום ה-X של קצה האצבע המורה
    pos_x = hand_lms.landmark[8].x 
    wave_history.append(pos_x)
    
    # הגדלנו את ההיסטוריה ל-25 פריימים כדי לקלוט תנועה ארוכה יותר
    if len(wave_history) > 25: wave_history.pop(0)
    if len(wave_history) < 25: return False
    
    # 1. בדיקת טווח תנועה מינימלי (לוודא שהיד לא סתם רועדת במקום)
    diff = max(wave_history) - min(wave_history)
    
    # 2. ספירת שינויי כיוון (הלב של ה-Wave)
    direction_changes = 0
    # נשתמש בסינון רעשים קטן (threshold) כדי לא לספור כל רעידה כשינוי כיוון
    for i in range(2, len(wave_history) - 2):
        prev_avg = (wave_history[i-1] + wave_history[i-2]) / 2
        curr = wave_history[i]
        next_avg = (wave_history[i+1] + wave_history[i+2]) / 2
        
        if (curr > prev_avg and curr > next_avg) or (curr < prev_avg and curr < next_avg):
            direction_changes += 1
            
    # הגדלנו את הרף: חייב לפחות 3 שינויי כיוון וטווח תנועה ברור
    return diff > 0.15 and direction_changes >= 3

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

    # 2. זיהוי WAVE (שלום) - חייב יד פתוחה ותנועה של 3 נפנופים
    if total >= 4: # דורש לפחות 4 אצבעות פתוחות לנפנוף
        if detect_wave(hand_lms):
            return "WAVE"

    # 3. זיהוי COME (בוא) - פוזיציה חכמה (חצי קיפול)
    wrist = hand_lms.landmark[0]
    middle_mcp = hand_lms.landmark[9]
    is_upright = middle_mcp.y < wrist.y 
    
    if hand_type == "Right" and is_upright:
        half_curled_count = 0
        for tip_idx in [8, 12, 16]:
            tip = hand_lms.landmark[tip_idx]
            pip = hand_lms.landmark[tip_idx-2]
            mcp = hand_lms.landmark[tip_idx-3]
            if mcp.y > tip.y > pip.y or abs(tip.y - pip.y) < 0.04:
                half_curled_count += 1
        
        if half_curled_count >= 2:
            return "COME"

    # 4. מחוות אחרות
    if hand_type == "Right":
        if fingers[1] == 1 and total <= 2: 
            if detect_circle(hand_lms): return "SPIN"

    # 5. מצבים סטטיים
    if total <= 1: return "SIT"
    if total >= 4: return "STAND"
    
    return "READY"

def get_combo_action(left_gesture, right_gesture):
    # סדר עדיפויות מוחלט
    if right_gesture == "WAVE": return "HELLO"
    if right_gesture == "COME": return "FOLLOW"
    if right_gesture == "SPIN": return "SPINNING"
    
    if left_gesture == "SIT" and right_gesture == "SIT": 
        return "LIE DOWN"
    if left_gesture == "STAND" and right_gesture == "STAND": 
        return "ATTENTION"
    
    return "READY"
