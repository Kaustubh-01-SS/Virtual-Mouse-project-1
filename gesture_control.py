import numpy as np
import pyautogui
import time

class GestureController:

    def __init__(self):
        self.screen_w, self.screen_h = pyautogui.size()

        # smoothing (0.0 = very smooth, 1.0 = no smoothing)
        self.prev_x = 0
        self.prev_y = 0
        self.smoothing = 0.3  # High smoothing for stable cursor

        # click delay to prevent multiple triggers
        self.last_left = 0
        self.last_right = 0
        self.last_scroll = 0
        self.delay = 0.3
        self.scroll_delay = 0.08  # Faster smooth scrolling
        
        # Drag mode tracking
        self.is_dragging = False

    def move_mouse(self, x, y, region):
        """Move cursor based on hand position within control region"""
        x1, y1, x2, y2 = region

        # Map hand position from control region to full screen
        # This naturally creates the "gain" effect
        screen_x = np.interp(x, [x1, x2], [0, self.screen_w])
        screen_y = np.interp(y, [y1, y2], [0, self.screen_h])

        # EMA smoothing filter for stable cursor movement
        curr_x = self.prev_x + (screen_x - self.prev_x) * self.smoothing
        curr_y = self.prev_y + (screen_y - self.prev_y) * self.smoothing

        # Clamp to screen boundaries
        curr_x = max(0, min(curr_x, self.screen_w - 1))
        curr_y = max(0, min(curr_y, self.screen_h - 1))

        # Move cursor
        pyautogui.moveTo(int(curr_x), int(curr_y))

        # Store for next frame
        self.prev_x = curr_x
        self.prev_y = curr_y

    def left_click(self):
        """Perform left mouse click with debounce"""
        if time.time() - self.last_left > self.delay:
            pyautogui.click()
            self.last_left = time.time()

    def right_click(self):
        """Perform right mouse click with debounce"""
        if time.time() - self.last_right > self.delay:
            pyautogui.rightClick()
            self.last_right = time.time()

    def scroll(self, amount):
        """Scroll mouse wheel with debounce. Positive = up, negative = down."""
        if time.time() - self.last_scroll > self.scroll_delay:
            pyautogui.scroll(int(amount))
            self.last_scroll = time.time()

    def start_drag(self):
        """Start drag mode by pressing left mouse button"""
        if not self.is_dragging:
            pyautogui.mouseDown()
            self.is_dragging = True

    def end_drag(self):
        """End drag mode by releasing left mouse button"""
        if self.is_dragging:
            pyautogui.mouseUp()
            self.is_dragging = False