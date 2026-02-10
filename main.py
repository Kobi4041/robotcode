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
        def move(self, dir, step): pass
        def translation(self, axis, val): pass
    robot = XGO_Mock()

# --- משתני שליטה ---
REQUIRED_DURATION = 0.8 
gesture_start_time = 0
current_stable_candidate = "READY"
confirmed_cmd = "READY"
last_final_cmd = ""
block_until = 0  # תקופת הצינון

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

    # 1. זיהוי פקודה
    raw_cmd = get_combo_action("None", current_ui_right)

    # 2. ניהול צינון - חוסם רק פקודות חדשות
    if curr_time < block_until:
        confirmed_cmd = "WAITING..."
    else:
        if raw_cmd == current_stable_candidate:
            if gesture_start_time == 0: gesture_start_time = curr_time
            if curr_time - gesture_start_time >= REQUIRED_DURATION:
                confirmed_cmd = raw_cmd
        else:
            current_stable_candidate = raw_cmd
            gesture_start_time = curr_time

    # 3. ביצוע פקודות
    if robot:
        # פקודות עם צינון (Spin ו-Wave)
        if confirmed_cmd in ["HELLO", "SPINNING"] and curr_time > block_until:
            if confirmed_cmd == "HELLO":
                robot.action(13)
                block_until = curr_time + 3.0 # זמן לביצוע הנפנוף + מנוחה
            
            elif confirmed_cmd == "SPINNING":
                robot.turn(120)
                time.sleep(4.2) # כאן ה-sleep סביר כי זו פעולה חוסמת ממילא
                robot.turn(0)
                robot.action(1)
                block_until = curr_time + 1.5 # צינון אחרי הסיבוב
            
            confirmed_cmd = "READY"

        # פקודה רציפה (FOLLOW) - ללא צינון
        elif confirmed_cmd == "FOLLOW":
            robot.move('x', 12)

        # פקודות סטטיות
        elif confirmed_cmd != last_final_cmd and confirmed_cmd != "WAITING...":
            if confirmed_cmd == "STOP":
                robot.stop()
                robot.move('x', 0)
                robot.action(1)
            elif confirmed_cmd == "SIT":
                robot.translation('z', -60)
            elif confirmed_cmd == "ATTENTION":
                robot.translation('z', 0)
                robot.action(1)
            elif confirmed_cmd == "READY":
                robot.stop()
                robot.translation('z', 0)

    last_final_cmd = confirmed_cmd
    cv2.putText(img, f"CMD: {confirmed_cmd}", (20, 50), 1, 1, (0, 255, 0), 2)
    cv2.imshow("XGO Final Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
