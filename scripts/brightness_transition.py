import time

def ease_out(t):
    """Ease-out function for smooth transitions."""
    return 1 - (1 - t) ** 3  # Cubic ease-out

def smooth_transition(current, target, duration=5.0, step_size=2, setter=None, reader=None):
    """
    Smoothly transitions from `current` to `target` using precise timing and feedback.
    
    - `setter`: function to apply each brightness level.
    - `reader`: function to re-read actual brightness for sync (optional).
    - `step_size`: step size in percent (default 2).
    - `duration`: total transition duration (in seconds).
    """
    if current == target:
        return  # Nothing to do

    diff = abs(target - current)
    steps = max(diff // step_size, 1)
    delay = duration / steps
    direction = 1 if target > current else -1

    for step in range(steps):
        # Use ease-out to change brightness progressively
        progress = ease_out(step / steps)
        transition_value = current + (diff * progress * direction)

        # Clamp between 5–100%
        transition_value = max(5, min(100, int(transition_value)))

        if setter:
            setter(transition_value)
        else:
            print(f"Would set: {transition_value}%")

        # Optional: verify if actual brightness is applied
        if reader:
            while abs(reader() - transition_value) > 1:
                time.sleep(0.05)

        time.sleep(delay)

    # Final correction
    if setter:
        setter(target)

