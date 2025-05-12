import cv2
import json
import os
from roi_manager import carregar_prateleiras

# Variáveis globais
roi_points = []
posicoes = []
image = None

def select_posicao(event, x, y, flags, param):
    global roi_points, posicoes, image
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points = [(x, y)]
    elif event == cv2.EVENT_LBUTTONUP:
        roi_points.append((x, y))
        if image is not None and image.size != 0:
            cv2.rectangle(image, roi_points[0], roi_points[1], (255, 0, 0), 2)
        posicoes.append(roi_points.copy())
        roi_points = []

def main():
    global image, posicoes
    # carrega prateleiras calibradas
    prateleiras = carregar_prateleiras()
    if not prateleiras:
        print("Calibre primeiro as prateleiras.")
        return

    # carrega imagem salva na calibração de prateleiras
    img_path = "data/annotations/calib_prateleiras.png"
    if not os.path.exists(img_path):
        print("Imagem de calibração não encontrada. Execute calibracao_prateleiras.py primeiro.")
        return
    image = cv2.imread(img_path)
    base = image.copy()

    # desenha retângulos das prateleiras como referência
    for r in prateleiras:
        cv2.rectangle(image, (r["x1"], r["y1"]), (r["x2"], r["y2"]), (0,255,0), 1)

    cv2.namedWindow("Calibração de Posições")
    cv2.setMouseCallback("Calibração de Posições", select_posicao)
    print("Desenhe cada posição (clique e arraste). 'r' para reiniciar, 's' para salvar.")

    while True:
        cv2.imshow("Calibração de Posições", image)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            image = base.copy()
            posicoes = []
            print("Reiniciado seleção de posições.")
        elif key == ord('s'):
            break

    cv2.destroyAllWindows()

    rois = []
    for idx, roi in enumerate(posicoes, start=1):
        (x1, y1), (x2, y2) = roi
        rois.append({"id": idx, "x1": x1, "y1": y1, "x2": x2, "y2": y2})

    os.makedirs("data/annotations", exist_ok=True)
    with open("data/annotations/rois_posicoes.json", "w") as f:
        json.dump(rois, f, indent=4)
    print(f"{len(rois)} posições salvas em data/annotations/rois_posicoes.json")

if __name__ == '__main__':
    main()
