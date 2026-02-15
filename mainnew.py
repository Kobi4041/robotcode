import cv2
import mediapipe as mp
import time
from gestnew import count_fingers, detect_circle # וודא ש-detect_circle מוגדר ב-gestnew

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
    robot = XGO_Mock()

cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
# הגדרה ל-2 ידיים
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
    # מילון לאחסון המצבים שנקלטו מהחיישן (המצלמה)
    hand_states = {"Right": "NONE", "Left": "NONE"}

    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            label = results.multi_handedness[i].classification[0].label
            # המודל קולט את שתי הידיים
            hand_states[label] = count_fingers(hand_lms, label)
            
            # בדיקת עיגול (Spin) - רק ביד ימין
            if label == "Right" and hand_states["Right"] == "STAND":
                if detect_circle(hand_lms):
                    hand_states["Right"] = "SPINNING"

            # ציור השלד על המסך
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # --- לוגיקת ההפעלה ---
    right = hand_states["Right"]
    left = hand_states["Left"]

    # 1. בדיקת פקודה משולבת (עדיפות עליונה)
    if right == "SIT" and left == "SIT":
        raw_cmd = "ACTION_21"
    
    # 2. אם אין פקודה משולבת, רק יד ימין קובעת
    elif right != "NONE":
        raw_cmd = right

    if raw_cmd != "NONE":
        confirmed_cmd = raw_cmd

    # --- ניהול סיבוב 360 מעלות ---
    if is_turning_360:
        if current_time - turn_start_time > 4.35:
            robot.turn(0)
            is_turning_360 = False
            confirmed_cmd = "STAND"
            print("Finished spinning.")

    # --- ביצוע ברובוט ---
    if confirmed_cmd != last_final_cmd:
        # עצירה בטיחותית לפני פעולה חדשה (אלא אם אנחנו באמצע סיבוב)
        if not is_turning_360:
            robot.stop()
            
            if confirmed_cmd == "ACTION_21":
                robot.action(21)
            elif confirmed_cmd == "SPINNING":
                robot.turn(93)
                turn_start_time = current_time
                is_turning_360 = True
            elif confirmed_cmd == "SIT":
                robot.action(1)
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
            elif confirmed_cmd == "FIVE":
                robot.reset()
            
            last_final_cmd = confirmed_cmd

    # --- תצוגה על המסך ---
    # מציג מה המצלמה קולטת מכל יד
    cv2.putText(img, f"Left Hand (Sensors): {left}", (20, 50), 1, 1.2, (255, 0, 0), 2)
    cv2.putText(img, f"Right Hand (Control): {right}", (20, 90), 1, 1.2, (0, 255, 0), 2)
    
    # מציג מה הרובוט מבצע בפועל
    status_text = f"ROBOT: {confirmed_cmd}"
    if is_turning_360: status_text += " !!!"
    cv2.putText(img, status_text, (20, 450), 1, 2, (255, 255, 255), 3)

    cv2.imshow("XGO Dual Hand System", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
