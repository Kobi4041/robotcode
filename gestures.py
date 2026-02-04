import cv2
import mediapipe as mp
import time
from gestures import count_fingers, get_combo_action

# --- הגנה ודימוי רובוט ---
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
    IS_SIM = False
except (ImportError, ModuleNotFoundError):
    IS_SIM = True
    class XGO_Mock:
        def action(self, cmd_id): print(f"ACTION SENT: {cmd_id}")
        def stop(self): print("STOP SENT (Skipped if Pose)")
    robot = XGO_Mock()

# --- משתני שליטה בזמן ---
gesture_start_time = 0
current_stable_gesture = "READY"
required_duration = 2.0  # כמה זמן להחזיק את הידיים (שניות)
is_locked = False        # האם הרובוט כרגע באמצע ביצוע
lock_duration = 3.0      # כמה זמן לנעול את הפעולה (שניות)

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

    # פלט משולב נוכחי מהמצלמה (לפי gestures.py)
    detected_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])

    # --- לוגיקת השהיה (2 שניות) ונעילה ---
    final_cmd = "READY" # ברירת מחדל בתוך הלולאה
    
    if not is_locked:
        if detected_cmd == current_stable_gesture and detected_cmd not in ["READY", "IDLE"]:
            elapsed = time.time() - gesture_start_time
            
            # ציור מד טעינה (Progress Bar)
            progress = min(elapsed / required_duration, 1.0)
            cv2.rectangle(img, (w//2-100, h-100), (w//2-100 + int(200*progress), h-80), (0, 255, 255), -1)
            cv2.rectangle(img, (w//2-100, h-100), (w//2+100, h-80), (255, 255, 255), 2) # מסגרת
            
            if elapsed >= required_duration:
                final_cmd = detected_cmd
                is_locked = True 
                lock_start_time = time.time()
        else:
            current_stable_gesture = detected_cmd
            gesture_start_time = time.time()
    else:
        # מצב נעול - שומרים על הפקודה האחרונה שאושרה
        final_cmd = current_stable_gesture
        if time.time() - lock_start_time > lock_duration: 
            is_locked = False

    # --- ביצוע פיזי מבוקר ---
    if final_cmd != last_final_cmd:
        if final_cmd == "LIE DOWN": 
            robot.action(13)
        elif final_cmd == "ATTENTION": 
            robot.action(1)
        # שים לב: אנחנו לא קוראים ל-stop() סתם כך כדי לא להרוס את הקימה
        last_final_cmd = final_cmd

    # --- תצוגת UI נקייה ---
    # פלט ידיים בפינות
    cv2.putText(img, f"L: {current_ui['Left']}", (20, 50), 1, 1.5, (255, 150, 0), 2)
    cv2.putText(img, f"R: {current_ui['Right']}", (w-220, 50), 1, 1.5, (0, 165, 255), 2)
    
    # סטטוס מרכזי
    if is_locked:
        msg = f"EXECUTING: {final_cmd}"
        color = (0, 255, 0)
    else:
        msg = f"WAITING: {detected_cmd}"
        color = (255, 255, 255)
    
    cv2.putText(img, msg, (w//2-150, h-40), 1, 1.8, color, 2)

    cv2.imshow("XGO Master Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
