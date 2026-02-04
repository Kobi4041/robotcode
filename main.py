import cv2
import mediapipe as mp
import time
from gestures import count_fingers

# --- אתחול רובוט ---
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
    IS_SIM = False
    
    print(">>> Initializing Connection...")
    # המתנה ארוכה יותר כדי לוודא שהרובוט "התעורר"
    time.sleep(2.0) 
    
    # פקודת עמידה כפולה כדי לוודא שהוא קם ב-100%
    robot.action(1) 
    time.sleep(0.5)
    robot.action(1)
    
    print(">>> Robot should be STANDING and Ready")
except (ImportError, ModuleNotFoundError):
    IS_SIM = True
    class XGO_Mock:
        def action(self, cmd_id): print(f"ACTION SENT: {cmd_id}")
    robot = XGO_Mock()
    print(">>> Running in Simulation Mode")

# --- משתני שליטה ---
last_executed_action = 1  # מתחילים במצב עמידה (1)
required_duration = 1.0   # זמן אישור של שנייה אחת
gesture_start_time = 0
current_stable_gesture = "None"

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
    
    right_hand_status = "None"

    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            label = results.multi_handedness[i].classification[0].label
            
            # מתמקדים רק ביד ימין
            if label == "Right":
                right_hand_status = count_fingers(hand_lms, "Right")
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
                break

    # תרגום ה-Gesture לפעולה (Action 13 לשכיבה, Action 1 לעמידה)
    target_action = None
    if right_hand_status == "SIT": 
        target_action = 13
    elif right_hand_status == "STAND": 
        target_action = 1

    # --- לוגיקת אישור ונעילה ---
    if target_action is not None:
        if target_action == current_stable_gesture:
            elapsed = time.time() - gesture_start_time
            
            # מד טעינה ויזואלי
            progress = min(elapsed / required_duration, 1.0)
            cv2.rectangle(img, (20, h-50), (int(20 + (w-40)*progress), h-30), (0, 255, 0), -1)
            
            if elapsed >= required_duration and target_action != last_executed_action:
                robot.action(target_action)
                last_executed_action = target_action
        else:
            current_stable_gesture = target_action
            gesture_start_time = time.time()
    else:
        current_stable_gesture = "None"

    #
