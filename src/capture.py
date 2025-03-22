# src/capture.py

import cv2
import time
import numpy as np
from detection import detect_objects
from shelf_detection import preprocess_for_shelf_detection, detect_shelf_lines, is_aligned
from db import criar_tabela, inserir_deteccao
from sort import Sort  # Certifique-se de ter o módulo sort.py disponível na sua pasta 'src/'

def main():
    criar_tabela()  # Cria a tabela no MySQL, por exemplo

    # Inicializa a captura da webcam
    cap = cv2.VideoCapture(0)

    # Intervalo de detecção de 5 segundos
    detection_interval = 5.0  
    last_detection_time = time.time()

    # Lista para armazenar detecções (para exibição)
    last_detections = []
    shelf_lines = None

    # Inicializa o tracker SORT
    tracker = Sort(max_age=30, min_hits=3, iou_threshold=0.3)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()
        elapsed = current_time - last_detection_time

        # A cada 5 segundos, execute a detecção
        if elapsed >= detection_interval:
            # Pré-processamento para detecção de prateleiras
            preprocessed = preprocess_for_shelf_detection(frame)
            shelf_lines = detect_shelf_lines(preprocessed)

            # Detecta os objetos na imagem (por exemplo, usando YOLO)
            objects = detect_objects(frame)

            # Formata as detecções para o tracker SORT: [x1, y1, x2, y2, score]
            detections = []
            for obj in objects:
                x, y, w, h = obj["box"]
                score = obj["confidence"]
                x1, y1 = x, y
                x2, y2 = x + w, y + h
                detections.append([x1, y1, x2, y2, score])
            detections = np.array(detections)

            # Atualiza o tracker com as detecções
            tracks = tracker.update(detections)
            # tracks é um array com linhas do tipo [x1, y1, x2, y2, track_id]

            # Armazena os resultados da detecção com IDs únicos
            last_detections = []  
            for d in tracks:
                x1, y1, x2, y2, track_id = d
                # Converte para formato [x, y, w, h]
                box = [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]
                # Verifica se o objeto está alinhado com alguma prateleira
                aligned, line_y = is_aligned(box, shelf_lines)
                last_detections.append((box, track_id, aligned))
                # Imprime as coordenadas e o ID no console
                print(f"Objeto ID {int(track_id)} -> (x={box[0]}, y={box[1]}, w={box[2]}, h={box[3]}) | Alinhado: {aligned}")
                # Insere no banco de dados (opcional)
                # Supondo que a classe seja "person" ou outra, você pode adaptar:
                inserir_deteccao("person", box, aligned, line_y if line_y is not None else 0)

            last_detection_time = current_time

        # Desenha as detecções e os IDs dos objetos
        for (box, track_id, aligned) in last_detections:
            x, y, w, h = box
            color = (0, 255, 0) if aligned else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            label = f"ID {int(track_id)} - {'Alinhado' if aligned else 'Desalinhado'}"
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Opcional: Desenhar as linhas das prateleiras detectadas
        if shelf_lines is not None:
            for rho, theta in shelf_lines:
                a = np.cos(theta)
                b = np.sin(theta)
                x0 = a * rho
                y0 = b * rho
                pt1 = (int(x0 + 1000 * (-b)), int(y0 + 1000 * (a)))
                pt2 = (int(x0 - 1000 * (-b)), int(y0 - 1000 * (a)))
                cv2.line(frame, pt1, pt2, (255, 0, 0), 2)

        cv2.imshow("Deteccao com Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
