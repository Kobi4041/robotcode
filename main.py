import cv2
import mediapipe as mp
from gestures import count_fingers, get_combo_action

# --- ניסיון חיבור לרובוט או מצב סימולציה ---
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
    IS_SIM = False
except (ImportError, ModuleNotFoundError):
    IS_SIM = True
    class XGO_Mock:
        def action(self, cmd_id): print(f"ACTION: {cmd_id}")
        def stop(self): pass
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
            # קבלת הפלט של היד הבודדת
            gesture = count_fingers(hand_lms, label)
            current_ui[label] = gesture
            
            # ציור שלד היד בצורה עדינה
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # קבלת הפלט המשולב או תנועה בתזוזה
    final_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])

    # --- הצגת הפלטים על המסך (Overlay) ---
    
    # 1. פלט יד שמאל
    cv2.putText(img, f"LEFT: {current_ui['Left']}", (20, 50), FONT, 0.8, SHADOW_COLOR, 4) # צל
    cv2.putText(img, f"LEFT: {current_ui['Left']}", (20, 50), FONT, 0.8, (255, 150, 0), 2)
    
    # 2. פלט יד ימין
    cv2.putText(img, f"RIGHT: {current_ui['Right']}", (w-250, 50), FONT, 0.8, SHADOW_COLOR, 4) # צל
    cv2.putText(img, f"RIGHT: {current_ui['Right']}", (w-250, 50), FONT, 0.8, (0, 165, 255), 2)
    
    # 3. פלט משולב/תנועה (מרכז תחתון)
    cmd_text = f"TOTAL ACTION: {final_cmd}"
    t_size = cv2.getTextSize(cmd_text, FONT, 1, 2)[0]
    cv2.putText(img, cmd_text, ((w-t_size[0])//2, h-40), FONT, 1, SHADOW_COLOR, 4) # צל
    cv2.putText(img, cmd_text, ((w-t_size[0])//2, h-40), FONT, 1, (0, 255, 0), 2)

    # לוגיקת ביצוע פיזית
    if final_cmd != last_final_cmd:
        if final_cmd == "LIE DOWN": robot.translation('z',-50)
        elif final_cmd in ["ATTENTION", "STAND"]: robot.action(1)
        else: robot.stop()
        last_final_cmd = final_cmd

    cv2.imshow("XGO Output Monitor", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()

