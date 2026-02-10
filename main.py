import cv2
import mediapipe as mp
from gestures import count_fingers, get_combo_action
import time
import sys

# --- חיבור לרובוט ---
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
    IS_SIM = False
except:
    IS_SIM = True
    class XGO_Mock:
        def action(self, cmd_id): print(f"[SIM] ACTION: {cmd_id}")
        def stop(self): print("[SIM] STOP")
        def move(self, direction, step): print(f"[SIM] MOVE: {direction} to {step}")
        def translation(self, axis, value): print(f"[SIM] TRANS: {axis} {value}")
    robot = XGO_Mock()

# --- הגדרות ---
REQUIRED_DURATION = 1.0  
gesture_start_time = 0
current_stable_candidate = "READY"
confirmed_cmd = "READY"
last_final_cmd = ""

cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=1) # רק יד אחת לביצועים טובים
mp_draw = mp.solutions.drawing_utils

try:
    while cap.isOpened():
        success, img = cap.read()
        if not success: break

        img = cv2.flip(img, 1)
        h, w, _ = img.shape
        results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        current_ui = {"Left": "None", "Right": "None"}

        if results.multi_hand_landmarks:
            for i, hand_lms in enumerate(results.multi_hand_landmarks):
                label = results.multi_handedness[i].classification[0].label
                gesture = count_fingers(hand_lms, label)
                current_ui[label] = gesture
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

        raw_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])

        # לוגיקת יציבות
        if raw_cmd == "READY":
            # אם אין יד או מצב READY, אנחנו לא עוצרים מיד את ה-FOLLOW כדי לאפשר "רעש" קל
            # אבל אם עבר זמן מה, אפשר לאפס
            current_stable_candidate = "READY"
            gesture_start_time = 0
            progress = 0
        elif raw_cmd == current_stable_candidate:
            if gesture_start_time == 0: gesture_start_time = time.time()
            elapsed = time.time() - gesture_start_time
            progress = min(elapsed / REQUIRED_DURATION, 1.0)
            if elapsed >= REQUIRED_DURATION: confirmed_cmd = raw_cmd
        else:
            current_stable_candidate = raw_cmd
            gesture_start_time = time.time()
            progress = 0

        # --- ביצוע פקודות (לוגיקת העצירה החדשה) ---
        if robot:
            # אם המשתמש עושה אגרוף (STOP), זה קוטע הכל
            if raw_cmd == "STOP" or confirmed_cmd == "STOP":
                robot.stop()
                robot.move('x', 0)  # איפוס מהירות הליכה
                robot.move('y', 0)
                robot.action(1)     # חזרה לעמידה בסיסית
                confirmed_cmd = "STOP" # מקבע את העצירה
                print("!!! EMERGENCY STOP !!!")

            elif confirmed_cmd == "FOLLOW":
                robot.move('x', 25) 
                
            elif confirmed_cmd != last_final_cmd:
                if confirmed_cmd == "SIT":
                    robot.stop()
                    robot.translation('z', -60) 
                    
                elif confirmed_cmd == "ATTENTION":
                    robot.stop()
                    robot.translation('z', 0)
                    robot.action(1) 
                    
                elif confirmed_cmd == "HELLO":
                    robot.stop()
                    robot.action(13)
                    
                elif confirmed_cmd == "READY":
                    # אם הפסקנו ללכת בגלל READY, מוודאים עצירה
                    if last_final_cmd == "FOLLOW":
                        robot.stop()
                        robot.move('x', 0)
                    robot.translation('z', 0)

        last_final_cmd = confirmed_cmd
        
        # תצוגה
        cv2.putText(img, f"CMD: {confirmed_cmd}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        if 0 < progress < 1:
            cv2.rectangle(img, (w//2-100, h-80), (w//2+100, h-70), (50,50,50), -1)
            cv2.rectangle(img, (w//2-100, h-80), (w//2-100+int(200*progress), h-70), (0,255,255), -1)
            
        cv2.imshow("XGO Safety Control", img)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

finally:
    # סגירה בטוחה
    if robot:
        robot.stop()
        robot.move('x', 0)
    cap.release()
    cv2.destroyAllWindows()
