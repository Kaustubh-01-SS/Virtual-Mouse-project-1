import cv2
import time
import pyautogui
import subprocess
from hand_tracking import HandTracker
from gesture_control import GestureController

# Initialize camera with error handling
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# Check if camera opened successfully
if not cap.isOpened():
    print("ERROR: Cannot open camera. Check if camera is connected.")
    exit(1)

tracker = HandTracker()
gesture = GestureController()

# Gesture state machine
gesture_mode = None

# Gesture parameters
click_delay = 0.3
last_left_time = 0
last_right_time = 0
prev_fingers_y = None
scroll_threshold = 10
scroll_amount = 500
last_alt_tab_time = 0
alt_tab_delay = 0.5  # Delay between Alt+Tab triggers

# Swipe detection parameters
prev_hand_x = None
swipe_threshold = 50  # Minimum horizontal distance to trigger swipe
last_swipe_time = 0
swipe_delay = 0.5  # Delay between swipes

# Tab/App switching parameters
current_tab_index = 0
tab_switch_direction = None  # 'left' or 'right'
last_tab_switch_time = 0
tab_switch_delay = 0.6  # Delay between tab switches
hand_x_velocity_threshold = 5  # Slow movement velocity threshold
tab_list = []  # List of open windows

# FPS tracking
fps_time = time.time()
fps_count = 0
current_fps = 0

print("===== GESTURE MOUSE CONTROL v2.0 =====")
print("✓ Index STRAIGHT and all other fingers down  → MOVE")
print("✓ Only INDEX+MIDDLE finger UP → LEFT CLICK")
print("✓ Only MIDDLE+RING finger UP → RIGHT CLICK")
print("✓ Index + Middle + Thumb STRAIGHT → DRAG MODE (Hold Click)")
print("✓ All 5 Fingers UP + Move hand UP → SELECT NEXT APP")
print("✓ All 5 Fingers UP + Move hand DOWN → SELECT PREVIOUS APP")
print("✓ All 5 Finger tips joint together + Wave UP → SCROLL DOWN")
print("✓ All 5 Finger tips joint together + Wave DOWN → SCROLL UP")
print("✓ Press ESC to EXIT")
print("=======================================")

