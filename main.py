import cv2
import mediapipe as mp
from gestures import count_fingers, get_combo_action
import time

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
            if results.multi_handedness[i].classification[0].label == "Right":
                current_ui_right = count_fingers(hand_lms, "Right")
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    raw_cmd = get_combo_action("None", current_ui_right)

    # 1. ניהול צינון ויציבות
    if curr_time < block_until:
        confirmed_cmd = "WAITING..."
    else:
        if raw_cmd == current_stable_candidate:
            if gesture_start_time == 0: gesture_start_time = curr_time
            if curr_time - gesture_start_time >= REQUIRED_DURATION:
                if raw_cmd == "FOLLOW":
                    if curr_time - last_come_time > 5.0: come_here_count = 0
                    if last_final_cmd != "FOLLOW" and confirmed_cmd != "FOLLOW":
                        come_here_count += 1
                        last_come_time = curr_time
                        if come_here_count >= 2:
                            confirmed_cmd = "FOLLOW"
                            come_here_count = 0
                        else:
                            current_stable_candidate = "NONE"
                            confirmed_cmd = "READY"
                else:
                    confirmed_cmd = raw_cmd
                    come_here_count = 0
        else:
            current_stable_candidate = raw_cmd
            gesture_start_time = curr_time

    # 2. ביצוע פקודות
    if robot and confirmed_cmd != "WAITING...":
        # פקודות אקשן
        if confirmed_cmd == "HELLO":
            robot.action(13)
            block_until = curr_time + 3.0
            confirmed_cmd = "READY"
        
        elif confirmed_cmd == "SPINNING":
            robot.turn(120)
            time.sleep(4) # פקודה חוסמת לסיבוב
            robot.turn(0)
            robot.action(1)
            block_until = curr_time + 1.0
            confirmed_cmd = "READY"

        # תנועה רציפה
        elif confirmed_cmd == "FOLLOW":
            robot.move('x', 12)
        elif confirmed_cmd == "REVERSE":
            robot.move('x', -12)

        # שינוי מצב (סטטי)
        elif confirmed_cmd != last_final_cmd:
            robot.stop()
            if confirmed_cmd == "STOP":
                robot.translation(['z', 'x'], [100, 0])
                robot.attitude('p', 0)
                robot.action(1)
            elif confirmed_cmd == "SIT":
                robot.translation(['z', 'x'], [75, -20])
                robot.attitude('p', 15)
            elif confirmed_cmd == "ATTENTION":
                robot.translation(['z', 'x'], [100, 0])
                robot.attitude('p', 0)
                robot.action(1)
            elif confirmed_cmd == "READY":
                # מניעת קימה אוטומטית מ-SIT
                if last_final_cmd == "SIT":
                    confirmed_cmd = "SIT"
                else:
                    robot.move('x', 0)
                    robot.translation(['z', 'x'], [100, 0])
                    robot.attitude('p', 0)
            
            last_final_cmd = confirmed_cmd

    # 3. תצוגה
    color = (0, 0, 255) if confirmed_cmd == "WAITING..." else (0, 255, 0)
    display_text = f"CMD: {confirmed_cmd}"
    if come_here_count == 1: display_text += " (WAITING FOR 2nd)"
    
    cv2.putText(img, display_text, (20, 50), 1, 1.5, color, 2)
    cv2.imshow("XGO Final Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
