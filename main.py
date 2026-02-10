import cv2
import mediapipe as mp
from gestures import count_fingers, get_combo_action
import time

# --- ניסיון חיבור לרובוט או מצב סימולציה ---
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
    IS_SIM = False
    print("Connected to XGO Robot")
except (ImportError, ModuleNotFoundError):
    IS_SIM = True
    class XGO_Mock:
        def action(self, cmd_id): print(f"[SIM] ACTION: {cmd_id}")
        def stop(self): print("[SIM] STOP")
        def move(self, direction, step): print(f"[SIM] MOVE: {direction} by {step}mm")
        def turn(self, speed): print(f"[SIM] TURN: {speed} degrees/s")
        def translation(self, axis, value): print(f"[SIM] TRANSLATION: {axis} to {value}")
    robot = XGO_Mock()
    print("Running in Simulation Mode")

# --- הגדרות תצוגה ---
FONT = cv2.FONT_HERSHEY_SIMPLEX

# --- משתני יציבות (זמן אישור) ---
REQUIRED_DURATION = 1.0  # שניה אחת לאישור פעולה
gesture_start_time = 0
current_stable_candidate = "READY"
confirmed_cmd = "READY"
last_final_cmd = ""

cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
# הגדרנו max_num_hands=2 אבל ה-gestures יתעלם משמאל
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
            # זיהוי אם זו יד ימין או שמאל
            label = results.multi_handedness[i].classification[0].label
            # הפונקציה מחזירה פקודה רק עבור יד ימין (לפי העדכון האחרון)
            gesture = count_fingers(hand_lms, label)
            current_ui[label] = gesture
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # 1. זיהוי הפקודה הגולמית (מתבסס בעיקר על Right)
    raw_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])

    # 2. לוגיקת יציבות (מנגנון ה-1.0 שניה)
    if raw_cmd == "READY":
        confirmed_cmd = "READY"
        current_stable_candidate = "READY"
        gesture_start_time = 0
        progress = 0
    elif raw_cmd == current_stable_candidate:
        if gesture_start_time == 0:
            gesture_start_time = time.time()
        
        elapsed = time.time() - gesture_start_time
        progress = min(elapsed / REQUIRED_DURATION, 1.0)
        
        if elapsed >= REQUIRED_DURATION:
            confirmed_cmd = raw_cmd
    else:
        current_stable_candidate = raw_cmd
        gesture_start_time = time.time()
        progress = 0
        # אם היינו ב-FOLLOW (הליכה) והזזנו את היד, עוצרים מיד
        if confirmed_cmd == "FOLLOW": confirmed_cmd = "READY"

    # --- הצגת פלטים על המסך ---
    cv2.putText(img, f"RIGHT HAND: {current_ui['Right']}", (20, 50), FONT, 0.8, (0, 165, 255), 2)
    
    # פס טעינה ויזואלי
    if progress > 0 and progress < 1:
        cv2.rectangle(img, (w//2 - 100, h-80), (w//2 + 100, h-70), (50, 50, 50), -1)
        cv2.rectangle(img, (w//2 - 100, h-80), (w//2 - 100 + int(200 * progress), h-70), (0, 255, 255), -1)

    cmd_text = f"ACTION: {confirmed_cmd}"
    cv2.putText(img, cmd_text, (w//2-100, h-30), FONT, 1, (0, 255, 0), 2)

    # --- ביצוע פקודות רובוט ---
    if robot:
        # פקודה רציפה (זזה כל עוד היד במצב COME)
        if confirmed_cmd == "FOLLOW":
            robot.move('x', 25) 
            
        # פקודות בודדות (מתבצעות רק כשהפקודה משתנה)
        elif confirmed_cmd != last_final_cmd:
            
            if confirmed_cmd == "STOP":
                robot.stop()
                robot.action(10) # שכיבה (LIE DOWN) כפעולת עצירה
                print(">>> Robot STOPPED (0 Fingers)")

            elif confirmed_cmd == "SIT":
                robot.stop() 
                robot.action(12) # פעולת SIT רשמית (2 אצבעות)
                print(">>> Robot SIT (2 Fingers)")
                
            elif confirmed_cmd == "ATTENTION":
                robot.stop()
                robot.translation('z', 0)
                robot.action(1)  # עמידה זקופה (1 אצבע)
                print(">>> Robot STAND (1 Finger)")
                
            elif confirmed_cmd == "HELLO":
                robot.stop()
                robot.action(13) # נפנוף שלום
                
            elif confirmed_cmd == "SPINNING":
                robot.stop()
                robot.turn(120)
                time.sleep(4.2)
                robot.turn(0)
                robot.stop()
                confirmed_cmd = "READY"

            elif confirmed_cmd == "READY":
                robot.stop()
                robot.turn(0)
                robot.translation('z', 0)
                robot.action(1) 

    last_final_cmd = confirmed_cmd
    cv2.imshow("XGO Gesture Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
