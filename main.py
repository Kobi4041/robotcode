import cv2
import mediapipe as mp
import time
from gestures import count_fingers # משתמש בקובץ שלך

# --- שלב 1: חיבור וקימה חובה ---
print(">>> Connecting to robot...")
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0') 
    
    # הסוד לקימה יציבה: לתת לו רגע ואז פקודת עמידה ברורה
    time.sleep(1.5)
    robot.action(1) # עמידה
    print(">>> ROBOT STANDING")
except Exception as e:
    print(f">>> Robot error: {e}")
    robot = None

# --- שלב 2: פתיחת מצלמה ---
print(">>> Opening Camera...")
cap = cv2.VideoCapture(0)

# אם המצלמה לא נפתחת, זה יגיד לך מיד
if not cap.isOpened():
    print(">>> ERROR: Cannot open camera. Check if another script is using it.")
    exit()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

last_action = "STAND" # מתחילים במצב עמידה

# --- שלב 3: לולאת עבודה ---
while True:
    success, img = cap.read()
    if not success: break
    
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    gesture = "None"
    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            # זיהוי לפי הקוד שלך (יד ימין בלבד)
            label = results.multi_handedness[i].classification[0].label
            if label == "Right":
                gesture = count_fingers(hand_lms, "Right")
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # ביצוע הפעולות שביקשת
    if robot:
        if gesture == "SIT" and last_action != "SIT":
            robot.action(13) # שכיבה
            last_action = "SIT"
            print(">>> Doing: SIT")
        elif gesture == "STAND" and last_action != "STAND":
            robot.action(1) # עמידה
            last_action = "STAND"
            print(">>> Doing: STAND")

    # הצגת המצב על המסך
    cv2.putText(img, f"Gesture: {gesture}", (10, 50), 1, 2, (0, 255, 0), 2)
    cv2.imshow("XGO Simple Control", img)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
