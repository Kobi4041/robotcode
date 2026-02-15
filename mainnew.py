import cv2
import mediapipe as mp
# שינוי הייבוא לפונקציית הלב החדשה
from gestnew import count_fingers, detect_heart_gesture 
import time

# --- אתחול רובוט ---
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
except:
    class XGO_Mock:
        def action(self, cmd_id): print(f"[SIM] ACTION: {cmd_id}")
        def stop(self): print("[SIM] STOP")
        def reset(self): print("[SIM] RESET")
        def turn(self, speed): print(f"[SIM] TURN: {speed} °/s")
        def move(self, dir, step): print(f"[SIM] MOVE: {dir} {step}")
        def translation(self, axis, val): print(f"[SIM] TRANS: {axis} {val}")
        def attitude(self, axis, val): print(f"[SIM] ATTITUDE: {axis} {val}")
        def mark_time(self, data): print(f"[SIM] MARK_TIME: {data}mm")
        def pace(self, mode): print(f"[SIM] PACE: {mode}")
    robot = XGO_Mock()

# --- משתני עזר ---
confirmed_cmd = "STAND"
last_final_cmd = ""
is_turning_360 = False
turn_start_time = 0

cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=2)
mp_draw = mp.solutions.drawing_utils

while cap.isOpened():
    success, img = cap.read()
    if not success: break
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    current_time = time.time()
    raw_cmd = "NONE"
    
    # משתנים לתצוגה ויזואלית
    right_hand_status = "Not Detected"
    left_hand_status = "Not Detected"
    heart_detected = False

    # 1. זיהוי פקודות וציור שלדים
    if results.multi_hand_landmarks:
        # א. בדיקה לזיהוי לב (שתי ידיים) - עדיפות עליונה
        if len(results.multi_hand_landmarks) >= 2:
            if detect_heart_gesture(results):
                raw_cmd = "HEART"
                heart_detected = True
        
        # ב. לולאה לזיהוי אצבעות בכל יד וציור
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            hand_label = results.multi_handedness[i].classification[0].label
            
            # קבלת הפקודה מהיד הנוכחית (ימין או שמאל)
            hand_cmd = count_fingers(hand_lms, hand_label)
            
            if hand_label == "Right":
                right_hand_status = hand_cmd
                color = (0, 255, 0) # ירוק לימין
                if not heart_detected:
                    raw_cmd = hand_cmd if hand_cmd != "NONE" else raw_cmd
            else: # Left
                left_hand_status = hand_cmd
                color = (0, 0, 255) # אדום לשמאל
                if not heart_detected and (raw_cmd == "NONE" or raw_cmd == "STAND"):
                    raw_cmd = hand_cmd if hand_cmd != "NONE" else raw_cmd
            
            # ציור השלד
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS,
                                 mp_draw.DrawingSpec(color=color, thickness=2, circle_radius=2),
                                 mp_draw.DrawingSpec(color=color, thickness=2))

    # 2. עדכון הזיכרון
    if raw_cmd != "NONE":
        confirmed_cmd = raw_cmd

    # 3. ניהול סיבוב 360 מעלות
    if is_turning_360:
        if current_time - turn_start_time > 4.35:
            robot.turn(0); robot.mark_time(0)
            is_turning_360 = False; confirmed_cmd = "STAND"

    # 4. ביצוע פקודות ברובוט
    if robot and confirmed_cmd != last_final_cmd:
        if not is_turning_360:
            robot.stop() 
            if confirmed_cmd == "FOLLOW": robot.move('x', 12)                 
            elif confirmed_cmd == "STAND": robot.reset()
            elif confirmed_cmd == "REVERSE": robot.move('x', -12)
            elif confirmed_cmd == "SIT":
                robot.translation(['z', 'x'], [75, -20]); robot.attitude('p', 15)
            elif confirmed_cmd == "HELLO": robot.action(13)
            
            # פקודה חדשה: לב (מפעיל אקשן שמחה)
            elif confirmed_cmd == "HEART": 
                print("Robot feels the love!")
                robot.action(10) 
                
            elif confirmed_cmd == "SPINNING":
                robot.turn(93); turn_start_time = current_time; is_turning_360 = True
            elif confirmed_cmd == "STOP": robot.move('x', 0); robot.turn(0)
            
            last_final_cmd = confirmed_cmd

    # --- ויזואליזציה על המסך ---
    # רקע שחור עליון
    cv2.rectangle(img, (0, 0), (640, 80), (0, 0, 0), -1)
    
    # סטטוס יד ימין (ירוק)
    cv2.putText(img, f"RIGHT: {right_hand_status}", (20, 30), 1, 1.2, (0, 255, 0), 2)
    # סטטוס יד שמאל (אדום)
    cv2.putText(img, f"LEFT: {left_hand_status}", (350, 30), 1, 1.2, (0, 0, 255), 2)
    
    # אינדיקטור לב (מרכז)
    # צבע ורוד/אדום כשיש לב, אפור כשאין
    heart_ui_color = (147, 20, 255) if heart_detected else (100, 100, 100)
    cv2.putText(img, f"HEART DETECTED: {heart_detected}", (160, 65), 1, 1.5, heart_ui_color, 2)

    # פקודה סופית בתחתית
    cv2.putText(img, f"ROBOT STATUS: {confirmed_cmd}", (20, 450), 1, 1.5, (255, 255, 255), 2)

    cv2.imshow("XGO Heart & Gesture Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
