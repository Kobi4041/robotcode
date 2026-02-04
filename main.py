import cv2
import mediapipe as mp
import time
from gestures import count_fingers

# --- אתחול עם ריסט עמוק ---
print(">>> Starting Reset Sequence...")
robot = None
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0') 
    time.sleep(1.0)
    
    # ריסט תוכנתי לרובוט
    robot.reset() 
    print(">>> Robot Reset Command Sent!")
    time.sleep(1.0)
    
except Exception as e:
    print(f">>> Could not reset robot: {e}")

# --- פתיחת מצלמה ---
cap = cv2.VideoCapture(0)
# הגדרת רזולוציה נמוכה יותר כדי למנוע תקיעה ב-Pi
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

last_action = 1 # 1=עמידה, 13=שכיבה

while cap.isOpened():
    success, img = cap.read()
    if not success:
        print(">>> Camera Error")
        break
        
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    gesture = "None"
    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            if results.multi_handedness[i].classification[0].label == "Right":
                gesture = count_fingers(hand_lms, "Right")
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # ביצוע פקודות
    if robot:
        if gesture == "SIT" and last_action != 13:
            robot.action(13)
            last_action = 13
            print(">>> Action: Sitting")
        elif gesture == "STAND" and last_action != 1:
            robot.action(1)
            last_action = 1
            print(">>> Action: Standing")

    # תצוגה
    cv2.putText(img, f"Right Hand: {gesture}", (10, 30), 1, 1.5, (0, 255, 0), 2)
    cv2.imshow("XGO Reset Mode", img)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
