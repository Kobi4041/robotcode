import cv2
import mediapipe as mp
import time
# ייבוא מהקובץ gestnew.py שסיפקת
from gestnew import count_fingers, detect_heart 

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
# חשוב: max_num_hands=2 כדי שנוכל לזהות את הלב
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=2)
mp_draw = mp.solutions.drawing_utils

while cap.isOpened():
    success, img = cap.read()
    if not success: break
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    current_time = time.time()
    raw_cmd = "NONE"
    
    # 1. זיהוי פקודות
    if results.multi_hand_landmarks:
        # א. בדיקה ללב (שתי ידיים)
        if len(results.multi_hand_landmarks) == 2:
            if detect_heart(results):
                raw_cmd = "HEART"

        # ב. אם אין לב, מחפשים פקודה מיד ימין
        if raw_cmd == "NONE":
            for i, hand_lms in enumerate(results.multi_hand_landmarks):
                label = results.multi_handedness[i].classification[0].label
                # ציור השלד לכל יד (כחול לימין, אדום לשמאל לצורך זיהוי)
                color = (255, 0, 0) if label == "Right" else (0, 0, 255)
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
                
                if label == "Right":
                    raw_cmd = count_fingers(hand_lms, "Right")

    # 2. עדכון הזיכרון
    if raw_cmd != "NONE":
        confirmed_cmd = raw_cmd

    # 3. ניהול סיבוב 360
    if is_turning_360:
        if current_time - turn_start_time > 4.35:
            robot.turn(0)
            is_turning_360 = False
            confirmed_cmd = "STAND"

    # 4. ביצוע ברובוט
    if confirmed_cmd != last_final_cmd:
        if not is_turning_360:
            robot.stop() 
            if confirmed_cmd == "HEART": robot.action(10) # ריקוד שמחה
            elif confirmed_cmd == "SIT": robot.action(1)   # או התנועה שהגדרת קודם
            elif confirmed_cmd == "STAND": robot.reset()
            elif confirmed_cmd == "HELLO": robot.action(13)
            elif confirmed_cmd == "STOP": robot.stop()
            elif confirmed_cmd == "SPINNING":
                robot.turn(93)
                turn_start_time = current_time
                is_turning_360 = True
            
            last_final_cmd = confirmed_cmd

    # תצוגה
    cv2.putText(img, f"CMD: {confirmed_cmd}", (20, 50), 1, 1.5, (0, 255, 0), 2)
    cv2.imshow("Robot Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
