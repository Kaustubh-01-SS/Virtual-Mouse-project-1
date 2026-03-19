import cv2
import sys

print("Testing camera access...\n")

# Try different camera indices
for i in range(5):
    print(f"Testing camera index {i}...")
    cap = cv2.VideoCapture(i)
    
    if cap.isOpened():
        print(f"  ✓ Camera {i} opened")
        success, frame = cap.read()
        if success:
            print(f"  ✓ Camera {i} can read frames!")
            print(f"    Frame size: {frame.shape}")
            cap.release()
            print(f"\n✓ SUCCESS: Use VideoCapture({i}) in main.py")
            sys.exit(0)
        else:
            print(f"  ✗ Camera {i} opened but cannot read frames (driver error)")
            cap.release()
    else:
        print(f"  ✗ Camera {i} not available")

print("\n✗ No working camera found!")
print("\nSOLUTIONS:")
print("1. Connect a USB camera or enable the built-in camera")
print("2. Install/update camera drivers")
print("3. Check Device Manager for camera conflicts")
print("4. For testing without hardware, use a virtual camera app")
