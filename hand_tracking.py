import cv2
import mediapipe as mp
import numpy as np

class HandTracker:

    def __init__(self):
        self.mp_hands = mp.tasks.vision.HandLandmarker
        self.BaseOptions = mp.tasks.BaseOptions
        self.HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
        self.VisionRunningMode = mp.tasks.vision.RunningMode

        options = self.HandLandmarkerOptions(
            base_options=self.BaseOptions(model_asset_path="hand_landmarker.task"),
            running_mode=self.VisionRunningMode.IMAGE,
            num_hands=1
        )

        self.detector = self.mp_hands.create_from_options(options)

    def detect_hands(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.detector.detect(mp_image)

        landmarks_list = []
        hand_type = None

        if result.hand_landmarks:
            for hand in result.hand_landmarks:
                h, w, _ = frame.shape
                for id, lm in enumerate(hand):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    landmarks_list.append((id, cx, cy))
        
        if result.handedness and len(result.handedness) > 0:
            try:
                # Access the first hand's classification
                hand_type = result.handedness[0][0].category_name
            except (IndexError, AttributeError):
                hand_type = None

        return frame, landmarks_list, hand_type