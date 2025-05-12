import cv2
import json
import os

# Globals
roi_points = []
rois = []
image = None      # the captured calibration frame

def select_roi(event, x, y, flags, param):
    global roi_points, rois, image
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points = [(x, y)]
    elif event == cv2.EVENT_LBUTTONUP:
        roi_points.append((x, y))
        if image is not None and image.size:
            cv2.rectangle(image, roi_points[0], roi_points[1], (0, 255, 0), 1)
        rois.append(roi_points.copy())
        roi_points.clear()

def main():
    global image, rois
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro ao acessar a webcam.")
        return

    print("Ajuste a câmera. Quando estiver pronto, pressione 'c' para capturar o frame para calibração.")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.imshow("Calibração de Prateleiras - Live", frame)
        if cv2.waitKey(1) & 0xFF == ord('c'):
            image = frame.copy()
            break

    cap.release()
    cv2.destroyWindow("Calibração de Prateleiras - Live")

    # save the calibration image for reuse
    os.makedirs("data/annotations", exist_ok=True)
    cv2.imwrite("data/annotations/calibration_frame.jpg", image)

    # now draw shelf ROIs
    cv2.namedWindow("Calibração de Prateleiras - Live")
    cv2.setMouseCallback("Calibração de Prateleiras - Live", select_roi)
    print("Desenhe as prateleiras na imagem capturada.")
    print("Pressione 'r' para reiniciar, 'c' para confirmar e salvar.")

    while True:
        cv2.imshow("Calibração de Prateleiras - Live", image)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            image = cv2.imread("data/annotations/calibration_frame.jpg").copy()
            rois.clear()
            print("Seleção reiniciada.")
        elif key == ord('c'):
            break

    cv2.destroyAllWindows()

    # serialize shelf ROIs
    rois_data = []
    for idx, roi in enumerate(rois, start=1):
        x1,y1 = roi[0]
        x2,y2 = roi[1]
        rois_data.append({"id": idx, "x1": x1, "y1": y1, "x2": x2, "y2": y2})

    with open("data/annotations/rois_live.json", "w") as f:
        json.dump(rois_data, f, indent=4)

    print(f"{len(rois_data)} prateleiras salvas em 'data/annotations/rois_live.json'.")
    print("Imagem de calibração salva em 'data/annotations/calibration_frame.jpg'.")

if __name__ == "__main__":
    main()
