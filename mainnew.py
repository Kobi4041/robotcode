import cv2
import mediapipe as mp
from gestnew import count_fingers, detect_heart # וודא שייבאת את שניהם
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
# שינוי ל-2 ידיים מקסימום
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=2)
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
        # א. בדיקה ראשונה: האם יש "לב" (דורש שתי ידיים)
        if len(results.multi_hand_landmarks) == 2:
            if detect_heart(results):
                raw_cmd = "HEART"

        # ב. אם לא זוהה לב, מחפשים פקודה מיד ימין בלבד
        if raw_cmd == "NONE":
            for i, hand_lms in enumerate(results.multi_hand_landmarks):
                hand_label = results.multi_handedness[i].classification[0].label
                # מציירים את השלד לכל יד שנמצאה
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
                
                # רק יד ימין מפעילה פקודות רגילות
                if hand_label == "Right":
                    raw_cmd = count_fingers(hand_lms, "Right")

    # 2. עדכון הזיכרון
    if raw_cmd != "NONE":
        confirmed_cmd = raw_cmd

    # 3. ניהול סיום סיבוב 360 מעלות
    if is_turning_360:
        if current_time - turn_start_time > 4.35:
            robot.turn(0)
            robot.mark_time(0)
            is_turning_360 = False
            confirmed_cmd = "STAND"
            print("Finished 360 degree turn.")

    # 4. ביצוע פקודות ברובוט
    if robot and confirmed_cmd != last_final_cmd:
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
            elif confirmed_cmd == "HEART":
                print("Heart gesture detected! Robot is happy.")
                robot.action(10) # פעולת שמחה/ריקוד
            elif confirmed_cmd == "SPINNING":
                robot.pace('normal')
                robot.mark_time(20)
                robot.turn(93)
                turn_start_time = current_time
                is_turning_360 = True
            elif confirmed_cmd == "STOP":
                robot.move('x', 0)
                robot.turn(0)

            last_final_cmd = confirmed_cmd

    # תצוגה
    status_text = f"CMD: {confirmed_cmd}"
    if is_turning_360: status_text += " (TURNING...)"
    
    # צבע טקסט משתנה ללב (ורוד) כשהוא מזוהה
    color = (203, 192, 255) if confirmed_cmd == "HEART" else (0, 255, 0)
    
    cv2.putText(img, status_text, (20, 50), 1, 1.5, color, 2)
    cv2.imshow("XGO Dual Hand Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()

