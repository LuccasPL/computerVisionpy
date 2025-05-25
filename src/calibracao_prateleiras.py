import cv2
import json
import os

roi_points = []
rois = []
image = None

def select_roi(event, x, y, flags, param):
    global roi_points, rois, image
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points = [(x, y)]
    elif event == cv2.EVENT_LBUTTONUP:
        roi_points.append((x, y))
        cv2.rectangle(image, roi_points[0], roi_points[1], (0, 255, 0), 1)
        rois.append({
            "id": len(rois) + 1,
            "x1": roi_points[0][0],
            "y1": roi_points[0][1],
            "x2": roi_points[1][0],
            "y2": roi_points[1][1]
        })
        roi_points = []

def main():
    global image, rois
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro ao acessar a webcam.")
        return

    print("Pressione 'c' para capturar a imagem-base das prateleiras.")
    while True:
        ret, frame = cap.read()
        if not ret: continue
        cv2.imshow("Calibração Prateleiras - Ajuste e 'c' para capturar", frame)
        if cv2.waitKey(1) & 0xFF == ord('c'):
            image = frame.copy()
            os.makedirs("data/annotations/", exist_ok=True)
            cv2.imwrite("data/annotations/calib_frame.png", image)
            break

    cap.release()
    cv2.namedWindow("Desenhe Prateleiras")
    cv2.setMouseCallback("Desenhe Prateleiras", select_roi)
    print("Desenhe retângulos sobre cada prateleira. 'r' para reset, 's' para salvar.")

    while True:
        disp = image.copy()
        cv2.imshow("Desenhe Prateleiras", disp)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            image = cv2.imread("data/annotations/calib_frame.png")
            rois = []
            print("Resetado.")
        elif key == ord('s'):
            break

    cv2.destroyAllWindows()
    with open("data/annotations/rois_prateleiras.json", "w") as f:
        json.dump(rois, f, indent=2)
    print(f"{len(rois)} prateleiras salvas em rois_prateleiras.json.")

if __name__ == "__main__":
    main()
