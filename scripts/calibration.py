import os
import time
import json
import shutil
import numpy as np
import cv2
from datetime import datetime
from brightness_transition import smooth_transition  # if needed, else you can remove this

# Paths relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "../data"))
PROFILE_PATH = os.path.join(DATA_DIR, "ambient_light_profile.json")
BACKLIGHT_PATH = '/sys/class/backlight/intel_backlight'

# Create data directory if not exists
os.makedirs(DATA_DIR, exist_ok=True)

def calibrate_camera():
    print("[🚀] Starting camera calibration...")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[❌] Webcam not available.")
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_EXPOSURE, -6)
    cap.set(cv2.CAP_PROP_CONTRAST, 50)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 100)

    usable_brightness = []
    frames_captured = 0
    max_attempts = 40

    while frames_captured < 10 and max_attempts > 0:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            max_attempts -= 1
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        flat = gray.flatten()
        lower = np.percentile(flat, 10)
        upper = np.percentile(flat, 90)
        trimmed = flat[(flat >= lower) & (flat <= upper)]

        if len(trimmed) > 0:
            usable_brightness.append(np.mean(trimmed))
            frames_captured += 1

        time.sleep(0.05)
        max_attempts -= 1

    cap.release()

    if not usable_brightness:
        print("[❌] No usable frame captured.")
        return None

    final_brightness = float(np.median(usable_brightness))
    print(f"[🧠] Ambient brightness (median of samples): {final_brightness:.2f}")

    profile = {
        "ambient_min": float(np.min(usable_brightness)),
        "ambient_max": float(np.max(usable_brightness)),
        "ambient_median": final_brightness,
        "camera_resolution": [320, 240],
        "fps_expected": 30,
        "timestamp": str(datetime.now())
    }

    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=4)

    print(f"[💾] Calibration profile saved to {PROFILE_PATH}")
    return profile


if __name__ == "__main__":
    calibrate_camera()

