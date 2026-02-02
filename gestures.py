import math

# היסטוריית תנועה
finger_history = []
come_here_history = []

def detect_circle(hand_lms):
    global finger_history
    pos = (hand_lms.landmark[8].x, hand_lms.landmark[8].y)
    finger_history.append(pos)
    if len(finger_history) > 10: finger_history.pop(0)
    if len(finger_history) < 10: return False

    min_x = min([p[0] for p in finger_history]); max_x = max([p[0] for p in finger_history])
    min_y = min([p[1] for p in finger_history]); max_y = max([p[1] for p in finger_history])
    return (max_x - min_x) > 0.05 and (max_y - min_y) > 0.05

def detect_come_here(total_fingers):
    global come_here_history
    come_here_history.append(total_fingers)
    if len(come_here_history) > 20: come_here_history.pop(0)
    return max(come_here_history) >= 4 and min(come_here_history) <= 1

def count_fingers(hand_lms, hand_type):
    fingers = []
    # זיהוי אגודל (מרחק מהזרת)
    thumb_tip = hand_lms.landmark[4]
    pinky_base = hand_lms.landmark[17]
    dist = math.sqrt((thumb_tip.x - pinky_base.x)**2 + (thumb_tip.y - pinky_base.y)**2)
    fingers.append(1 if dist > 0.18 else 0)

    # 4 אצבעות
    for tip in [8, 12, 16, 20]:
        fingers.append(1 if hand_lms.landmark[tip].y < hand_lms.landmark[tip-2].y else 0)
    
    total = fingers.count(1)

    # מחוות תנועה - רק ביד ימין (ללא DANCE למניעת בלבול)
    if hand_type == "Right":
        if detect_come_here(total): return "COME"
        if fingers[1] == 1 and total <= 2:
            if detect_circle(hand_lms): return "SPIN"

    # מחוות סטטיות
    if total == 0: return "SIT"
    if total == 5: return "STAND"
    if total == 2: return "DANCE"
    if total == 1: return "HELLO"

    return "UNKNOWN"

def get_combo_action(left_gesture, right_gesture):
    if right_gesture == "COME": return "FOLLOW"
    if right_gesture == "SPIN": return "SPINNING"
    if left_gesture == "SIT" and right_gesture == "SIT": return "LIE DOWN"
    if left_gesture == "STAND" and right_gesture == "STAND": return "ATTENTION"
    return "UNKNOWN"
