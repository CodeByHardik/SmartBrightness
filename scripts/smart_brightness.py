import os
import shutil
import time
import json
import subprocess
import numpy as np
import cv2
from brightness_transition import smooth_transition  # Renamed 'transition.py' to 'brightness_transition.py'

# Paths relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "../data"))
PROFILE_PATH = os.path.join(DATA_DIR, "ambient_light_profile.json")  # Renamed 'camera_profile.json' to 'ambient_light_profile.json'
CALIBRATION_SCRIPT = os.path.join(BASE_DIR, "calibration.py")  # Renamed 'calibrate.py' to 'calibration.py'
BACKLIGHT_PATH = '/sys/class/backlight/intel_backlight'

# Ensure the necessary directories and files exist
os.makedirs(DATA_DIR, exist_ok=True)

# Function to create a default camera profile if not found
def create_default_profile():
    default_profile = {
        "ambient_min": 40,
        "ambient_max": 170
    }
    try:
        with open(PROFILE_PATH, "w") as f:
            json.dump(default_profile, f)
        print(f"[📊] Default calibration profile created at {PROFILE_PATH}")
    except Exception as e:
        print(f"[⚠️] Failed to create default profile: {e}")

# Load calibration data dynamically
def load_camera_profile():
    if not os.path.exists(PROFILE_PATH):
        print(f"[📊] Calibration data not found at {PROFILE_PATH}. Running calibration...")
        print(f"[🧠] Using calibration script at: {CALIBRATION_SCRIPT}")

        if not os.path.exists(CALIBRATION_SCRIPT):
            print(f"[❌] Calibration script not found at: {CALIBRATION_SCRIPT}")
            create_default_profile()
            return None

        try:
            VENV_PYTHON = os.path.abspath(os.path.join(BASE_DIR, "../venv/bin/python"))
            result = subprocess.run([VENV_PYTHON, CALIBRATION_SCRIPT], check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(f"[stderr] {result.stderr}")
        except subprocess.CalledProcessError as e:
            print(f"[❌] Calibration failed with return code {e.returncode}")
            print(f"[stdout] {e.stdout}")
            print(f"[stderr] {e.stderr}")
            create_default_profile()
            return None

    try:
        with open(PROFILE_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[⚠️] Failed to load calibration data: {e}")
        return None

def get_average_brightness():
    """
    Captures frames from webcam and calculates average brightness.
    """
    print("[📸] Initializing webcam...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[❌] Webcam not available.")
        return None

    # Get resolution and FPS from profile
    profile = load_camera_profile()
    if not profile:
        return None

    camera_resolution = profile.get("camera_resolution", [320, 240])
    fps_expected = profile.get("fps_expected", 30)
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_resolution[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_resolution[1])
    cap.set(cv2.CAP_PROP_FPS, fps_expected)

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
        if np.mean(gray) <= 10:
            time.sleep(0.05)
            max_attempts -= 1
            continue

        gray = cv2.medianBlur(gray, 5)
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
    return final_brightness

def get_current_brightness():
    """
    Gets current screen brightness percentage.
    """
    try:
        with open(os.path.join(BACKLIGHT_PATH, "brightness")) as f:
            current = int(f.read())
        with open(os.path.join(BACKLIGHT_PATH, "max_brightness")) as f:
            max_brightness = int(f.read())
        return int((current / max_brightness) * 100)
    except Exception as e:
        print(f"[⚠️] Could not read brightness: {e}")
        return 50


def set_brightness(percent):
    """
    Sets screen brightness using brightnessctl.
    """
    if not shutil.which("brightnessctl"):
        print("[🚫] brightnessctl not found!")
        return
    percent = int(np.clip(percent, 5, 100))
    os.system(f"brightnessctl set {percent}% > /dev/null 2>&1")
    print(f"[🔆] Screen brightness set to: {percent}%")


def ambient_to_percent(brightness, ambient_min=40, ambient_max=170):
    """
    Maps ambient light value to screen brightness percentage.
    """
    return int(np.clip(np.interp(brightness, [ambient_min, ambient_max], [10, 100]), 5, 100))


def main():
    print("[🚀] Smart Brightness starting up...")

    profile = load_camera_profile()
    if not profile:
        print("[⚠️] Could not proceed without calibration.")
        return

    ambient_min = profile.get("ambient_min", 40)
    ambient_max = profile.get("ambient_max", 170)

    ambient = get_average_brightness()
    if ambient is None:
        print("[⚠️] Adjustment skipped due to webcam/data issue.")
        return

    target_percent = ambient_to_percent(ambient, ambient_min, ambient_max)
    current_percent = get_current_brightness()

    print(f"[🎯] Transition from {current_percent}% → {target_percent}%")
    smooth_transition(
        current=current_percent,
        target=target_percent,
        setter=set_brightness,
        reader=get_current_brightness
    )
    print("[✅] Brightness adjustment complete.")


if __name__ == "__main__":
    main()

