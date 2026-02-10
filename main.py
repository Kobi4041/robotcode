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

# --- הגדרות תצוגה ---
FONT = cv2.FONT_HERSHEY_SIMPLEX
TEXT_COLOR = (255, 255, 255)
SHADOW_COLOR = (0, 0, 0)

# --- משתני יציבות (הוספה חדשה) ---
REQUIRED_DURATION = 1.0  # כמה זמן (בשניות) להחזיק את המחווה
gesture_start_time = 0
current_stable_candidate = "READY"
confirmed_cmd = "READY"
last_final_cmd = ""

cap = cv2.VideoCapture(0)
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

    # 1. זיהוי הפקודה הגולמית מהמצלמה
    raw_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])

    # 2. לוגיקת יציבות (מניעת רגישות יתר)
    if raw_cmd == "READY":
        confirmed_cmd = "READY"
        current_stable_candidate = "READY"
        progress = 0
    elif raw_cmd == current_stable_candidate:
        elapsed = time.time() - gesture_start_time
        progress = min(elapsed / REQUIRED_DURATION, 1.0)
        if elapsed >= REQUIRED_DURATION:
            confirmed_cmd = raw_cmd
    else:
        current_stable_candidate = raw_cmd
        gesture_start_time = time.time()
        progress = 0
        # שומרים על הפקודה האחרונה עד שהחדשה תאושר (אלא אם זה FOLLOW, שם נרצה עצירה מהירה)
        if confirmed_cmd == "FOLLOW": confirmed_cmd = "READY"

    # --- הצגת הפלטים על המסך ---
    cv2.putText(img, f"LEFT: {current_ui['Left']}", (20, 50), FONT, 0.8, SHADOW_COLOR, 4)
    cv2.putText(img, f"LEFT: {current_ui['Left']}", (20, 50), FONT, 0.8, (255, 150, 0), 2)
    cv2.putText(img, f"RIGHT: {current_ui['Right']}", (w-250, 50), FONT, 0.8, SHADOW_COLOR, 4)
    cv2.putText(img, f"RIGHT: {current_ui['Right']}", (w-250, 50), FONT, 0.8, (0, 165, 255), 2)
    
    # הצגת "פס טעינה" ויזואלי למחווה
    if progress > 0 and progress < 1:
        cv2.rectangle(img, (w//2 - 100, h-80), (w//2 + 100, h-70), (50, 50, 50), -1)
        cv2.rectangle(img, (w//2 - 100, h-80), (w//2 - 100 + int(200 * progress), h-70), (0, 255, 255), -1)

    cmd_text = f"ACTION: {confirmed_cmd}"
    t_size = cv2.getTextSize(cmd_text, FONT, 1, 2)[0]
    cv2.putText(img, cmd_text, ((w-t_size[0])//2, h-30), FONT, 1, SHADOW_COLOR, 4)
    cv2.putText(img, cmd_text, ((w-t_size[0])//2, h-30), FONT, 1, (0, 255, 0), 2)

    # --- ביצוע פקודות רובוט ---
    if robot:
        if confirmed_cmd == "FOLLOW":
            robot.move('x', 25) 
            
        elif confirmed_cmd != last_final_cmd:
            if confirmed_cmd == "LIE DOWN":
                robot.stop() 
                robot.translation('z', -70)
                
            elif confirmed_cmd == "ATTENTION":
                robot.stop()
                robot.translation('z', 0)
                robot.action(1)
                
            elif confirmed_cmd == "HELLO":
                robot.stop()
                robot.action(12)
                
            elif confirmed_cmd == "SPINNING":
                print(">>> Robot: Performing a 360-degree turn...")
                robot.stop()
                robot.turn(120)
                time.sleep(3)
                robot.turn(0)
                robot.stop()
                # איפוס מנגנון היציבות לאחר פעולה ארוכה
                current_stable_candidate = "READY"
                confirmed_cmd = "READY"
                print(">>> Robot: Turn completed.")

            elif confirmed_cmd == "READY":
                robot.stop()
                robot.turn(0)
                robot.translation('z', 0)
                print(">>> Robot: Stopped.")

    last_final_cmd = confirmed_cmd

    cv2.imshow("XGO Output Monitor", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
