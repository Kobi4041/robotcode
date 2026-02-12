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
        def move(self, direction, step): print(f"[SIM] MOVE: {direction} {step}")
        def translation(self, axis, val): print(f"[SIM] TRANS: {axis} to {val}")
    robot = XGO_Mock()

# --- משתני שליטה ---
REQUIRED_DURATION = 0.8 
gesture_start_time = 0
current_stable_candidate = "READY"
confirmed_cmd = "READY"
last_final_cmd = ""
block_until = 0  

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
    
    # איחוד לוגי: אם חזר "LIE DOWN" מהמחוות, נתייחס אליו כ-"SIT"
    if raw_cmd == "LIE DOWN":
        raw_cmd = "SIT"

    # 2. ניהול צינון ויציבות
    if curr_time < block_until:
        display_status = "BUSY..."
    else:
        display_status = confirmed_cmd
        if raw_cmd == current_stable_candidate:
            if gesture_start_time == 0: gesture_start_time = curr_time
            if curr_time - gesture_start_time >= REQUIRED_DURATION:
                confirmed_cmd = raw_cmd
        else:
            current_stable_candidate = raw_cmd
            gesture_start_time = curr_time

    # 3. ביצוע פקודות רובוט
    if robot:
        if curr_time >= block_until:
            
            # א. פקודות אקשן חד-פעמיות
            if confirmed_cmd == "HELLO":
                print(">>> EVENT: HELLO ACTIVATED")
                robot.action(13)
                block_until = curr_time + 3.0 
                confirmed_cmd = "READY"

            elif confirmed_cmd == "SPINNING":
                print(">>> EVENT: SPINNING ACTIVATED")
                robot.turn(120)
                block_until = curr_time + 4.2 
                last_final_cmd = "SPIN_STARTED"
                confirmed_cmd = "READY"

            if last_final_cmd == "SPIN_STARTED" and curr_time >= block_until:
                print(">>> SYSTEM: SPIN COMPLETED")
                robot.turn(0)
                robot.stop()
                robot.action(1)
                last_final_cmd = "READY"

            # ב. פקודות תנועה רציפה
            if confirmed_cmd == "FOLLOW":
                if last_final_cmd != "FOLLOW":
                    print(">>> MOVE: FOLLOW START")
                robot.move('x', 12)
                
            elif confirmed_cmd == "REVERSE":
                if last_final_cmd != "REVERSE":
                    print(">>> MOVE: REVERSE START")
                robot.move('x', -12)

            # ג. פקודות מצב (סטטיות)
            elif confirmed_cmd != last_final_cmd:
                if confirmed_cmd == "STOP":
                    print(">>> ACTION: STOP")
                    robot.stop()
                    robot.move('x', 0)
                    robot.action(1)
                
                elif confirmed_cmd == "SIT":
                    print(">>> ACTION: SIT")
                    robot.stop()
                    robot.translation('z', -70) # גובה ישיבה אחיד
                
                elif confirmed_cmd == "ATTENTION":
                    print(">>> ACTION: ATTENTION")
                    robot.stop()
                    robot.translation('z', 0)
                    robot.action(1)
                
                elif confirmed_cmd == "READY":
                    if last_final_cmd not in ["READY", ""]:
                        print(">>> ACTION: READY (STANDBY)")
                    robot.stop()
                    robot.move('x', 0)
                    robot.translation('z', 0)
                    robot.action(1)

                last_final_cmd = confirmed_cmd

    # תצוגה על המסך
    color = (0, 0, 255) if curr_time < block_until else (0, 255, 0)
    cv2.putText(img, f"CMD: {display_status}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    
    cv2.imshow("XGO Final Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
