import cv2
import json
import os

roi_points = []
positions = []
image = None

def select_roi(event, x, y, flags, param):
    global roi_points, positions, image
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points = [(x, y)]
    elif event == cv2.EVENT_LBUTTONUP:
        roi_points.append((x, y))
        cv2.rectangle(image, roi_points[0], roi_points[1], (255, 0, 0), 1)
        positions.append({
            "id": len(positions) + 1,
            "x1": roi_points[0][0],
            "y1": roi_points[0][1],
            "x2": roi_points[1][0],
            "y2": roi_points[1][1]
        })
        roi_points = []

def main():
    global image, positions
    path = "data/annotations/calib_frame.png"
    if not os.path.exists(path):
        print("Execute primeiro calibracao_prateleiras.py")
        return
    image = cv2.imread(path)
    if image is None:
        print("Erro ao carregar o frame de calibração.")
        return

    cv2.namedWindow("Desenhe Posições")
    cv2.setMouseCallback("Desenhe Posições", select_roi)
    print("Desenhe retângulos sobre cada posição. 'r' para reset, 's' para salvar.")

    while True:
        disp = image.copy()
        cv2.imshow("Desenhe Posições", disp)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            image = cv2.imread(path)
            positions = []
            print("Resetado.")
        elif key == ord('s'):
            break

    cv2.destroyAllWindows()
    os.makedirs("data/annotations/", exist_ok=True)
    with open("data/annotations/rois_posicoes.json", "w") as f:
        json.dump(positions, f, indent=2)
    print(f"{len(positions)} posições salvas em rois_posicoes.json.")

if __name__ == "__main__":
    main()
