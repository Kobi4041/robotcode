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
            
            if gesture == "SPIN": colors[label] = (255, 0, 255)
            elif gesture == "COME": colors[label] = (255, 255, 0)
            elif gesture in ["SIT", "STAND"]: colors[label] = (0, 255, 0)

            if label == "Right" and gesture == "SPIN" and len(finger_history) > 1:
                for j in range(1, len(finger_history)):
                    p1 = (int(finger_history[j-1][0]*w), int(finger_history[j-1][1]*h))
                    p2 = (int(finger_history[j][0]*w), int(finger_history[j][1]*h))
                    cv2.line(img, p1, p2, (255, 0, 255), 3)

            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    final_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])
    
    # --- ביצוע פעולה פיזית (מסונן) ---
    if final_cmd != last_final_cmd:
        # כאן קורה השינוי: רק LIE DOWN עובר לרובוט
        if final_cmd == "LIE DOWN":
            print("Physical Action triggered: LIE DOWN")
            robot.action(13) 
        else:
            # כל פקודה אחרת (FOLLOW, SPINNING, וכו') - הרובוט עוצר פיזית
            print(f"Logic detected {final_cmd}, but physical robot is blocked.")
            robot.stop() 
            
        last_final_cmd = final_cmd

    # ממשק משתמש (נשאר מלא כדי שתראה מה מזוהה)
    cv2.rectangle(img, (10, 10), (300, 150), (40, 40, 40), -1)
    cv2.putText(img, f"L: {current_ui['Left']}", (20, 50), 1, 1.5, colors['Left'], 2)
    cv2.putText(img, f"R: {current_ui['Right']}", (20, 90), 1, 1.5, colors['Right'], 2)
    cv2.putText(img, f"CMD: {final_cmd}", (20, 130), 1, 1.8, (255, 255, 255), 2)

    cv2.imshow("XGO Lie Down ONLY Mode", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