while True:
    success, frame = cap.read()
    if not success:
        print("ERROR: Failed to read frame from camera")
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    # ========== FPS COUNTER ==========
    fps_count += 1
    if time.time() - fps_time > 1:
        current_fps = fps_count
        fps_count = 0
        fps_time = time.time()

    # ========== CONTROL REGION ==========
    margin = 100
    region = (margin, margin, w - margin, h - margin)
    cv2.rectangle(frame, (region[0], region[1]), (region[2], region[3]), (100, 200, 100), 2)
    cv2.putText(frame, "CONTROL REGION", (region[0] + 10, region[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 100), 1)

    frame, landmarks, hand_type = tracker.detect_hands(frame)

    # Initialize finger state variables
    thumb_straight = False
    thumb_extended = False
    index_straight = False
    middle_straight = False
    ring_straight = False
    pinky_straight = False
    all_fingers_up = False

    # ========== STATUS PANEL ==========
    hand_status = "✓ HAND DETECTED" if landmarks and len(landmarks) >= 21 else "○ WAITING FOR HAND"
    status_color = (0, 255, 0) if landmarks and len(landmarks) >= 21 else (100, 100, 100)
    cv2.putText(frame, hand_status, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

    # Debug: Show thumb state when hand is detected
    if landmarks and len(landmarks) >= 21:
        thumb_state = f"Thumb: {'↑' if thumb_straight else '↓'} {'◆ext' if thumb_extended else '·fold'}"
        thumb_color = (100, 50, 255) if (thumb_straight and thumb_extended) else (150, 150, 150)
        cv2.putText(frame, thumb_state, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, thumb_color, 1)

    cv2.putText(frame, f"FPS: {current_fps}", (w - 150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # ========== GESTURE DETECTION ==========
    if landmarks and len(landmarks) >= 21:
        # Extract finger positions - landmarks are tuples (id, x, y)
        thumb_tip = landmarks[4]      # (id, x, y)
        thumb_pip = landmarks[3]
        index_tip = landmarks[8]
        index_pip = landmarks[6]
        middle_tip = landmarks[12]
        middle_pip = landmarks[10]
        ring_tip = landmarks[16]
        ring_pip = landmarks[14]
        pinky_tip = landmarks[20]
        pinky_pip = landmarks[18]

        # Finger straightness: if tip Y < pip Y, finger is up (Y increases downward)
        thumb_straight = thumb_tip[2] < thumb_pip[2]
        index_straight = index_tip[2] < index_pip[2]
        middle_straight = middle_tip[2] < middle_pip[2]
        ring_straight = ring_tip[2] < ring_pip[2]
        pinky_straight = pinky_tip[2] < pinky_pip[2]

        # Enhanced thumb detection: check if thumb is truly extended (distance from middle base)
        # distance from thumb tip to middle finger PIP (palm reference point)
        thumb_to_middle_dist = ((thumb_tip[1] - middle_pip[1])**2 + (thumb_tip[2] - middle_pip[2])**2)**0.5
        thumb_extended = thumb_to_middle_dist > 50  # Threshold for thumb being spread out
        
        all_fingers_up = thumb_straight and index_straight and middle_straight and ring_straight and pinky_straight

        # Visualize all fingertips
        for landmark in landmarks:
            if landmark[0] in [4, 8, 12, 16, 20]:  # Finger tips
                cv2.circle(frame, (landmark[1], landmark[2]), 5, (200, 200, 200), -1)

        # ===== GESTURE 0: DRAG MODE (Index + Middle + Thumb straight & extended) =====
        if index_straight and middle_straight and thumb_straight and thumb_extended and not all_fingers_up:
            gesture.start_drag()
            gesture.move_mouse(index_tip[1], index_tip[2], region)
            gesture_mode = "DRAG"
            cv2.circle(frame, (index_tip[1], index_tip[2]), 12, (100, 50, 255), -1)
            cv2.circle(frame, (thumb_tip[1], thumb_tip[2]), 8, (100, 50, 255), -1)  # Highlight thumb
            cv2.putText(frame, "✋ DRAG MODE", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (100, 50, 255), 3)

        # ===== GESTURE 1: MOVE (Index straight, all other fingers down) =====
        elif index_straight and not middle_straight and not ring_straight and not pinky_straight and not all_fingers_up:
            gesture.end_drag()  # End drag if transitioning to move
            gesture.move_mouse(index_tip[1], index_tip[2], region)
            gesture_mode = "MOVE"
            cv2.circle(frame, (index_tip[1], index_tip[2]), 12, (0, 255, 0), -1)
            cv2.putText(frame, "➜ MOVE", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

        # ===== GESTURE 2: LEFT CLICK (Only INDEX+MIDDLE finger UP) =====
        elif index_straight and middle_straight and not ring_straight and not pinky_straight and not all_fingers_up:
            gesture.end_drag()  # End drag before left click
            if time.time() - last_left_time > click_delay:
                gesture.left_click()
                last_left_time = time.time()
            gesture_mode = "LEFT_CLICK"
            cv2.putText(frame, "◆ LEFT CLICK ◆", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 100, 0), 3)

        # ===== GESTURE 3: RIGHT CLICK (Only MIDDLE+RING finger UP) =====
        elif middle_straight and ring_straight and not index_straight and not pinky_straight and not all_fingers_up:
            gesture.end_drag()  # End drag before right click
            if time.time() - last_right_time > click_delay:
                gesture.right_click()
                last_right_time = time.time()
            gesture_mode = "RIGHT_CLICK"
            cv2.putText(frame, "◆ RIGHT CLICK ◆", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (100, 100, 255), 3)

        # ===== GESTURE 4: TAB/APP SWITCHER & SCROLL (All 5 fingers straight/up) =====
        elif all_fingers_up:
            # Check if all 5 fingertips are close together (joint) by checking distances
            finger_tips = [thumb_tip, index_tip, middle_tip, ring_tip, pinky_tip]
            # Calculate average distance between fingertips to detect if they're joint
            distances = []
            for i in range(len(finger_tips)):
                for j in range(i+1, len(finger_tips)):
                    dist = ((finger_tips[i][1] - finger_tips[j][1])**2 + (finger_tips[i][2] - finger_tips[j][2])**2)**0.5
                    distances.append(dist)
            avg_distance = sum(distances) / len(distances) if distances else 0
            fingers_joint = avg_distance < 80  # Threshold for fingertips being close together
            
            # Use middle finger tip as reference point for hand position
            hand_x = middle_tip[1]
            avg_fingers_y = (thumb_tip[2] + index_tip[2] + middle_tip[2] + ring_tip[2] + pinky_tip[2]) / 5
            
            # Calculate both movements to determine dominance
            if prev_hand_x is not None and prev_fingers_y is not None:
                hand_x_delta = hand_x - prev_hand_x  # positive = moved right, negative = moved left
                fingers_delta = prev_fingers_y - avg_fingers_y  # positive = fingers moved up
                
                abs_x_delta = abs(hand_x_delta)
                abs_y_delta = abs(fingers_delta)
                
                # Calculate velocity for slow movement detection
                hand_y_velocity = abs(fingers_delta)
                
                # Determine movement dominance (must be at least 2x stronger in one direction)
                horizontal_dominant = abs_x_delta > abs_y_delta * 2 and abs_x_delta > swipe_threshold
                vertical_dominant = abs_y_delta > abs_x_delta * 2 and abs_y_delta > scroll_threshold
                
                # ===== TAB/APP SWITCHER (Vertical movement with 5 fingers up, NOT joint) =====
                if vertical_dominant and not fingers_joint and time.time() - last_tab_switch_time > tab_switch_delay:
                    # Movement UP = Next App (Alt+Tab)
                    if fingers_delta > scroll_threshold:
                        pyautogui.hotkey('alt', 'tab')
                        last_tab_switch_time = time.time()
                        current_tab_index += 1
                        cv2.putText(frame, "⬆ SELECT NEXT APP", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 165, 0), 3)
                        cv2.putText(frame, f"App Index: {current_tab_index}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)
                    # Movement DOWN = Previous App (Alt+Shift+Tab)
                    elif fingers_delta < -scroll_threshold:
                        pyautogui.hotkey('alt', 'shift', 'tab')
                        last_tab_switch_time = time.time()
                        current_tab_index = max(0, current_tab_index - 1)
                        cv2.putText(frame, "⬇ SELECT PREVIOUS APP", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 165, 0), 3)
                        cv2.putText(frame, f"App Index: {current_tab_index}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)
                
                # ===== SCROLL DETECTION (Finger tips joint + vertical wave) =====
                elif vertical_dominant and fingers_joint:
                    # Wave UP = Scroll Down
                    if fingers_delta > scroll_threshold:
                        gesture.scroll(-scroll_amount)  # Scroll down
                        cv2.putText(frame, "⬇ SCROLL DOWN (Wave UP)", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 200, 255), 3)
                    # Wave DOWN = Scroll Up
                    elif fingers_delta < -scroll_threshold:
                        gesture.scroll(scroll_amount)  # Scroll up
                        cv2.putText(frame, "⬆ SCROLL UP (Wave DOWN)", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 200, 255), 3)
                
                elif fingers_joint:
                    cv2.putText(frame, "☰ SCROLL READY (Joint tips - Wave up/down)", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 150, 200), 3)
                else:
                    cv2.putText(frame, "☰ APP SWITCHER READY (Move hand up/down)", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 150, 200), 3)
            
            elif prev_hand_x is not None or prev_fingers_y is not None:
                if fingers_joint:
                    cv2.putText(frame, "☰ SCROLL READY (Joint tips - Wave up/down)", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 150, 200), 3)
                else:
                    cv2.putText(frame, "☰ APP SWITCHER READY (Move hand up/down)", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 150, 200), 3)
            
            prev_hand_x = hand_x
            prev_fingers_y = avg_fingers_y
            gesture_mode = "TAB_SWITCHER/SCROLL"

        else:
            gesture.end_drag()  # End drag mode when no gesture detected
            gesture_mode = None
            prev_fingers_y = None
            prev_hand_x = None
            current_tab_index = 0  # Reset tab index when hand is closed

    else:
        gesture.end_drag()  # End drag when hand is not detected
        gesture_mode = None
        gesture_stability = 0
        prev_fingers_y = None
        prev_hand_x = None
        current_tab_index = 0  # Reset tab index when hand is not detected
        cv2.putText(frame, "Position your hand in the control region", (20, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)

    # ========== DISPLAY & CONTROLS ==========
    cv2.imshow("Gesture Mouse Control", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        print("\n✓ Exiting...")
        break

print("Gesture Mouse stopped.")
cap.release()
cv2.destroyAllWindows()