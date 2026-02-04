import cv2
import mediapipe as mp
import time
from gestures import count_fingers

# --- אתחול רובוט ---
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
    IS_SIM = False
    time.sleep(0.5)
    robot.action(1) # עמידה ראשונית
    print(">>> XGO Ready: Right hand controls stand/sit")
except (ImportError, ModuleNotFoundError):
    IS_SIM = True
    class XGO_Mock:
        def action(self, cmd_id): print(f"ROBOT ACTION: {cmd_id}")
    robot = XGO_Mock()

# --- משתני שליטה ---
last_executed_action = 1 # 1 = עמידה, 13 = שכיבה
required_duration = 1.0  # זמן אישור קצר ומהיר (שנייה אחת)
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
            
            # מתייחסים רק ליד ימין
            if label == "Right":
                right_hand_status = count_fingers(hand_lms, "Right")
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
                break # מצאנו את ימין, לא צריך להמשיך בלולאה

    # תרגום מצב היד לפקודת רובוט
    target_action = None
    if right_hand_status == "SIT": # אגרוף סגור
        target_action = 13
    elif right_hand_status == "STAND": # יד פתוחה
        target_action = 1

    # --- לוגיקת אישור וביצוע ---
    if target_action is not None:
        if target_action == current_stable_gesture:
            elapsed = time.time() - gesture_start_time
            
            # מד טעינה קטן מעל היד
            progress = min(elapsed / required_duration, 1.0)
            cv2.rectangle(img, (20, h-60), (int(20 + (200 * progress)), h-40), (0, 255, 0), -1)
            
            if elapsed >= required_duration and target_action != last_executed_action:
                robot.action(target_action)
                last_executed_action = target_action
        else:
            current_stable_gesture = target_action
            gesture_start_time = time.time()
    else:
        current_stable_gesture = "None"

    # --- תצוגת UI מינימליסטית ---
    mode_text = "STANDING" if last_executed_action == 1 else "SITTING"
    status_color = (0, 255, 0) if last_executed_action == 1 else (0, 0, 255)
    
    cv2.putText(img, f"RIGHT HAND: {right_hand_status}", (20, 50), 1, 1.5, (255, 255, 255), 2)
    cv2.putText(img, f"ROBOT MODE: {mode_text}", (20, 100), 1, 2, status_color, 3)

    cv2.imshow("XGO Right Hand Only", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
