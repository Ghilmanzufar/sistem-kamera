import os
import sys
import time
import threading
import cv2

def create_capture_device(source):
    """
    Inisialisasi cv2.VideoCapture dengan DirectShow (Windows) & RTSP low-latency buffer.
    """
    is_num = isinstance(source, int) or (isinstance(source, str) and str(source).strip().isdigit())
    if is_num:
        src_idx = int(source)
        if sys.platform.startswith("win"):
            cap = cv2.VideoCapture(src_idx, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(src_idx)
        else:
            cap = cv2.VideoCapture(src_idx)
    else:
        # RTSP / Network Stream: TCP transport & 2s timeout
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|timeout;2000000"
        cap = cv2.VideoCapture(str(source))

    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Zero-delay buffer
    return cap
