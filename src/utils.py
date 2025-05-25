# src/utils.py

import cv2
import numpy as np

def adjust_gamma(image, gamma=1.3):
    inv = 1.0 / gamma
    table = np.array([((i/255.0)**inv)*255 for i in np.arange(256)]).astype("uint8")
    return cv2.LUT(image, table)

def preprocess_frame(frame):
    # CLAHE no canal de luminância
    yuv   = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    yuv[:,:,0] = clahe.apply(yuv[:,:,0])
    return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)

def draw_detection(frame, detection, color=(0, 255, 0)):
    """
    Desenha uma caixa delimitadora e o rótulo no frame.
    :param frame: imagem (numpy array)
    :param detection: dicionário com keys "box", "class", "confidence"
    :param color: cor da caixa (B, G, R)
    """
    x, y, w, h = detection["box"]
    label = detection["class"]
    confidence = detection["confidence"]
    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
    cv2.putText(frame, f"{label} {confidence:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return frame
