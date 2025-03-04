# src/capture.py

import cv2
import numpy as np
from detection import detect_objects  # Função já implementada para detecção de objetos
from shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines, is_aligned

def main():
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Pré-processamento para detectar as prateleiras
        preprocessed = preprocess_for_shelf_detection(frame)
        shelf_lines = detect_shelf_lines(preprocessed)

        # Detecção dos objetos na imagem (usando o modelo YOLO, por exemplo)
        objects = detect_objects(frame)

        # Para cada objeto detectado, verificar se está alinhado com as prateleiras
        for obj in objects:
            box = obj["box"]
            aligned, line_y = is_aligned(box, shelf_lines)
            color = (0, 255, 0) if aligned else (0, 0, 255)
            x, y, w, h = box
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            label = f"{obj['class']} - {'Alinhado' if aligned else 'Desalinhado'}"
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Desenha as linhas das prateleiras detectadas
        if shelf_lines is not None:
            for rho, theta in shelf_lines:
                a = np.cos(theta)
                b = np.sin(theta)
                x0 = a * rho
                y0 = b * rho
                pt1 = (int(x0 + 1000 * (-b)), int(y0 + 1000 * (a)))
                pt2 = (int(x0 - 1000 * (-b)), int(y0 - 1000 * (a)))
                cv2.line(frame, pt1, pt2, (255, 0, 0), 2)

        cv2.imshow("Captura e Análise", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
