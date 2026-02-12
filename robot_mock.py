import cv2
import mediapipe as mp
from gestures import count_fingers, get_combo_action
import time
import sys

# --- אתחול רובוט ---
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
except:
    class XGO_Mock:
        def action(self, cmd_id): print(f"[SIM] ACTION: {cmd_id}")
        def stop(self): print("[SIM] STOP")
        def turn(self, speed): print(f"[SIM] TURN: {speed}")
        def move(self, dir, step): print(f"[SIM] MOVE: {dir} {step}")
        def translation(self, axis, val): print(f"[SIM] TRANS: {axis} {val}")
        def attitude(self, axis, val): print(f"[SIM] ATTITUDE: {axis} {val}")
    robot = XGO_Mock()

# --- משתני שליטה ---
REQUIRED_DURATION = 0.5 
gesture_start_time = 0
current_stable_candidate = "READY"
confirmed_cmd = "READY"
last_final_cmd = ""
block_until = 0  

# משתנים לזיהוי כפול של FOLLOW
come_here_count = 0
last_come_time = 0

cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

while cap.isOpened():
    success, img = cap.read()
    if not success: break
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    curr_time = time.time()
    
    current_ui_right = "None"
    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            label = results.multi_handedness[i].classification[0].label
            if label == "Right":
                current_ui_right = count_fingers(hand_lms, label)
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # 1. זיהוי פקודה גולמית
    raw_cmd = get_combo_action("None", current_ui_right)

    # 2. ניהול צינון ויציבות - כאן מתבצעת החסימה
    if curr_time < block_until:
        confirmed_cmd = "WAITING..."
        # איפוס משתני זיהוי כדי שלא "יזכור" מחוות שנעשו בזמן החסימה
        gesture_start_time = 0
        current_stable_candidate = "READY"
    else:
        if raw_cmd == current_stable_candidate:
            if gesture_start_time == 0: gesture_start_time = curr_time
            if curr_time - gesture_start_time >= REQUIRED_DURATION:
                
                # לוגיקה לזיהוי כפול של FOLLOW
                if raw_cmd == "FOLLOW":
                    if curr_time - last_come_time > 5.0:
                        come_here_count = 0
                    
                    if last_final_cmd != "FOLLOW" and confirmed_cmd != "FOLLOW":
                        come_here_count += 1
                        last_come_time = curr_time
                        print(f">>> GESTURE: COME HERE ({come_here_count}/2)")
                        
                        if come_here_count >= 2:
                            confirmed_cmd = "FOLLOW"
                            come_here_count = 0
                        else:
                            current_stable_candidate = "NONE"
                            confirmed_cmd = "READY"
                else:
                    confirmed_cmd = raw_cmd
                    if raw_cmd != "READY":
                        come_here_count = 0
        else:
            current_stable_candidate = raw_cmd
            gesture_start_time = curr_time

    # 3. ביצוע פקודות
    if robot and curr_time >= block_until:
        
        # א. פקודות אקשן (ארוכות)
        if confirmed_cmd == "HELLO":
            robot.action(13)
            block_until = curr_time + 4.0 # חסימה ל-4 שניות
            confirmed_cmd = "READY"

        # א. פקודות אקשן (ארוכות)
        if confirmed_cmd == "SPINNING":
            print(">>> EVENT: SPINNING STARTED")
            robot.turn(120)
            # אנחנו קובעים שזמן הסיום יהיה בעוד 4 שניות מהרגע הזה
            # מוסיפים עוד 1.5 שניות לצינון (סה"כ 5.5)
            block_until = time.time() + 5.5 
            last_final_cmd = "SPIN_ACTIVE" # מסמנים שהסיבוב פעיל
            confirmed_cmd = "READY"

        # בדיקה אם סיבוב שהתחיל צריך להסתיים
        if last_final_cmd == "SPIN_ACTIVE" and curr_time >= (block_until - 1.5):
            print(">>> EVENT: SPINNING STOPPED")
            robot.turn(0)
            robot.action(1)
            last_final_cmd = "READY"

        # ב. פקודות תנועה (מוסיפים חסימה קצרה למניעת קפיצות)
        elif confirmed_cmd == "FOLLOW":
            robot.move('x', 12)
            # ב-Follow/Reverse לא נשים חסימה ארוכה כדי לאפשר עצירה
            
        elif confirmed_cmd == "REVERSE":
            robot.move('x', -12)

        # ג. פקודות מצב (סטטיות) - ישיבה, עמידה ועצירה
        elif confirmed_cmd != last_final_cmd and confirmed_cmd != "WAITING...":
            if confirmed_cmd == "STOP":
                robot.stop()
                robot.move('x', 0)
                robot.translation(['z', 'x'], [100, 0])
                robot.attitude('p', 0)
                robot.action(1)
                block_until = curr_time + 1.0

            elif confirmed_cmd == "SIT":
                print(">>> ACTION: MAX REALISTIC SIT - LOCKED")
                robot.stop()
                robot.translation(['z', 'x'], [75, -20])
                robot.attitude('p', 15)
                # חסימה קצרה רק כדי שהתנועה תסתיים, אבל המצב נשאר SIT ב-confirmed_cmd
                block_until = curr_time + 2.0 

            elif confirmed_cmd == "ATTENTION":
                print(">>> ACTION: STANDING UP")
                robot.stop()
                robot.translation(['z', 'x'], [100, 0])
                robot.attitude('p', 0)
                robot.action(1)
                block_until = curr_time + 2.0

            elif confirmed_cmd == "READY":
                # רק אם הפקודה הקודמת לא הייתה SIT, נאפשר חזרה אוטומטית ל-READY
                # זה מונע מהרובוט לקום לבד מישיבה
                if last_final_cmd != "SIT":
                    robot.stop()
                    robot.move('x', 0)
                    robot.translation(['z', 'x'], [100, 0])
                    robot.attitude('p', 0)
                else:
                    # אם היינו ב-SIT והיד נעלמה, נשארים ב-SIT
                    confirmed_cmd = "SIT"

            last_final_cmd = confirmed_cmd



    # תצוגה
    display_text = f"CMD: {confirmed_cmd}"
    if confirmed_cmd == "WAITING...":
        color = (0, 0, 255) # אדום בזמן חסימה
    else:
        color = (0, 255, 0) # ירוק כשאפשר לפעול
        if come_here_count == 1: display_text += " (WAITING FOR 2nd)"
    
    cv2.putText(img, display_text, (20, 50), 1, 1.5, color, 2)
    cv2.imshow("XGO Final Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
