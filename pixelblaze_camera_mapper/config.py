from enum import Enum


class MappingMethod(Enum):
    LINEAR = 1  # Recommended
    BINARY = 2  # Experimental, not yet ready to use


# Options to set
PIXELBLAZE_IP = "192.168.4.1"
CAMERA_ID = 0  # The camera ID used by OpenCV.
SUBTRACT_BACKGROUND = False  # Only use if your camera/subject are both static
MAPPING_METHOD = MappingMethod.LINEAR
