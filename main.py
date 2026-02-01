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

print("System is running. Press 'q' to quit.")

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
            
            # צבע ירוק לידיים פתוחות/סגורות (פעולות מאושרות)
            if gesture in ["SIT", "STAND"]:
                colors[label] = (0, 255, 0)

            # ציור שלד היד על המסך
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # קבלת הפקודה הסופית מה-Gestures
    final_cmd = get_combo_action(current_ui["Left"], current_ui["Right"])
    
    # --- לוגיקת ביצוע פיזית מעודכנת ---
    if final_cmd != last_final_cmd:
        
        # 1. פקודת שכיבה (שתי ידיים סגורות)
        if final_cmd == "LIE DOWN":
            print(">>> Physical Action: LIE DOWN (13)")
            robot.action(13)
            
        # 2. פקודת עמידה (שתי ידיים פתוחות או לפחות אחת פתוחה)
        elif final_cmd in ["ATTENTION", "STAND"]:
            print(">>> Physical Action: STAND UP (1)")
            robot.action(1) 
            
        # 3. כל מצב אחר - עוצרים תנועה פיזית (הליכה/סיבוב) אבל לא "תוקעים" את העמידה
        else:
            print(f"Displaying: {final_cmd} (No physical move)")
            # עצירה רק אם הכלב היה באמצע תנועה כמו הליכה
            robot.stop()

        last_final_cmd = final_cmd

    # --- ממשק משתמש על המסך ---
    # רקע כהה לטקסט
    cv2.rectangle(img, (10, 10), (320, 160), (40, 40, 40), -1)
    
    cv2.putText(img, f"Left Hand: {current_ui['Left']}", (20, 50), 1, 1.5, colors['Left'], 2)
    cv2.putText(img, f"Right Hand: {current_ui['Right']}", (20, 90), 1, 1.5, colors['Right'], 2)
    
    # הצגת הפקודה הסופית בצבע בולט
    cmd_color = (0, 255, 0) if final_cmd in ["LIE DOWN", "ATTENTION"] else (255, 255, 255)
    cv2.putText(img, f"ROBOT: {final_cmd}", (20, 140), 1, 2, cmd_color, 3)

    cv2.imshow("XGO Control Center", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
