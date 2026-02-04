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
        def action(self, cmd_id): print(f"ACTION: {cmd_id}")
        def stop(self): pass
    robot = XGO_Mock()

# --- משתני שליטה בזמן ---
gesture_start_time = 0
current_stable_gesture = "READY"
required_duration = 2.0  # שתי שניות רצוף
is_locked = False        # האם הרובוט כרגע בביצוע פעולה נעולה

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

    # פלט משולב נוכחי מהמצלמה
    detected_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])

    # --- לוגיקת השהיה (2 שניות) ונעילה ---
    if not is_locked:
        if detected_cmd == current_stable_gesture and detected_cmd != "READY":
            # אם המחווה יציבה, נבדוק כמה זמן עבר
            elapsed = time.time() - gesture_start_time
            
            # הצגת "מד טעינה" ויזואלי
            progress = min(elapsed / required_duration, 1.0)
            cv2.rectangle(img, (w//2-100, h-100), (w//2-100 + int(200*progress), h-80), (0, 255, 255), -1)
            
            if elapsed >= required_duration:
                final_cmd = detected_cmd
                is_locked = True # נועלים את המצב
                lock_start_time = time.time()
        else:
            # אם המחווה השתנתה, מאפסים את הטיימר
            current_stable_gesture = detected_cmd
            gesture_start_time = time.time()
            final_cmd = "READY"
    else:
        # הרובוט בתוך פעולה (נעול)
        final_cmd = current_stable_gesture
        # נשחרר את הנעילה אחרי 3 שניות (כדי שיוכל לקבל פקודה חדשה)
        if time.time() - lock_start_time > 3.0: 
            is_locked = False

    # --- ביצוע פיזי ---
    if final_cmd != last_final_cmd:
        if final_cmd == "LIE DOWN": robot.action(13)
        elif final_cmd == "ATTENTION": robot.action(1)
        elif final_cmd == "READY": robot.stop()
        last_final_cmd = final_cmd

    # --- תצוגת UI ---
    # פלט יד שמאל
    cv2.putText(img, f"LEFT: {current_ui['Left']}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 150, 0), 2)
    # פלט יד ימין
    cv2.putText(img, f"RIGHT: {current_ui['Right']}", (w-200, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
    
    # מצב רובוט וסטטוס נעילה
    status_text = f"EXECUTING: {final_cmd}" if is_locked else f"STABILIZING: {detected_cmd}"
    color = (0, 255, 0) if is_locked else (255, 255, 255)
    cv2.putText(img, status_text, (w//2-120, h-40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    cv2.imshow("XGO Locked Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
