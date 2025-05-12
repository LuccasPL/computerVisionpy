import cv2
import json
import os

# Variáveis globais
roi_points = []
prateleiras = []
image = None

def select_prateleira(event, x, y, flags, param):
    global roi_points, prateleiras, image
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points = [(x, y)]
    elif event == cv2.EVENT_LBUTTONUP:
        roi_points.append((x, y))
        if image is not None and image.size != 0:
            cv2.rectangle(image, roi_points[0], roi_points[1], (0, 255, 0), 1)
        prateleiras.append(roi_points.copy())
        roi_points = []

def main():
    global image, prateleiras
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro ao acessar a webcam.")
        return

    print("Ajuste a câmera e pressione 'c' para congelar o frame das prateleiras.")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.imshow("Calibração de Prateleiras", frame)
        if cv2.waitKey(1) & 0xFF == ord('c'):
            image = frame.copy()
            # salva a imagem para reuso
            os.makedirs("data/annotations", exist_ok=True)
            cv2.imwrite("data/annotations/calib_prateleiras.png", image)
            break
    cap.release()

    cv2.namedWindow("Calibração de Prateleiras")
    cv2.setMouseCallback("Calibração de Prateleiras", select_prateleira)
    print("Desenhe cada prateleira (clique e arraste). 'r' para reiniciar, 's' para salvar.")

    original = image.copy()
    while True:
        cv2.imshow("Calibração de Prateleiras", image)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            image = original.copy()
            prateleiras = []
            print("Reiniciado seleção de prateleiras.")
        elif key == ord('s'):
            break

    cv2.destroyAllWindows()

    rois = []
    for idx, roi in enumerate(prateleiras, start=1):
        (x1, y1), (x2, y2) = roi
        rois.append({"id": idx, "x1": x1, "y1": y1, "x2": x2, "y2": y2})

    with open("data/annotations/rois_prateleiras.json", "w") as f:
        json.dump(rois, f, indent=4)
    print(f"{len(rois)} prateleiras salvas em data/annotations/rois_prateleiras.json")

if __name__ == '__main__':
    main()
