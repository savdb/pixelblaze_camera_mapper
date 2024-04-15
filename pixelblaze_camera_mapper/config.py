from enum import Enum


class MappingMethod(Enum):
    LINEAR = 1  # Recommended
    BINARY = 2  # Faster but more error-prone


# Options to set
PIXELBLAZE_IP = "192.168.4.1"
CAMERA_ID = 0  # The camera ID used by OpenCV.
MAPPING_METHOD = MappingMethod.LINEAR

# Tweaks to detection parameters
SUBTRACT_BACKGROUND = False  # Only use if your camera/subject are both static
EROSION_SIZE = 2  # Used to remove small noisy areas
PIXEL_DETECTION_DISTANCE = 6  # Distance a pixel can move frame-to-frame (binary only)
