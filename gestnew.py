import math
import time

# --- משתני היסטוריה גלובליים ---
finger_history = []
wave_history = []

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
    # החלשתי מעט את ה-diff ל-0.1 כדי שיהיה קל יותר לקלוט ב-Mock
    return diff > 0.1 and direction_changes >= 3

# משתנה גלובלי לצינון
last_spin_time = 0 

def detect_circle(hand_lms):
    global finger_history, last_spin_time
    
    current_time = time.time()
    # צינון של 2 שניות בין זיהוי לזיהוי כדי למנוע כפילויות
    if current_time - last_spin_time < 2.0:
        return False

    pos = (hand_lms.landmark[8].x, hand_lms.landmark[8].y)
    finger_history.append(pos)
    
    # הגדלנו את ההיסטוריה ל-60 פריימים כדי להספיק לקלוט שני סיבובים
    if len(finger_history) > 60: 
        finger_history.pop(0)
        
    if len(finger_history) < 60: 
        return False
    
    try:
        xs = [p[0] for p in finger_history]
        ys = [p[1] for p in finger_history]
        
        # 1. בדיקת טווח תנועה מינימלי (לוודא שזה לא סתם רעידות)
        diff_x = max(xs) - min(xs)
        diff_y = max(ys) - min(ys)
        
        if diff_x < 0.15 or diff_y < 0.15:
            return False

        # 2. ספירת שינויי כיוון (Direction Changes)
        # בעיגול אחד מלא יש 2 שינויי כיוון ב-X ו-2 ב-Y. 
        # לשני סיבובים נחפש לפחות 4 שינויים בכל ציר.
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

        # אם זיהינו מספיק שינויי כיוון בשני הצירים - זה שני סיבובים!
        if changes_x >= 4 and changes_y >= 4:
            print(f"--- 2 CIRCLES DETECTED! (X:{changes_x}, Y:{changes_y}) ---")
            finger_history = []  # איפוס
            last_spin_time = current_time 
            return True
            
    except Exception as e:
        print(f"Circle detect error: {e}")
        return False
        
    return False
def count_fingers(hand_lms, hand_type):
    if not hand_lms or hand_type != "Right": return "NONE"
    
    # 1. ספירת אצבעות (ציר Y)
    fingers_open = []   
    for tip in [8, 12, 16, 20]:
        fingers_open.append(1 if hand_lms.landmark[tip].y < hand_lms.landmark[tip-2].y else 0)
    
    total_others = sum(fingers_open)

    # 2. בדיקת אגודל
    thumb_open = 1 if hand_lms.landmark[4].x < hand_lms.landmark[3].x else 0

    # --- בדיקת מחוות דינמיות (קודם כל!) ---

    # בדיקת שלום (HELLO) - מתבצעת כשהיד פתוחה
    if total_others == 4 and thumb_open == 1:
        if detect_wave(hand_lms):
            return "HELLO"
        
        # 2. אם היד פתוחה אבל לא מנפנפת - זה FIVE_FINGERS (עמידה)
        return "FIVE_FINGERS"

    # בדיקת סיבוב (SPINNING) - מתבצעת כשרק האצבע המורה למעלה
   
    if total_others == 1 and fingers_open[0] == 1:
        try:
            if detect_circle(hand_lms):
                print("--- CIRCLE DETECTED! ---") # הדפסה לבדיקה בטרמינל
                return "SPINNING"
        except Exception as e:
            print(f"Circle Error: {e}")
        
        return "STAND" # אם לא זוהה עיגול, פשוט תחזיר STAND (ולא NONE)

    # --- בדיקת מחוות סטטיות (אם לא זוהתה תנועה דינמית) ---
    
    
    
    if total_others == 4 and thumb_open == 0:
        return "REVERSE"

    if total_others == 2: return "SIT"
    if total_others == 3: return "FOLLOW"
    if total_others == 0: return "STOP"
    if total_others == 1: return "STAND"
    
    return "NONE"