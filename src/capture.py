# src/capture.py

import cv2
import time
import numpy as np
from detection import detect_objects  # Função que retorna uma lista de dicionários com "box" e "class"
from shelf_detection import (
    preprocess_for_shelf_detection,
    detect_shelf_lines,
    is_aligned
)

def main():
    # Abre a webcam
    cap = cv2.VideoCapture(0)
    
    # Define o intervalo de detecção em segundos
    detection_interval = 5.0  
    last_detection_time = time.time()

    # Variável para armazenar a última detecção realizada
    last_detections = []
    # Variável para armazenar as linhas de prateleira detectadas (para desenhar)
    shelf_lines = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()
        elapsed = current_time - last_detection_time

        # Realiza a detecção apenas a cada 5 segundos
        if elapsed >= detection_interval:
            # Pré-processa o frame para detectar as prateleiras
            preprocessed = preprocess_for_shelf_detection(frame)
            shelf_lines = detect_shelf_lines(preprocessed)

            # Detecção dos objetos usando o seu modelo (por exemplo, YOLO)
            objects = detect_objects(frame)

            # Processa cada objeto detectado para verificar se está alinhado com as prateleiras
            last_detections = []  # Reinicia a lista de detecções
            for obj in objects:
                box = obj["box"]  # [x, y, w, h]
                aligned, line_y = is_aligned(box, shelf_lines)
                last_detections.append((box, obj["class"], aligned))
                
                # Imprime as posições e o status de alinhamento no console
                x, y, w, h = box
                print(f"Objeto '{obj['class']}' -> (x={x}, y={y}, w={w}, h={h}) | Alinhado: {aligned}")
            
            # Atualiza o tempo da última detecção
            last_detection_time = current_time

        # Desenha as detecções (caixas e rótulos) baseadas na última detecção
        for (box, obj_class, aligned) in last_detections:
            x, y, w, h = box
            color = (0, 255, 0) if aligned else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            label = f"{obj_class} - {'Alinhado' if aligned else 'Desalinhado'}"
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Desenha as linhas das prateleiras detectadas (opcional, para visualização)
        if shelf_lines is not None:
            for rho, theta in shelf_lines:
                a = np.cos(theta)
                b = np.sin(theta)
                x0 = a * rho
                y0 = b * rho
                pt1 = (int(x0 + 1000 * (-b)), int(y0 + 1000 * (a)))
                pt2 = (int(x0 - 1000 * (-b)), int(y0 - 1000 * (a)))
                cv2.line(frame, pt1, pt2, (255, 0, 0), 2)

        # Exibe o frame com as detecções e linhas desenhadas
        cv2.imshow("Deteccao a cada 5s", frame)

        # Pressione 'q' para sair
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
