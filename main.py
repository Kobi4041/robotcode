import cv2
import mediapipe as mp
from gestures import count_fingers, get_combo_action
import time
import sys

# --- אתחול רובוט ---
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
    IS_SIM = False
except:
    IS_SIM = True
    class XGO_Mock:
        def action(self, cmd_id): print(f"[SIM] ACTION: {cmd_id}")
        def stop(self): print("[SIM] STOP")
        def turn(self, speed): print(f"[SIM] TURN: {speed}")
        def move(self, dir, step): pass
        def translation(self, axis, val): pass
    robot = XGO_Mock()

# --- משתני שליטה ---
REQUIRED_DURATION = 0.8 # קיצרנו מעט לזיהוי מהיר יותר
gesture_start_time = 0
current_stable_candidate = "READY"
confirmed_cmd = "READY"
last_final_cmd = ""

# משתנה קריטי לסיבוב
spin_end_time = 0 

cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

try:
    while cap.isOpened():
        success, img = cap.read()
        if not success: break
        img = cv2.flip(img, 1)
        results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        current_ui = {"Left": "None", "Right": "None"}
        if results.multi_hand_landmarks:
            for i, hand_lms in enumerate(results.multi_hand_landmarks):
                label = results.multi_handedness[i].classification[0].label
                gesture = count_fingers(hand_lms, label)
                current_ui[label] = gesture
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

        raw_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])
        curr_time = time.time()

        # 1. ניהול טיימר הסיבוב (SPIN) - קודם לכל השאר
        if spin_end_time > 0:
            if curr_time < spin_end_time:
                # הרובוט כרגע בסיבוב, אנחנו לא מקבלים פקודות חדשות
                cv2.putText(img, "SPINNING...", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                cv2.imshow("XGO Control", img)
                cv2.waitKey(1)
                continue 
            else:
                # הזמן נגמר
                robot.turn(0)
                robot.stop()
                spin_end_time = 0
                confirmed_cmd = "READY"

        # 2. לוגיקת יציבות רגילה
        if raw_cmd == current_stable_candidate:
            if gesture_start_time == 0: gesture_start_time = curr_time
            if curr_time - gesture_start_time >= REQUIRED_DURATION:
                confirmed_cmd = raw_cmd
        else:
            current_stable_candidate = raw_cmd
            gesture_start_time = curr_time

        # 3. ביצוע פקודות
        if robot:
            # מקרה מיוחד: הפעלת סיבוב
            if confirmed_cmd == "SPINNING" and spin_end_time == 0:
                robot.stop()
                robot.turn(120)
                spin_end_time = curr_time + 4.2 # קובע סוף סיבוב לעוד 4 שניות
            
            # מקרה מיוחד: עצירת חירום (קוטע הכל)
            elif raw_cmd == "STOP":
                robot.stop()
                robot.turn(0)
                spin_end_time = 0
                confirmed_cmd = "STOP"

            elif confirmed_cmd == "FOLLOW":
                robot.move('x', 25)
            
            elif confirmed_cmd != last_final_cmd:
                if confirmed_cmd == "SIT":
                    robot.translation('z', -60)
                elif confirmed_cmd == "ATTENTION":
                    robot.translation('z', 0)
                    robot.action(1)
                elif confirmed_cmd == "HELLO":
                    robot.action(13)
                elif confirmed_cmd == "READY":
                    robot.stop() # עוצר הליכה/תנועה

        last_final_cmd = confirmed_cmd
        cv2.putText(img, f"CMD: {confirmed_cmd}", (20, 50), 1, 1, (0, 255, 0), 2)
        cv2.imshow("XGO Control", img)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

finally:
    if robot: robot.stop()
    cap.release()
    cv2.destroyAllWindows()
