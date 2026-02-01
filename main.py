import cv2
import mediapipe as mp
from gestures import count_fingers, get_combo_action
from xgolib import XGO  # החיבור לרובוט הפיזי

# אתחול הרובוט
dog = XGO(port='/dev/ttyAMA0') 

cap = cv2.VideoCapture(0)
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

    # זיהוי הפעולה מה-gestures.py (שתי ידיים סגורות = "LIE DOWN")
    final_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])
    
    # --- לוגיקת הביצוע שביקשת ---
    if final_cmd != last_command:
        # הפעולה היחידה שתתבצע פיזית
        if final_cmd == "LIE DOWN":
            print("Executing Physical Action: SIT/LIE DOWN")
            dog.action(13) 
        else:
            # כל פקודה אחרת (FOLLOW, STAND וכו') - רק הדפסה, בלי תנועה ברובוט
            print(f"Detected {final_cmd}, but ignoring physical movement.")
            # אנחנו עוצרים את הכלב כדי שלא ימשיך פעולות קודמות בטעות
            dog.stop() 
            
        last_command = final_cmd

    # --- תצוגה על המסך (תמיד מציג מה מזוהה) ---
    cv2.putText(img, f"CMD: {final_cmd}", (20, 50), 1, 2, (0, 255, 0), 2)
    cv2.putText(img, f"L: {current_ui['Left']}  R: {current_ui['Right']}", (20, 90), 1, 1.5, (255, 255, 255), 2)
    
    cv2.imshow("XGO Safe Control", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
