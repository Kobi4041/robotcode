import cv2
import mediapipe as mp
from gestures import count_fingers 
import time

# --- Robot Initialization ---
# Attempt to connect to the physical XGO robot; otherwise, use a Mock class for simulation
try:
    from xgolib import XGO
    robot = XGO(port='/dev/ttyAMA0')
except:
    # Mock class simulates robot responses in the terminal when hardware is not present
    class XGO_Mock:
        def action(self, cmd_id): print(f"[SIM] ACTION: {cmd_id}")
        def stop(self): print("[SIM] STOP")
        def reset(self): print("[SIM] RESET")
        def turn(self, speed): print(f"[SIM] TURN: {speed} °/s")
        def move(self, direction, step): print(f"[SIM] MOVE: {direction} {step}")
        def translation(self, axis, val): print(f"[SIM] TRANS: {axis} {val}")
        def attitude(self, axis, val): print(f"[SIM] ATTITUDE: {axis} {val}")
        def mark_time(self, data): print(f"[SIM] MARK_TIME: {data}mm")
        def pace(self, mode): print(f"[SIM] PACE: {mode}")
    robot = XGO_Mock()

# --- Control Variables ---
# Used for managing states, preventing command duplication, and handling autonomous timers
confirmed_cmd = "STAND"
last_final_cmd = ""
is_turning_360 = False
turn_start_time = 0

# --- MediaPipe Setup ---
# Initialize camera and Hand tracking solution
cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

# --- Main Logic Loop ---
while cap.isOpened():
    success, img = cap.read()
    if not success: break
    
    # Mirror image for a more natural user experience
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    current_time = time.time()
    raw_cmd = "NONE"
    
    # 1. Gesture Recognition
    # Process detected landmarks and identify the command from the Right hand
    if results.multi_hand_landmarks:
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            if results.multi_handedness[i].classification[0].label == "Right":
                raw_cmd = count_fingers(hand_lms, "Right")
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)

    # 2. Command Persistence
    # Update the confirmed command only when a new valid gesture is detected
    if raw_cmd != "NONE":
        confirmed_cmd = raw_cmd

    # 3. Autonomous 360 Degree Turn Logic
    # Handles the rotation timer to ensure a full circle without blocking the camera feed
    if is_turning_360:
        # Based on speed, roughly 4.35 seconds are needed for a full circle
        if current_time - turn_start_time > 4.35:
            robot.turn(0)
            robot.mark_time(0)
            is_turning_360 = False
            confirmed_cmd = "STAND" # Reset state to Stand after completion
            print("System: Finished 360 degree turn.")

    # 4. Robot Command Execution
    # Commands are sent only when the confirmed command changes
    if robot and confirmed_cmd != last_final_cmd:
        
        # Safety halt before executing a new static posture (skipped if turning)
        if not is_turning_360:
            robot.stop() 
            
            # Map confirmed commands to specific robot SDK methods
            if confirmed_cmd == "FOLLOW":
                robot.move('x', 12) # Walk forward

            elif confirmed_cmd == "STAND":
                robot.reset() # Return to default standing position

            elif confirmed_cmd == "REVERSE":
                robot.move('x', -12) # Walk backward

            elif confirmed_cmd == "SIT":
                # Adjusted posture for a 'Sitting' position
                robot.translation(['z', 'x'], [75, -35])
                robot.attitude('p', -15)

            elif confirmed_cmd == "HELLO":
                robot.action(13) # Pre-programmed waving action

            elif confirmed_cmd == "SPINNING":
                # Start an autonomous 360 degree spin
                print("System: Starting 360 degree turn...")
                robot.pace('normal')
                robot.mark_time(20) # Lift legs higher for better rotation
                robot.turn(93)      # Rotation speed in degrees per second
                turn_start_time = current_time
                is_turning_360 = True
            
            elif confirmed_cmd == "STOP":
                robot.move('x', 0) # Halt all movement

            last_final_cmd = confirmed_cmd

    # --- UI Display ---
    # Overlay the current robot status and command on the video feed
    status_text = f"CMD: {confirmed_cmd}"
    if is_turning_360: 
        status_text += " (TURNING...)"
    
    cv2.putText(img, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)
    cv2.imshow("XGO Control", img)
    
    # Exit loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break

# Cleanup resources
cap.release()
cv2.destroyAllWindows()
