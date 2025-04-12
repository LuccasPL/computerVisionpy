# src/utils.py

import cv2

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
