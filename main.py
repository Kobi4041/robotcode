import cv2
import mediapipe as mp
from gestures import count_fingers 
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
        def Turn(self, speed): print(f"[SIM] TURN: {speed} °/s")
        def move(self, dir, step): print(f"[SIM] MOVE: {dir} {step}")
        def translation(self, axis, val): print(f"[SIM] TRANS: {axis} {val}")
        def attitude(self, axis, val): print(f"[SIM] ATTITUDE: {axis} {val}")
        def mark_time(self, data): print(f"[SIM] MARK_TIME: {data}mm")
        def pace(self, mode): print(f"[SIM] PACE: {mode}")
    robot = XGO_Mock()

# --- משתני עזר למניעת כפילויות וניהול זמן ---
confirmed_cmd = "STAND"
last_final_cmd = ""
is_turning_360 = False
turn_start_time = 0

cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

while cap.isOpened():
    success, img = cap.read()
    if not success: break
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    current_time = time.time()
    raw_cmd = "NONE"
    
    # 1. זיהוי הפקודה מהמצלמה
    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            if results.multi_handedness[i].classification[0].label == "Right":
                raw_cmd = count_fingers(hand_lms, "Right")
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # 2. עדכון הזיכרון (רק אם זוהתה פקודה שאינה NONE)
    if raw_cmd != "NONE":
        confirmed_cmd = raw_cmd

    # 3. ניהול סיום סיבוב 360 מעלות (בדיקה בכל פריים)
    if is_turning_360:
        # אם עברו 4 שניות (90 מעלות לשנייה * 4 = 360)
        if current_time - turn_start_time > 4.35:
            robot.turn(0)
            robot.mark_time(0)
            is_turning_360 = False
            confirmed_cmd = "STAND" # מחזיר את המצב לעמידה בסוף הסיבוב
            print("Finished 360 degree turn.")

    # 4. ביצוע פקודות ברובוט
    if robot and confirmed_cmd != last_final_cmd:
        # עצירה בטיחותית (רק אם אנחנו לא באמצע סיבוב אוטונומי)
        if not is_turning_360:
            robot.stop() 
            
            if confirmed_cmd == "FOLLOW":
                robot.move('x', 12)                 

            elif confirmed_cmd == "STAND":
                robot.reset()

            elif confirmed_cmd == "REVERSE":
                robot.move('x', -12)

            elif confirmed_cmd == "SIT":
                robot.translation(['z', 'x'], [75, -35])
                robot.attitude('p', -15)

            elif confirmed_cmd == "HELLO":
                robot.action(13)

            elif confirmed_cmd == "SPINNING":
                print("Starting 360 degree turn...")
                robot.pace('normal')
                robot.mark_time(20) # מרים רגליים
                robot.turn(93)      # מהירות 90 מעלות לשנייה
                turn_start_time = current_time
                is_turning_360 = True
            
            elif confirmed_cmd == "STOP":
                robot.move('x', 0)
                

            last_final_cmd = confirmed_cmd

    # תצוגה
    status_text = f"CMD: {confirmed_cmd}"
    if is_turning_360: status_text += " (TURNING...)"
    
    cv2.putText(img, status_text, (20, 50), 1, 1.5, (0, 255, 0), 2)
    cv2.imshow("XGO Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()



