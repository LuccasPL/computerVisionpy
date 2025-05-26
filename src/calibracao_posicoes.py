import cv2
import json
import os
from roi_manager import carregar_prateleiras, verificar_prateleira

# estado temporário
roi_points = []
posicoes = []
image = None
shelf2count = {}

def select_posicao(event, x, y, flags, param):
    global roi_points, posicoes, image
    if event == cv2.EVENT_LBUTTONDOWN:
        roi_points = [(x, y)]
    elif event == cv2.EVENT_LBUTTONUP:
        roi_points.append((x, y))
        # desenha retângulo na cópia
        cv2.rectangle(image, roi_points[0], roi_points[1], (255, 0, 0), 2)
        # determina centro e prateleira
        cx = (roi_points[0][0] + roi_points[1][0]) // 2
        cy = (roi_points[0][1] + roi_points[1][1]) // 2
        in_shelf, shelf = verificar_prateleira((cx, cy), prateleiras)
        if not in_shelf:
            print("Posição fora de qualquer prateleira, ignorada.")
        else:
            sid = shelf["id"]
            # incrementa contador por prateleira
            cnt = shelf2count.get(sid, 0) + 1
            shelf2count[sid] = cnt
            posicoes.append({
                "shelf_id": sid,
                "pos_id": cnt,
                "x1": roi_points[0][0],
                "y1": roi_points[0][1],
                "x2": roi_points[1][0],
                "y2": roi_points[1][1]
            })
            print(f"Registrada posição {cnt} na prateleira {sid}.")
        roi_points = []

def main():
    global image, posicoes, prateleiras

    # carrega prateleiras já calibradas
    prateleiras = carregar_prateleiras("data/annotations/rois_prateleiras.json")
    if not prateleiras:
        print("Calibre as prateleiras antes.")
        return

    # carrega a mesma imagem usada na calibração de prateleiras
    frame_path = "data/annotations/calib_prateleiras.png"
    if not os.path.exists(frame_path):
        print(f"Imagem de calibração não encontrada em '{frame_path}'.")
        return
    image = cv2.imread(frame_path)
    if image is None:
        print("Falha ao carregar a imagem de calibração.")
        return

    # desenha contorno das prateleiras para referência
    for r in prateleiras:
        cv2.rectangle(image, (r['x1'], r['y1']), (r['x2'], r['y2']), (0,255,0), 2)

    cv2.namedWindow("Calibração de Posições")
    cv2.setMouseCallback("Calibração de Posições", select_posicao)
    print("Desenhe cada posição dentro das prateleiras. 'r' reinicia, 's' salva e sai.")

    base = image.copy()
    while True:
        cv2.imshow("Calibração de Posições", image)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            image = base.copy()
            posicoes = []
            shelf2count.clear()
            print("Posições reiniciadas.")
        elif key == ord('s'):
            break

    cv2.destroyAllWindows()

    # salva JSON com shelf_id e pos_id
    os.makedirs("data/annotations", exist_ok=True)
    with open("data/annotations/rois_posicoes.json", "w") as f:
        json.dump(posicoes, f, indent=4, ensure_ascii=False)
    print(f"{len(posicoes)} posições salvas em 'data/annotations/rois_posicoes.json'")

if __name__ == '__main__':
    main()
