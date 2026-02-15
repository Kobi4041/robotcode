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
        def reset(self): print("[SIM] RESET") # הוספנו את זה כדי למנוע את השגיאה
        def turn(self, speed): print(f"[SIM] TURN: {speed}")
        def move(self, dir, step): print(f"[SIM] MOVE: {dir} {step}")
        def translation(self, axis, val): print(f"[SIM] TRANS: {axis} {val}")
        def attitude(self, axis, val): print(f"[SIM] ATTITUDE: {axis} {val}")
    robot = XGO_Mock()

# --- משתני עזר למניעת כפילויות ---
confirmed_cmd = "STAND"
last_final_cmd = ""

cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

while cap.isOpened():
    success, img = cap.read()
    if not success: break
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    # ברירת מחדל בכל פריים
    # 1. זיהוי הפקודה הנוכחית
    raw_cmd = "NONE"
    
    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            if results.multi_handedness[i].classification[0].label == "Right":
                confirmed_cmd = count_fingers(hand_lms, "Right")
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
    # 2. עדכון הפקודה רק אם היא לא NONE
    # זה הלב של ה"זיכרון" - אם לא זיהינו כלום, confirmed_cmd נשאר מה שהיה
    if raw_cmd != "NONE":
        confirmed_cmd = raw_cmd

    # --- ביצוע פקודות ---
    if robot:
        if confirmed_cmd != last_final_cmd:
            # שלב 1: עצירה בטיחותית לפני כל שינוי מצב
            robot.stop() 
            
            # שלב 2: ביצוע הפקודה החדשה
            if confirmed_cmd == "FOLLOW":
                robot.move('x', 12)                

            elif confirmed_cmd == "STAND":
                robot.reset()
            elif confirmed_cmd == "REVERSE":
                robot.move('x', -12)
            elif confirmed_cmd == "SPINNING":
                robot.turn(120)
                
                
            elif confirmed_cmd == "SIT":
                robot.translation(['z', 'x'], [75, -20])
                robot.attitude('p', 15)
            
            elif confirmed_cmd == "HELLO":
                robot.action(13)
                # אחרי אקשן כדאי לחזור למצב המתנה
                

            
            elif confirmed_cmd == "STOP":
                # ב-STOP אנחנו לא רוצים Reset, רק לוודא עצירה מוחלטת
                robot.move('x', 0)

            # עדכון המצב האחרון
            last_final_cmd = confirmed_cmd


    # תצוגה
    cv2.putText(img, f"CMD: {confirmed_cmd}", (20, 50), 1, 1.5, (0, 255, 0), 2)
    cv2.imshow("XGO Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
