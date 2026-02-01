import cv2
import mediapipe as mp
from gestures import count_fingers, get_combo_action, finger_history
from xgolib import XGO 

# אתחול הרובוט
robot = XGO(port='/dev/ttyAMA0') 

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

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
    colors = {"Left": (200, 200, 200), "Right": (200, 200, 200)}

    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            label = results.multi_handedness[i].classification[0].label
            gesture = count_fingers(hand_lms, label)
            current_ui[label] = gesture
            
            # צבעים לפי מצב
            if gesture == "SPIN": colors[label] = (255, 0, 255)
            elif gesture == "COME": colors[label] = (255, 255, 0)
            elif gesture in ["SIT", "STAND"]: colors[label] = (0, 255, 0)

            # ציור שלד היד
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # זיהוי הפקודה הסופית
    final_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])
    
    # --- ביצוע פעולה פיזית (עכשיו גם ATTENTION וגם LIE DOWN) ---
    if final_cmd != last_final_cmd:
        if final_cmd == "LIE DOWN":
            print("Physical Action: LIE DOWN (13)")
            robot.action(13) 
            
        elif final_cmd == "ATTENTION":
            print("Physical Action: ATTENTION/STAND (1)")
            robot.action(1)  # פקודת עמידה דרוכה
            
        else:
            # כל שאר הפקודות עדיין חסומות פיזית (רק תצוגה)
            print(f"Logic detected {final_cmd}, no physical move.")
            robot.stop() 
            
        last_final_cmd = final_cmd

    # ממשק משתמש
    cv2.rectangle(img, (10, 10), (300, 150), (40, 40, 40), -1)
    cv2.putText(img, f"L: {current_ui['Left']}", (20, 50), 1, 1.5, colors['Left'], 2)
    cv2.putText(img, f"R: {current_ui['Right']}", (20, 90), 1, 1.5, colors['Right'], 2)
    cv2.putText(img, f"CMD: {final_cmd}", (20, 130), 1, 1.8, (255, 255, 255), 2)

    cv2.imshow("XGO Control - LieDown & Attention", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
