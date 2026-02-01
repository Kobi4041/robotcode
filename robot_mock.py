import cv2
import mediapipe as mp
from gestures import count_fingers, get_combo_action
from xgolib import XGO # הייבוא האמיתי ששולט בסרוואים

# אתחול הכלב האמיתי - החיבור הטורי ב-CM4
dog = XGO(port='/dev/ttyAMA0') 

cap = cv2.VideoCapture(0)
# הגדרת רזולוציה נמוכה יותר כדי שה-PI יעבוד מהר יותר
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=2)

last_command = ""

while cap.isOpened():
    success, img = cap.read()
    if not success: break

    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    current_ui = {"Left": "None", "Right": "None"}

    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            label = results.multi_handedness[i].classification[0].label
            gesture = count_fingers(hand_lms, label)
            current_ui[label] = gesture

    # זיהוי הפעולה מה-gestures.py שלך (מחזיר "LIE DOWN" אם שתי ידיים ב-SIT)
    final_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])
    
    # ביצוע הפעולה הפיזית על הכלב
    if final_cmd != last_command:
        if final_cmd == "LIE DOWN":
            print("Physical Action: Lowering body...")
            dog.action(13)  # קוד 13 ב-XGO זה שכיבה (Prone/Lie Down)
        elif final_cmd == "STAND":
            dog.action(1)   # חזרה לעמידה רגילה
        
        last_command = final_cmd

    # תצוגה על המסך כדי שתדע מה הכלב חושב
    cv2.putText(img, f"ROBOT STATUS: {final_cmd}", (20, 50), 1, 1.5, (0, 255, 0), 2)
    cv2.imshow("XGO Hardware Control", img)
    
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
