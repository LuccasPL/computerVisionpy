# src/detection.py  (atualizado)
import cv2
import numpy as np
import os

# caminhos do seu modelo
MODEL_CONFIG  = os.path.join("models", "yolov3.cfg")
MODEL_WEIGHTS = os.path.join("models", "yolov3.weights")
CLASSES_FILE  = os.path.join("models", "coco.names")

# carrega nomes
with open(CLASSES_FILE, "r") as f:
    classes = [l.strip() for l in f]

# carrega a rede
net = cv2.dnn.readNet(MODEL_WEIGHTS, MODEL_CONFIG)

# força CPU (evita erros de CUDA)
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

# obtém nomes das camadas de saída
layer_names   = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

def detect_objects(frame,
                   confidence_threshold=0.2,   # abaixado de 0.5
                   nms_threshold=0.4,
                   inp_size=(416, 416)):       # aumentado de (416,416)
    """
    Retorna lista de detecções no formato:
      { 'class': str, 'confidence': float, 'box': [x,y,w,h] }
    """
    h, w = frame.shape[:2]

    # cria blob maior
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, inp_size,
                                 swapRB=True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    boxes, confidences, class_ids = [], [], []
    for out in outs:
        for det in out:
            scores = det[5:]
            cid    = np.argmax(scores)
            conf   = float(scores[cid])
            if conf > confidence_threshold:
                cls_name = classes[cid]
                thresh = confidence_threshold
                if cls_name == "sports ball":
                    thresh = 0.20
                if conf > thresh:
                    cx, cy = int(det[0] * w), int(det[1] * h)
                    bw, bh = int(det[2] * w), int(det[3] * h)
                    x = cx - bw//2
                    y = cy - bh//2
                    boxes.append([x, y, bw, bh])
                    confidences.append(conf)
                    class_ids.append(cid)

    # aplica Non‑Maxima Suppression
    idxs = cv2.dnn.NMSBoxes(boxes, confidences,
                            confidence_threshold, nms_threshold)

    detections = []
    if len(idxs) > 0:
        for i in idxs.flatten():
            detections.append({
                "class": classes[class_ids[i]],
                "confidence": confidences[i],
                "box": boxes[i]
            })
    return detections

if __name__ == "__main__":
    # teste rápido
    img = cv2.imread("data/raw/img_009.jpg")
    dets = detect_objects(img)
    for d in dets:
        x,y,w,h = d["box"]
        cv2.rectangle(img, (x,y),(x+w,y+h),(0,255,0),2)
        cv2.putText(img, f"{d['class']}:{d['confidence']:.2f}",
                    (x,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,(0,255,0),1)
    cv2.imshow("Teste", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
