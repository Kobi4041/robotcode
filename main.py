import cv2
import mediapipe as mp
import time
from gestures import count_fingers, get_combo_action
def set_static_lie_down(robot_instance):
    # שימוש ב-translation כדי "לנעול" אותו למטה
    robot_instance.translation(0, 0, -60)
    print(">>> Status: STATIC LIE DOWN")

def set_static_stand(robot_instance):
    # מחזיר לגובה אפס ומאפס פוזה
    robot_instance.translation(0, 0, 0)
    robot_instance.action(1)
    print(">>> Status: STATIC STAND")

# --- ניסיון חיבור לרובוט או מצב סימולציה ---
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
    IS_SIM = False
    print(">>> Connected to XGO")
except (ImportError, ModuleNotFoundError):
    IS_SIM = True
    class XGO_Mock:
        def action(self, cmd_id): print(f"ACTION SENT: {cmd_id}")
        def stop(self): print("STOP SENT")
    robot = XGO_Mock()
    print(">>> Simulation Mode")

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

    # פלט משולב
    final_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])

    # --- לוגיקת ביצוע פיזית ללא STOP מפריע ---
    if final_cmd != last_final_cmd:
        if final_cmd == "LIE DOWN":
            set_static_lie_down(robot)
            
        elif final_cmd == "ATTENTION":
            def set_static_stand(robot)
            
        # שים לב: אין כאן else עם robot.stop()!
        # הרובוט יסיים את הפעולה האחרונה ויישאר בה.
        
        last_final_cmd = final_cmd

    # --- תצוגת פלט על המסך (שקוף) ---
    # יד שמאל
    cv2.putText(img, f"LEFT: {current_ui['Left']}", (20, 50), 1, 1.5, (255, 150, 0), 2)
    # יד ימין
    cv2.putText(img, f"RIGHT: {current_ui['Right']}", (w-250, 50), 1, 1.5, (0, 165, 255), 2)
    # פלט סופי
    cv2.putText(img, f"ROBOT: {final_cmd}", (w//2-100, h-40), 1, 2, (0, 255, 0), 3)

    cv2.imshow("XGO Monitor", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
