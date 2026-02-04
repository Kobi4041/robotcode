import cv2
import mediapipe as mp
import time
from xgolib import XGO
from gestures import count_fingers, get_combo_action

# --- אתחול הרובוט ---
try:
    robot = XGO(port='/dev/ttyAMA0')
    robot.translation(0, 0, 0) # עמידה התחלתית
    print("Robot Connected")
except:
    print("Robot not found - Running in Simulation Mode")
    robot = None

# --- הגדרות ויזואליזציה ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=2)
mp_draw = mp.solutions.drawing_utils

# --- משתני שליטה ---
last_final_cmd = ""
gesture_start_time = 0
current_detected = "READY"
required_duration = 1.0  # שנייה אחת לאישור פקודה

cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, img = cap.read()
    if not success: break
    
    img = cv2.flip(img, 1)
    h, w, _ = img.shape
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    current_gestures = {"Left": "None", "Right": "None"}
    
    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            label = results.multi_handedness[i].classification[0].label
            gesture = count_fingers(hand_lms, label)
            current_gestures[label] = gesture
            
            # ציור נקודות יד
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # שליפת הפעולה המשולבת (לפי ה-logic של gestures.py)
    detected_cmd = get_combo_action(current_gestures["Left"], current_gestures["Right"])

    # --- מנגנון יציבות (ספירה של שנייה אחת) ---
    if detected_cmd in ["LIE DOWN", "ATTENTION"]:
        if detected_cmd == current_detected:
            elapsed = time.time() - gesture_start_time
            # ויזואליזציה של מד טעינה
            progress = min(elapsed / required_duration, 1.0)
            cv2.rectangle(img, (w//2-100, h-60), (w//2-100 + int(200*progress), h-40), (0, 255, 0), -1)
            cv2.rectangle(img, (w//2-100, h-60), (w//2+100, h-40), (255, 255, 255), 2)
            
            if elapsed >= required_duration and detected_cmd != last_final_cmd:
                # --- ביצוע פעולה סטטית ---
                if robot:
                    if detected_cmd == "LIE DOWN":
                        robot.translation(0, 0, -60) # שכיבה סטטית
                    elif detected_cmd == "ATTENTION":
                        robot.translation(0, 0, 0)   # עמידה סטטית
                        robot.action(1)              # יישור רגליים
                
                last_final_cmd = detected_cmd
                print(f"EXECUTED: {detected_cmd}")
        else:
            current_detected = detected_cmd
            gesture_start_time = time.time()
    else:
        current_detected = "READY"

    # --- ויזואליזציה (UI) ---
    # רקע שקוף לטקסט
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, img, 0.5, 0, img)

    # הצגת המצב הנוכחי של הידיים
    cv2.putText(img, f"LEFT: {current_gestures['Left']}", (20, 35), 1, 1.5, (255, 255, 0), 2)
    cv2.putText(img, f"RIGHT: {current_gestures['Right']}", (w-250, 35), 1, 1.5, (255, 255, 0), 2)
    
    # הצגת הפקודה שנבחרה
    color = (0, 255, 0) if last_final_cmd == detected_cmd else (255, 255, 255)
    cv2.putText(img, f"MODE: {last_final_cmd}", (w//2-100, 70), 1, 1.8, color, 3)

    cv2.imshow("XGO Static Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
