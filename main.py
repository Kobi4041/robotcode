import cv2
import mediapipe as mp
from gestures import count_fingers, get_combo_action
import time

# --- ניסיון חיבור לרובוט או מצב סימולציה ---
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
    IS_SIM = False
except (ImportError, ModuleNotFoundError):
    IS_SIM = True
    class XGO_Mock:
        def action(self, cmd_id): print(f"[SIM] ACTION: {cmd_id}")
        def stop(self): print("[SIM] STOP")
        def move(self, direction, step): print(f"[SIM] MOVE: {direction} by {step}mm")
        def turn(self, speed): print(f"[SIM] TURN: {speed} degrees/s")
        def translation(self, axis, value): print(f"[SIM] TRANSLATION: {axis} to {value}")
    robot = XGO_Mock()

# --- אתחול מערכת ---
print(">>> Robot Initializing to Standing Pose...")
robot.stop()
robot.action(1)  # עמידה ראשונית
robot.translation('z', 0)
time.sleep(1.5)

# --- הגדרות ---
FONT = cv2.FONT_HERSHEY_SIMPLEX
REQUIRED_DURATION = 1.0
FOLLOW_DURATION = 2.0
gesture_start_time = time.time()
current_stable_candidate = "READY"
confirmed_cmd = "READY"
last_final_cmd = ""
is_busy = False

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=2)
mp_draw = mp.solutions.drawing_utils

while cap.isOpened():
    success, img = cap.read()
    if not success: break

    img = cv2.flip(img, 1)
    h, w, _ = img.shape
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    current_ui = {"Left": "None", "Right": "None"}

    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            label = results.multi_handedness[i].classification[0].label
            gesture = count_fingers(hand_lms, label)
            current_ui[label] = gesture
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    raw_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])

    # 2. לוגיקת יציבות עם "איפוס זיכרון" בזמן עבודה
    if not is_busy:
        if raw_cmd == "READY":
            confirmed_cmd = "READY"
            current_stable_candidate = "READY"
            progress = 0
        elif raw_cmd == current_stable_candidate:
            elapsed = time.time() - gesture_start_time
            needed = FOLLOW_DURATION if raw_cmd == "FOLLOW" else REQUIRED_DURATION
            progress = min(elapsed / needed, 1.0)
            if elapsed >= needed:
                confirmed_cmd = raw_cmd
        else:
            current_stable_candidate = raw_cmd
            gesture_start_time = time.time()
            progress = 0
            if confirmed_cmd == "FOLLOW": confirmed_cmd = "READY"
    else:
        # כאן התיקון: כל עוד הרובוט עסוק, השעון מתאפס והוא לא "זוכר" פקודות
        gesture_start_time = time.time()
        current_stable_candidate = "READY"
        progress = 1.0

    # --- תצוגה ---
    cv2.putText(img, f"L: {current_ui['Left']}", (10, 25), FONT, 0.5, (255, 150, 0), 1)
    cv2.putText(img, f"R: {current_ui['Right']}", (w-110, 25), FONT, 0.5, (0, 165, 255), 1)
    status_text = "BUSY..." if is_busy else f"CMD: {confirmed_cmd}"
    cv2.putText(img, status_text, (w//2-40, h-25), FONT, 0.5, (0, 255, 0), 1)

    # --- ביצוע פקודות ---
    if robot and not is_busy:
        if confirmed_cmd == "FOLLOW":
            if raw_cmd == "FOLLOW":
                robot.move('x', 15)
            else:
                robot.move('x', 0)
            
        elif confirmed_cmd != last_final_cmd:
            if confirmed_cmd == "LIE DOWN":
                is_busy = True
                robot.stop() 
                robot.translation('z', -70)
                time.sleep(1.5)
                is_busy = False
                confirmed_cmd = "READY" # מחזיר ל-READY לאיפוס
                
            elif confirmed_cmd == "ATTENTION":
                is_busy = True
                robot.stop()
                robot.action(1)
                time.sleep(2)
                is_busy = False
                confirmed_cmd = "READY"
                
            elif confirmed_cmd == "HELLO":
                is_busy = True
                robot.action(12)
                time.sleep(4) 
                is_busy = False
                confirmed_cmd = "READY"
                
            elif confirmed_cmd == "SPINNING":
                is_busy = True
                robot.stop()
                robot.turn(120)
                time.sleep(4)  # 4 שניות לסיבוב מלא
                robot.turn(0)
                robot.stop()
                is_busy = False
                confirmed_cmd = "READY"

            elif confirmed_cmd == "READY":
                # כאן התיקון: חזרה לעמידה זקופה ב-READY
                robot.stop()
                robot.turn(0)
                robot.translation('z', 0)
                robot.move('x', 0)
                if last_final_cmd != "READY":
                    robot.action(1) # הזדקפות חד פעמית

    last_final_cmd = confirmed_cmd
    cv2.imshow("XGO Monitor", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
