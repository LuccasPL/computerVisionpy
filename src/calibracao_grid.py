import cv2
import json
import os

# container for grid ROIs
grid_rois = []

# drawing state
drawing = False
pt1 = pt2 = None

# try to load the already-captured frame
calib_path = "data/annotations/calibration_frame.jpg"
if os.path.exists(calib_path):
    img = cv2.imread(calib_path)
    frame = img.copy()
else:
    # capture it now
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro ao abrir webcam.")
        exit(1)
    print("Pressione 'c' para congelar o frame e iniciar calibração de posições.")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.imshow("Ajuste e aperte 'c'", frame)
        if cv2.waitKey(1) & 0xFF == ord('c'):
            img = frame.copy()
            # save so next time we reuse
            os.makedirs("data/annotations", exist_ok=True)
            cv2.imwrite(calib_path, img)
            break
    cap.release()
    cv2.destroyWindow("Ajuste e aperte 'c'")

def mouse_cb(event, x, y, flags, param):
    global drawing, pt1, pt2, img
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        pt1 = (x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        pt2 = (x, y)
        # draw ROI
        cv2.rectangle(img, pt1, pt2, (0,255,0), 2)
        cv2.imshow("Calibração de Posições", img)
        # ask for shelf + position
        shelf = input("→ Número da prateleira para este ROI: ")
        pos   = input("→ Número da posição dentro desta prateleira: ")
        grid_rois.append({
            "shelf":   int(shelf),
            "position":int(pos),
            "x1":      pt1[0],
            "y1":      pt1[1],
            "x2":      pt2[0],
            "y2":      pt2[1]
        })

def main():
    global img
    cv2.namedWindow("Calibração de Posições")
    cv2.setMouseCallback("Calibração de Posições", mouse_cb)
    print("Desenhe retângulos (clique e solte).")
    print("Após cada, informe shelf e position.")
    print("Quando terminar, aperte 's' para salvar, 'r' para reiniciar.")

    while True:
        cv2.imshow("Calibração de Posições", img)
        k = cv2.waitKey(1) & 0xFF
        if k == ord('r'):
            img = cv2.imread(calib_path).copy()
            grid_rois.clear()
            print("Resetado.")
        elif k == ord('s'):
            break

    cv2.destroyAllWindows()

    os.makedirs("data/annotations", exist_ok=True)
    with open("data/annotations/grid_rois.json", "w") as f:
        json.dump(grid_rois, f, indent=2)
    print(f"{len(grid_rois)} ROIs salvos em 'data/annotations/grid_rois.json'.")

if __name__ == "__main__":
    main()
