import cv2
import mediapipe as mp
import time
import math
from xgolib import XGO
from gestures import count_fingers, get_combo_action

# --- אתחול הרובוט ---
try:
    robot = XGO(port='/dev/ttyAMA0')
    robot.translation(0, 0, 0) # איפוס לעמידה
    print("SUCCESS: Robot Connected")
except Exception as e:
    print(f"SIMULATION MODE: Robot not connected ({e})")
    robot = None

# --- הגדרות MediaPipe ---
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
            # קריאה לפונקציית זיהוי האצבעות מהקובץ השני
            gesture = count_fingers(hand_lms, label)
            current_gestures[label] = gesture
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # קביעת הפקודה המשולבת (Logic מתוך gestures.py)
    detected_cmd = get_combo_action(current_gestures["Left"], current_gestures["Right"])

    # --- מנגנון יציבות וביצוע ---
    if detected_cmd != "READY":
        if detected_cmd == current_detected:
            elapsed = time.time() - gesture_start_time
            
            # ויזואליזציה של מד טעינה
            progress = min(elapsed / required_duration, 1.0)
            cv2.rectangle(img, (w//2-100, h-60), (w//2-100 + int(200*progress), h-40), (0, 255, 0), -1)
            cv2.rectangle(img, (w//2-100, h-60), (w//2+100, h-40), (255, 255, 255), 2)
            
            if elapsed >= required_duration and detected_cmd != last_final_cmd:
                print(f">>> Executing: {detected_cmd}")
                if robot:
                    if detected_cmd == "LIE DOWN":
                        robot.translation(0, 0, -60) # שכיבה סטטית
                        
                    elif detected_cmd == "ATTENTION":
                        robot.translation(0, 0, 0)   # עמידה סטטית
                        robot.action(1)
                        
                    elif detected_cmd == "FOLLOW":
                        robot.move(0.4, 0)           # הליכה קדימה
                        
                    elif detected_cmd == "SPINNING":
                        robot.turn(60)               # סיבוב במקום
                
                last_final_cmd = detected_cmd
        else:
            current_detected = detected_cmd
            gesture_start_time = time.time()
    else:
        # אם המצב הוא READY או שאין ידיים - עוצרים תנועה ומאפסים
        if last_final_cmd != "READY":
            if robot:
                robot.stop()
                robot.translation(0, 0, 0)
            last_final_cmd = "READY"
            current_detected = "READY"

    # --- תצוגת UI על המסך ---
    # רקע כהה לטקסט למעלה
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, img, 0.5, 0, img)

    cv2.putText(img, f"L: {current_gestures['Left']}", (20, 45), 1, 1.5, (255, 255, 0), 2)
    cv2.putText(img, f"R: {current_gestures['Right']}", (w-200, 45), 1, 1.5, (0, 255, 255), 2)
    
    # מצב פעיל
    status_color = (0, 255, 0) if last_final_cmd != "READY" else (255, 255, 255)
    cv2.putText(img, f"CMD: {last_final_cmd}", (w//2-80, 50), 1, 2, status_color, 3)

    cv2.imshow("XGO Pro Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
