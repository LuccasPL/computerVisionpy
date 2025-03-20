# src/capture.py

import cv2
import time
import numpy as np
from detection import detect_objects
from shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines, is_aligned
from db import criar_tabela, inserir_deteccao  # Agora usando MySQL

def main():
    # Cria a tabela no banco de dados MySQL, se não existir
    criar_tabela()
    
    cap = cv2.VideoCapture(0)
    detection_interval = 5.0  # Intervalo de 5 segundos para detecção
    last_detection_time = time.time()
    last_detections = []
    shelf_lines = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()
        elapsed = current_time - last_detection_time

        if elapsed >= detection_interval:
            preprocessed = preprocess_for_shelf_detection(frame)
            shelf_lines = detect_shelf_lines(preprocessed)
            objects = detect_objects(frame)
            last_detections = []  # Reinicia a lista de detecções

            for obj in objects:
                box = obj["box"]
                aligned, line_y = is_aligned(box, shelf_lines)
                last_detections.append((box, obj["class"], aligned))
                x, y, w, h = box
                print(f"Objeto '{obj['class']}' -> (x={x}, y={y}, w={w}, h={h}) | Alinhado: {aligned}")
                inserir_deteccao(obj["class"], box, aligned, line_y)
            
            last_detection_time = current_time

        for (box, obj_class, aligned) in last_detections:
            x, y, w, h = box
            color = (0, 255, 0) if aligned else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            label = f"{obj_class} - {'Alinhado' if aligned else 'Desalinhado'}"
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        if shelf_lines is not None:
            for rho, theta in shelf_lines:
                a = np.cos(theta)
                b = np.sin(theta)
                x0 = a * rho
                y0 = b * rho
                pt1 = (int(x0 + 1000 * (-b)), int(y0 + 1000 * (a)))
                pt2 = (int(x0 - 1000 * (-b)), int(y0 - 1000 * (a)))
                cv2.line(frame, pt1, pt2, (255, 0, 0), 2)

        cv2.imshow("Deteccao a cada 5s", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
