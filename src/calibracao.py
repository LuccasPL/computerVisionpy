# src/calibracao.py

import cv2
import json

# Variáveis globais para armazenar pontos e ROIs
roi_points = []
rois = []
image = None

def select_roi(event, x, y, flags, param):
    global roi_points, rois, image
    # Quando o usuário clicar com o botão esquerdo, registre o primeiro ponto
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points = [(x, y)]
    # Quando soltar o botão, registre o segundo ponto e desenhe o retângulo
    elif event == cv2.EVENT_LBUTTONUP:
        roi_points.append((x, y))
        cv2.rectangle(image, roi_points[0], roi_points[1], (0, 255, 0), 2)
        rois.append(roi_points.copy())
        roi_points = []
        cv2.imshow("Calibração de Prateleiras", image)

def main():
    global image
    # Carregue uma imagem de exemplo do armazém (coloque uma imagem em data/raw/)
    image = cv2.imread("data/raw/exemplo.jpg")  # Certifique-se de ter uma imagem de exemplo
    if image is None:
        print("Erro: Imagem não encontrada em 'data/raw/exemplo.jpg'")
        return
    clone = image.copy()
    cv2.namedWindow("Calibração de Prateleiras")
    cv2.setMouseCallback("Calibração de Prateleiras", select_roi)
    print("Selecione as regiões de interesse (prateleiras) clicando e arrastando o mouse.")
    print("Pressione 'r' para reiniciar a seleção ou 'c' para confirmar e salvar.")

    while True:
        cv2.imshow("Calibração de Prateleiras", image)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            # Reinicia a imagem e as ROIs
            image = clone.copy()
            rois.clear()
            print("Seleção reiniciada.")
        elif key == ord('c'):
            # Confirma a seleção e sai do loop
            break

    cv2.destroyAllWindows()
    
    # Formata e salva as ROIs em um arquivo JSON
    rois_data = []
    for roi in rois:
        # Cada ROI será um dicionário com as coordenadas dos cantos
        roi_dict = {"x1": roi[0][0], "y1": roi[0][1], "x2": roi[1][0], "y2": roi[1][1]}
        rois_data.append(roi_dict)
    
    # Certifique-se de que a pasta 'data/annotations/' exista
    import os
    os.makedirs("data/annotations/", exist_ok=True)
    
    with open("data/annotations/rois.json", "w") as f:
        json.dump(rois_data, f, indent=4)
    print("As ROIs foram salvas em 'data/annotations/rois.json'.")

if __name__ == "__main__":
    main()
