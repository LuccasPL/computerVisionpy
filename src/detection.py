# src/detection.py

import cv2
import numpy as np

# Caminho para os arquivos do modelo
MODEL_CONFIG = "models\yolov3.cfg"
MODEL_WEIGHTS = "models\yolov3.weights"
CLASSES_FILE = "models\coco.names"

# Carregar os nomes das classes
with open(CLASSES_FILE, "r") as f:
    classes = [line.strip() for line in f.readlines()]

# Carregar o modelo YOLO com OpenCV DNN
net = cv2.dnn.readNet(MODEL_WEIGHTS, MODEL_CONFIG)

# Obter os nomes das camadas de saída
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

def detect_objects(frame, confidence_threshold=0.7, nms_threshold=0.4):
    height, width, _ = frame.shape
    # Criação do blob
    blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0,0,0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    class_ids = []
    confidences = []
    boxes = []
    
    # Processa cada detecção
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > confidence_threshold:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)
    
    # Supressão não máxima para remover sobreposições
    indexes = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, nms_threshold)
    detections = []
    for i in indexes:
        i = i[0] if isinstance(i, (list, tuple, np.ndarray)) else i
        box = boxes[i]
        detections.append({
            "class": classes[class_ids[i]],
            "confidence": confidences[i],
            "box": box
        })
    return detections

if __name__ == "__main__":
    # Teste com uma imagem
    img = cv2.imread("data/raw/img_009.jpg")
    results = detect_objects(img)
    for det in results:
        x, y, w, h = det["box"]
        label = det["class"]
        confidence = det["confidence"]
        cv2.rectangle(img, (x, y), (x+w, y+h), (0,255,0), 2)
        cv2.putText(img, f"{label} {confidence:.2f}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
    cv2.imshow("Detecções", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
