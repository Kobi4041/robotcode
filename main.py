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
        # עדכון ה-Mock לפי התיעוד החדש
        def move(self, direction, step): print(f"[SIM] MOVE: {direction} by {step}mm")
        def turn(self, speed): print(f"[SIM] TURN: {speed} degrees/s")
        def translation(self, axis, value): print(f"[SIM] TRANSLATION: {axis} to {value}")

    robot = XGO_Mock()

# --- הגדרות תצוגה ---
FONT = cv2.FONT_HERSHEY_SIMPLEX
TEXT_COLOR = (255, 255, 255)
SHADOW_COLOR = (0, 0, 0)

cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=2)
mp_draw = mp.solutions.drawing_utils

last_final_cmd = ""

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

    final_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])

    # --- הצגת הפלטים על המסך ---
    cv2.putText(img, f"LEFT: {current_ui['Left']}", (20, 50), FONT, 0.8, SHADOW_COLOR, 4)
    cv2.putText(img, f"LEFT: {current_ui['Left']}", (20, 50), FONT, 0.8, (255, 150, 0), 2)
    cv2.putText(img, f"RIGHT: {current_ui['Right']}", (w-250, 50), FONT, 0.8, SHADOW_COLOR, 4)
    cv2.putText(img, f"RIGHT: {current_ui['Right']}", (w-250, 50), FONT, 0.8, (0, 165, 255), 2)
    
    cmd_text = f"TOTAL ACTION: {final_cmd}"
    t_size = cv2.getTextSize(cmd_text, FONT, 1, 2)[0]
    cv2.putText(img, cmd_text, ((w-t_size[0])//2, h-40), FONT, 1, SHADOW_COLOR, 4)
    cv2.putText(img, cmd_text, ((w-t_size[0])//2, h-40), FONT, 1, (0, 255, 0), 2)

    # --- ביצוע פקודות רובוט ---
    if robot:
        if final_cmd == "FOLLOW":
            # לפי התיעוד: 'x' זה כיוון, 25 זה גודל הצעד (מ"מ)
            robot.move('x', 25) 
            

            
        elif final_cmd != last_final_cmd:
            if final_cmd == "LIE DOWN":
                robot.stop() 
                robot.translation('z', -70)
                
            elif final_cmd == "ATTENTION":
                robot.stop()
                robot.translation('z', 0)
                robot.action(1)
                
            elif final_cmd == "HELLO":
                robot.stop()
                robot.action(12)
                
            elif final_cmd == "SPINNING":
                # כאן אנחנו יוצרים סיבוב עצמאי בלי action מובנה
                print(">>> Robot: Performing a 360-degree turn...")
                robot.stop()      # איפוס לפני תחילת סיבוב
                robot.turn(120)   # מהירות סיבוב (120 מעלות לשנייה)
                time.sleep(3)     # נחכה 3 שניות (120 * 3 = 360 מעלות)
                robot.turn(0)     # פקודת עצירה לסיבוב
                robot.stop()      # חזרה למצב יציב
                print(">>> Robot: Turn completed.")

            elif final_cmd == "READY":
                robot.stop()
                robot.turn(0)
                robot.translation('z', 0)
                print(">>> Robot: Stopped.")

    last_final_cmd = final_cmd

    cv2.imshow("XGO Output Monitor", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
