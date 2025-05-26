import cv2
import json
import os

roi_points = []
prateleiras = []
image = None

def select_prateleira(event, x, y, flags, param):
    global roi_points, prateleiras, image
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points = [(x, y)]
    elif event == cv2.EVENT_LBUTTONUP:
        roi_points.append((x, y))
        cv2.rectangle(image, roi_points[0], roi_points[1], (0, 255, 0), 2)
        prateleiras.append(roi_points.copy())
        roi_points = []

def main():
    global image, prateleiras
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Erro ao acessar a webcam.")
        return

    print("Ajuste a câmera e pressione 'c' para capturar a imagem das prateleiras.")
    while True:
        ret, frame = cap.read()
        if not ret: continue
        cv2.imshow("Calibração de Prateleiras", frame)
        if cv2.waitKey(1) & 0xFF == ord('c'):
            image = frame.copy()
            break
    cap.release()

    # Salva frame para reuso
    os.makedirs("data/annotations", exist_ok=True)
    frame_path = "data/annotations/calib_prateleiras.png"
    cv2.imwrite(frame_path, image)
    print(f"Imagem de calibração salva em '{frame_path}'")

    # desenha ROIs
    cv2.namedWindow("Calibração de Prateleiras")
    cv2.setMouseCallback("Calibração de Prateleiras", select_prateleira)
    print("Desenhe cada prateleira com o mouse. 'r' para reiniciar, 's' para salvar.")

    original = image.copy()
    while True:
        cv2.imshow("Calibração de Prateleiras", image)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            image = original.copy()
            prateleiras = []
            print("Prateleiras reiniciadas.")
        elif key == ord('s'):
            break

    cv2.destroyAllWindows()

    rois = []
    for idx, ((x1, y1), (x2, y2)) in enumerate(prateleiras, start=1):
        rois.append({"id": idx, "x1": x1, "y1": y1, "x2": x2, "y2": y2})

    with open("data/annotations/rois_prateleiras.json", "w") as f:
        json.dump(rois, f, indent=4)
    print(f"{len(rois)} prateleiras salvas em 'data/annotations/rois_prateleiras.json'")

if __name__ == '__main__':
    main()
