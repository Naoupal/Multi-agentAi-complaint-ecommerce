import threading
_lock = threading.Lock()
_current_image_base64 = None

def set_current_image(image_base64: str | None):
    global _current_image_base64
    with _lock:
        _current_image_base64 = image_base64

def get_current_image() -> str | None:
    with _lock:
        return _current_image_base64

def clear_current_image():
    global _current_image_base64
    with _lock:
        _current_image_base64 = None
