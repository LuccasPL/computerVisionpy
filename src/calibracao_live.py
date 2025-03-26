# src/calibracao_live.py

import cv2
import json
import os

# Variáveis globais
roi_points = []
rois = []
image = None  # Declaração global da variável image

def select_roi(event, x, y, flags, param):
    global roi_points, rois, image  # Garante que usaremos a variável global 'image'
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points = [(x, y)]
    elif event == cv2.EVENT_LBUTTONUP:
        roi_points.append((x, y))
        # Verifica se 'image' está definida e possui tamanho válido antes de desenhar
        if image is not None and image.size != 0:
            cv2.rectangle(image, roi_points[0], roi_points[1], (0, 255, 0), 1)
        rois.append(roi_points.copy())
        roi_points = []

def main():
    global image, rois  # Declaramos que vamos usar as variáveis globais 'image' e 'rois'
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro ao acessar a webcam.")
        return

    print("Ajuste a câmera. Quando estiver pronto, pressione 'c' para capturar a imagem para calibração.")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.imshow("Calibração de Prateleiras - Live", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('c'):
            image = frame.copy()  # Captura a imagem e a guarda na variável global 'image'
            break

    cap.release()

    # Cria uma janela nomeada e define o callback para capturar os ROIs
    cv2.namedWindow("Calibração de Prateleiras - Live")
    cv2.setMouseCallback("Calibração de Prateleiras - Live", select_roi)
    print("Agora, desenhe as regiões de interesse (prateleiras) na imagem capturada.")
    print("Pressione 'r' para reiniciar a seleção ou 'c' para confirmar e salvar.")

    # Loop para exibir a imagem e permitir a seleção dos ROIs
    while True:
        cv2.imshow("Calibração de Prateleiras - Live", image)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            # Se o usuário desejar reiniciar, recarregamos a imagem original
            image = frame.copy()
            rois = []
            print("Seleção reiniciada.")
        elif key == ord('c'):
            break

    cv2.destroyAllWindows()

    # Salva as ROIs em um arquivo JSON
    rois_data = []
    for index, roi in enumerate(rois, start=1):
        roi_dict = {"id": index, "x1": roi[0][0], "y1": roi[0][1], "x2": roi[1][0], "y2": roi[1][1]}
        rois_data.append(roi_dict)

    os.makedirs("data/annotations/", exist_ok=True)
    with open("data/annotations/rois_live.json", "w") as f:
        json.dump(rois_data, f, indent=4)
    print("ROIs salvas em 'data/annotations/rois_live.json'.")

if __name__ == '__main__':
    main()
