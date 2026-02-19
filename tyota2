import cv2
import mediapipe as mp
import time
from gestnew import count_fingers, detect_circle

# --- אתחול רובוט ---
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
except:
    class XGO_Mock:
        def action(self, cmd_id): print(f"[SIM] ACTION: {cmd_id}")
        def stop(self): print("[SIM] STOP")
        def reset(self): print("[SIM] RESET")
        def turn(self, val): print(f"[SIM] TURN: {val}")
        def move(self, dir, val): print(f"[SIM] MOVE: {dir} {val}")
        def pace(self, p): pass
        def mark_time(self, t): pass
        def translation(self, a, v): pass
        def attitude(self, a, v): pass
    robot = XGO_Mock()

cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=2)
mp_draw = mp.solutions.drawing_utils

confirmed_cmd = "STAND"
last_final_cmd = ""
is_turning_360 = False
turn_start_time = 0

while cap.isOpened():
    success, img = cap.read()
    if not success: break
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    current_time = time.time()
    raw_cmd = "NONE"
    hand_states = {"Right": "NONE", "Left": "NONE"}

    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            label = results.multi_handedness[i].classification[0].label
            hand_states[label] = count_fingers(hand_lms, label)
            
            # בדיקת עיגול רק ביד ימין
            if label == "Right" and hand_states["Right"] == "STAND":
                if detect_circle(hand_lms):
                    hand_states["Right"] = "SPINNING"

            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # --- לוגיקת היררכיה "יד ימין בלבד + סיוע משמאל" ---
    right = hand_states["Right"]
    left = hand_states["Left"]

    if right != "NONE":
        # אם ימין על SIT, נבדוק אם שמאל מסייעת ל-PUSHUPS
        if right == "SIT" and left == "SIT":
            raw_cmd = "PUSHUPS"
        else:
            # בכל מקרה אחר שיד ימין נמצאת, היא הקובעת
            raw_cmd = right
    
    # שים לב: אין כאן "elif left != NONE" - אם יד ימין לא בפריים, הרובוט לא יגיב ליד שמאל

    if raw_cmd != "NONE":
        confirmed_cmd = raw_cmd

    # --- ניהול סיבוב ---
    if is_turning_360:
        if current_time - turn_start_time > 4.35:
            robot.turn(0)
            is_turning_360 = False
            confirmed_cmd = "STAND"

    # --- ביצוע ברובוט ---
    if confirmed_cmd != last_final_cmd:
        if not is_turning_360:
            robot.stop()
            if confirmed_cmd == "PUSHUPS": 
                robot.action(21)
            elif confirmed_cmd == "SPINNING":
                robot.turn(93)
                turn_start_time = current_time
                is_turning_360 = True
            elif confirmed_cmd == "SIT":
                # פקודת ישיבה "ידנית" דרך איברי הגוף
                robot.translation(['z', 'x'], [75, -35])
                robot.attitude('p', -15)
            elif confirmed_cmd == "STAND": 
                robot.reset()
            elif confirmed_cmd == "STOP": 
                robot.stop()
            elif confirmed_cmd == "HELLO": 
                robot.action(13)
            elif confirmed_cmd == "FOLLOW": 
                robot.move('x', 12)
            elif confirmed_cmd == "REVERSE": 
                robot.move('x', -12)
            
            last_final_cmd = confirmed_cmd

    # --- תצוגה ---
    # יד שמאל נצבעת רק כשהיא משתתפת ב-PUSHUPS
    r_color = (0, 255, 0) if right != "NONE" else (200, 200, 200)
    l_color = (255, 255, 0) if (left == "SIT" and right == "SIT") else (100, 100, 100)

    cv2.putText(img, f"Right (CONTROL): {right}", (20, 50), 1, 1.2, r_color, 2)
    cv2.putText(img, f"Left (ASSIST): {left}", (20, 90), 1, 1.2, l_color, 2)
    
    status_text = f"CMD: {confirmed_cmd}"
    cv2.putText(img, status_text, (20, 450), 1, 2, (255, 255, 255), 3)

    cv2.imshow("XGO Right Hand Master", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
